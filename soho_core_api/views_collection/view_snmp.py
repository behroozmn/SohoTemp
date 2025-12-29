# soho_core_api/views_collection/view_snmp.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

# Core utilities
from pylibs import (
    get_request_param,
    build_standard_error_response,
    StandardResponse,
    StandardErrorResponse,
)
from pylibs.mixins import SNMPValidationMixin
from pylibs.snmp import SNMPManager

# ========== OpenAPI Parameters ==========
ParamSNMPOperation = OpenApiParameter(
    name="operation",
    type=str,
    required=True,
    location="path",
    description="عملیات مورد نظر روی سرویس SNMP",
    enum=["start", "stop", "restart", "enable", "disable"],
)

# ========== ViewSet ==========
class SNMPViewSet(viewsets.ViewSet, SNMPValidationMixin):
    """
    مدیریت سرویس SNMP.
    """

    @extend_schema(
        responses={200: inline_serializer("SNMPConfig", {"data": serializers.JSONField()})}
    )
    def retrieve(self, request: Request) -> Response:
        """
        دریافت وضعیت و تنظیمات فعلی سرویس SNMP.
        """
        request_data = dict(request.query_params)
        try:
            manager = SNMPManager()
            data = {
                "config": manager.get_snmp_config(),
                "status": manager.get_snmp_status(),
            }
            return StandardResponse(
                data=data,
                message="تنظیمات و وضعیت SNMP با موفقیت دریافت شد.",
                request_data=request_data,
                save_to_db=False,
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="snmp_retrieve_failed",
                error_message="خطا در دریافت تنظیمات SNMP.",
                request_data=request_data,
                save_to_db=False,
            )

    @extend_schema(
        request=inline_serializer(
            name="SNMPConfigRequest",
            fields={
                "community": serializers.CharField(help_text="جامعیت SNMP"),
                "contact": serializers.CharField(required=False, help_text="اطلاعات تماس سیستم"),
                "location": serializers.CharField(required=False, help_text="مکان سیستم"),
                "sys_name": serializers.CharField(required=False, help_text="نام سیستم"),
                "port": serializers.CharField(required=False, default="161", help_text="پورت SNMP"),
                "version": serializers.CharField(required=False, default="2c", help_text="نسخه SNMP"),
            }
        ),
        responses={200: StandardResponse}
    )
    @action(detail=False, methods=["post"], url_path="config")
    def configure_snmp(self, request: Request) -> Response:
        """
        تنظیم پیکربندی سرویس SNMP.
        """
        config_data = request.data
        request_data = dict(request.data)
        
        err = self.validate_snmp_config(config_data, False, request_data)
        if err:
            return err

        try:
            manager = SNMPManager()
            manager.set_snmp_config(
                community=config_data.get("community", "public"),
                contact=config_data.get("contact"),
                location=config_data.get("location"),
                sys_name=config_data.get("sys_name"),
                port=config_data.get("port", "161"),
                version=config_data.get("version", "2c")
            )
            return StandardResponse(
                message="پیکربندی SNMP با موفقیت انجام شد.",
                request_data=request_data,
                save_to_db=False,
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="snmp_config_failed",
                error_message="خطا در تنظیم پیکربندی SNMP.",
                request_data=request_data,
                save_to_db=False,
            )

    @extend_schema(
        parameters=[ParamSNMPOperation],
        responses={200: StandardResponse}
    )
    @action(detail=False, methods=["post"], url_path="service/(?P<operation>[^/.]+)")
    def control_snmp_service(self, request: Request, operation: str) -> Response:
        """
        اجرای یک عملیات کنترلی روی سرویس SNMP (start, stop, restart, enable, disable).
        """
        request_data = {"operation": [operation]}
        
        err = self.validate_snmp_service_operation(operation, False, request_data)
        if err:
            return err

        try:
            manager = SNMPManager()
            method = getattr(manager, f"{operation}_snmp_service")
            method()
            return StandardResponse(
                message=f"عملیات '{operation}' روی سرویس SNMP با موفقیت انجام شد.",
                request_data=request_data,
                save_to_db=False,
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="snmp_control_failed",
                error_message=f"خطا در اجرای عملیات '{operation}' روی سرویس SNMP.",
                request_data=request_data,
                save_to_db=False,
            )

    @extend_schema(
        request=inline_serializer(
            name="SNMPTestRequest",
            fields={
                "community": serializers.CharField(required=False, default="public", help_text="جامعیت SNMP"),
                "version": serializers.CharField(required=False, default="2c", help_text="نسخه SNMP"),
                "host": serializers.CharField(required=False, default="localhost", help_text="هاست SNMP"),
                "port": serializers.CharField(required=False, default="161", help_text="پورت SNMP"),
            }
        ),
        responses={200: inline_serializer("SNMPTestResult", {"data": serializers.JSONField()})}
    )
    @action(detail=False, methods=["post"], url_path="test-connection")
    def test_snmp_connection(self, request: Request) -> Response:
        """
        تست اتصال به سرویس SNMP.
        """
        test_data = request.data
        request_data = dict(request.data)
        
        try:
            manager = SNMPManager()
            result = manager.test_snmp_connection(
                community=test_data.get("community", "public"),
                version=test_data.get("version", "2c"),
                host=test_data.get("host", "localhost"),
                port=test_data.get("port", "161")
            )
            return StandardResponse(
                data={"connection_success": result},
                message="تست اتصال SNMP انجام شد.",
                request_data=request_data,
                save_to_db=False,
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="snmp_test_failed",
                error_message="خطا در تست اتصال SNMP.",
                request_data=request_data,
                save_to_db=False,
            )