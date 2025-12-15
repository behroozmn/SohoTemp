# soho_core_api/views_collection/view_service.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, inline_serializer
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
    QuerySaveToDB,
)
from pylibs.mixins import ServiceValidationMixin
from pylibs.service import ServiceManager

# ========== OpenAPI Parameters ==========
ParamUnitName = OpenApiParameter(
    name="unit_name",
    type=str,
    required=True,
    location="path",
    description="نام یونیت systemd (مثال: nginx.service, sshd.service)",
)

ParamStateFilter = OpenApiParameter(
    name="state",
    type=str,
    required=False,
    description="فیلتر لیست یونیت‌ها بر اساس وضعیت (active, inactive, failed, running, ...)",
)

ParamAction = OpenApiParameter(
    name="action",
    type=str,
    required=True,
    description="عملیات مورد نظر روی سرویس",
    enum=["start", "stop", "restart", "reload", "enable", "disable", "mask", "unmask"],
)


# ========== ViewSet ==========
class SystemServiceViewSet(viewsets.ViewSet, ServiceValidationMixin):
    """
    مدیریت سرویس‌های سیستم‌عامل بر پایه systemd.
    """
    lookup_field = "unit_name"

    @extend_schema(parameters=[ParamStateFilter], responses={200: inline_serializer("UnitList", {"data": serializers.JSONField()})})
    def list(self, request: Request) -> Response:
        """
        دریافت لیست تمام یونیت‌های systemd با امکان فیلتر بر اساس وضعیت.
        """
        state = get_request_param(request, "state", str, None)
        request_data = dict(request.query_params)
        try:
            manager = ServiceManager()
            data = manager.list_units(state_filter=state)
            return StandardResponse(
                data=data,
                message="لیست یونیت‌ها با موفقیت دریافت شد.",
                request_data=request_data,
                save_to_db=False,
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="unit_list_failed",
                error_message="خطا در دریافت لیست یونیت‌ها.",
                request_data=request_data,
                save_to_db=False,
            )

    @extend_schema(parameters=[ParamUnitName], responses={200: inline_serializer("UnitDetail", {"data": serializers.JSONField()})})
    def retrieve(self, request: Request, unit_name: str) -> Response:
        """
        دریافت وضعیت کامل یک یونیت systemd (شامل PID، وضعیت فعال/غیرفعال، enabled بودن و ...).
        """
        request_data = dict(request.query_params)
        err = self.validate_unit_name(unit_name, request_data)
        if err:
            return err
        try:
            manager = ServiceManager()
            data = {
                "status": manager.get_status(unit_name),
                "dependencies": manager.get_dependencies(unit_name),
            }
            return StandardResponse(
                data=data,
                message=f"وضعیت یونیت '{unit_name}' با موفقیت دریافت شد.",
                request_data=request_data,
                save_to_db=False,
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="unit_status_failed",
                error_message="خطا در دریافت وضعیت یونیت.",
                request_data=request_data,
                save_to_db=False,
            )

    @extend_schema(parameters=[ParamUnitName, ParamAction], responses={200: StandardResponse})
    @action(detail=True, methods=["put"], url_path="control")
    def control_service(self, request: Request, unit_name: str) -> Response:
        """
        اجرای یک عملیات کنترلی روی سرویس (start, stop, restart, enable, mask و ...).
        """
        action_name = get_request_param(request, "action", str, None)
        request_data = dict(request.query_params)
        if not action_name:
            return StandardErrorResponse(
                error_code="missing_action",
                error_message="پارامتر 'action' الزامی است.",
                status=400,
                request_data=request_data,
                save_to_db=False,
            )
        err = self.validate_unit_name(unit_name,request_data)
        if err:
            return err

        err = self.validate_service_action(action_name, request_data)
        if err:
            return err

        try:
            manager = ServiceManager()
            method = getattr(manager, action_name)
            method(unit_name)
            return StandardResponse(
                message=f"عملیات '{action_name}' روی یونیت '{unit_name}' با موفقیت انجام شد.",
                request_data=request_data,
                save_to_db=False,
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="service_control_failed",
                error_message=f"خطا در اجرای عملیات '{action_name}' روی یونیت '{unit_name}'.",
                request_data=request_data,
                save_to_db=False,
            )
