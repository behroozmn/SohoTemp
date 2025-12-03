# soho_core_api/views/view_samba.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from pylibs import (
    get_request_param,
    build_standard_error_response,
    QuerySaveToDB,
    BodyParameterSaveToDB,
    StandardResponse,
    StandardErrorResponse,
)
from pylibs.samba import SambaManager
from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

# OpenAPI Parameters
ParamAll = OpenApiParameter(
    name="all", type=bool, required=False, default="true",
    description="دریافت تمام پراپرتی‌ها در صورت true"
)
ParamProperty = OpenApiParameter(
    name="property", type=str, required=False,
    description="نام پراپرتی خاص برای بازیابی"
)
ParamOnlyCustom = OpenApiParameter(
    name="only_custom", type=bool, required=False, default="false",
    description="فقط موارد ایجادشده توسط مدیر سیستم"
)
ParamOnlyShared = OpenApiParameter(
    name="only_shared", type=bool, required=False, default="false",
    description="فقط مواردی که در smb.conf استفاده شده‌اند"
)

class SambaUserView(APIView):
    """مدیریت کاربران سامبا."""

    @extend_schema(
        parameters=[
            OpenApiParameter(name="username", type=str, location="path", required=False,
                             description="نام کاربر (اختیاری)"),
            ParamAll, ParamProperty, ParamOnlyCustom, ParamOnlyShared
        ] + QuerySaveToDB,
        responses={200: inline_serializer("SambaUserResponse", {"data": serializers.JSONField()})}
    )
    def get(self, request: Request, username: Optional[str] = None) -> Response:
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        all_props = get_request_param(request, "all", bool, True)
        prop = get_request_param(request, "property", str, None)
        only_custom = get_request_param(request, "only_custom", bool, False)
        only_shared = get_request_param(request, "only_shared", bool, False)
        request_data = dict(request.query_params)

        try:
            manager = SambaManager()
            data = manager.get_samba_users(
                username=username,
                all_props=all_props,
                property_name=prop,
                only_custom_users=only_custom,
                only_shared_users=only_shared
            )
            if username and data is None:
                return StandardErrorResponse(
                    error_code="user_not_found",
                    error_message=f"کاربر '{username}' یافت نشد.",
                    status=404,
                    request_data=request_data,
                    save_to_db=save_to_db
                )
            return StandardResponse(
                data=data,
                message="اطلاعات کاربر(ها) سامبا با موفقیت بازیابی شد.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                error_code="samba_user_fetch_failed",
                error_message="خطا در دریافت اطلاعات کاربر(ها) سامبا.",
                request_data=request_data,
                save_to_db=save_to_db
            )

    @extend_schema(
        request={"application/json": {
            "type": "object",
            "properties": {
                "password": {"type": "string", "description": "رمز عبور کاربر"},
                "full_name": {"type": "string", "description": "نام کامل"},
                "expiration_date": {"type": "string", "format": "date", "description": "تاریخ انقضا به فرمت YYYY-MM-DD"},
                **BodyParameterSaveToDB["properties"]
            },
            "required": ["password"]
        }},
        responses={201: StandardResponse}
    )
    def post(self, request: Request, username: str) -> Response:
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        password = get_request_param(request, "password", str, None)
        full_name = get_request_param(request, "full_name", str, None)
        expiration = get_request_param(request, "expiration_date", str, None)
        request_data = dict(request.data)

        if not password:
            return StandardErrorResponse(
                error_code="missing_password",
                error_message="رمز عبور اجباری است.",
                status=400,
                request_data=request_data,
                save_to_db=save_to_db
            )

        try:
            manager = SambaManager()
            manager.create_samba_user(
                username=username,
                password=password,
                full_name=full_name,
                expiration_date=expiration
            )
            return StandardResponse(
                message=f"کاربر سامبا '{username}' با موفقیت ایجاد شد.",
                request_data=request_data,
                save_to_db=save_to_db,
                status=201
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                error_code="samba_user_create_failed",
                error_message="خطا در ایجاد کاربر سامبا.",
                request_data=request_data,
                save_to_db=save_to_db
            )

    @extend_schema(
        request={"application/json": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["enable", "disable", "delete", "change_password"], "description": "عملیات مورد نظر"},
                "new_password": {"type": "string", "description": "در صورت action=change_password"},
                **BodyParameterSaveToDB["properties"]
            },
            "required": ["action"]
        }}
    )
    def patch(self, request: Request, username: str) -> Response:
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        action = get_request_param(request, "action", str, None)
        new_pass = get_request_param(request, "new_password", str, None)
        request_data = dict(request.data)

        if not action:
            return StandardErrorResponse(
                error_code="missing_action",
                error_message="عملیات (action) اجباری است.",
                status=400,
                request_data=request_data,
                save_to_db=save_to_db
            )

        try:
            manager = SambaManager()
            if action == "enable":
                manager.enable_samba_user(username)
            elif action == "disable":
                manager.disable_samba_user(username)
            elif action == "delete":
                manager.delete_samba_user_or_group(username, is_group=False)
            elif action == "change_password":
                if not new_pass:
                    return StandardErrorResponse(
                        error_code="missing_new_password",
                        error_message="رمز جدید برای تغییر پسورد اجباری است.",
                        status=400,
                        request_data=request_data,
                        save_to_db=save_to_db
                    )
                manager.change_samba_user_password(username, new_pass)
            else:
                return StandardErrorResponse(
                    error_code="invalid_action",
                    error_message="عملیات نامعتبر.",
                    status=400,
                    request_data=request_data,
                    save_to_db=save_to_db
                )
            return StandardResponse(
                message=f"عملیات '{action}' بر روی کاربر '{username}' با موفقیت انجام شد.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                error_code="samba_user_modify_failed",
                error_message="خطا در انجام عملیات روی کاربر سامبا.",
                request_data=request_data,
                save_to_db=save_to_db
            )

class SambaGroupView(APIView):
    """مدیریت گروه‌های سامبا."""

    @extend_schema(
        parameters=[
            OpenApiParameter(name="groupname", type=str, location="path", required=False),
            ParamAll, ParamProperty, ParamOnlyCustom, ParamOnlyShared
        ] + QuerySaveToDB
    )
    def get(self, request: Request, groupname: Optional[str] = None) -> Response:
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        all_props = get_request_param(request, "all", bool, True)
        prop = get_request_param(request, "property", str, None)
        only_custom = get_request_param(request, "only_custom", bool, False)
        only_shared = get_request_param(request, "only_shared", bool, False)
        request_data = dict(request.query_params)

        try:
            manager = SambaManager()
            data = manager.get_samba_groups(
                groupname=groupname,
                all_props=all_props,
                property_name=prop,
                only_custom_groups=only_custom,
                only_shared_groups=only_shared
            )
            if groupname and data is None:
                return StandardErrorResponse(
                    error_code="group_not_found",
                    error_message=f"گروه '{groupname}' یافت نشد.",
                    status=404,
                    request_data=request_data,
                    save_to_db=save_to_db
                )
            return StandardResponse(
                data=data,
                message="اطلاعات گروه(ها) سامبا با موفقیت بازیابی شد.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                error_code="samba_group_fetch_failed",
                error_message="خطا در دریافت اطلاعات گروه(ها) سامبا.",
                request_data=request_data,
                save_to_db=save_to_db
            )

    @extend_schema(
        request={"application/json": {
            "type": "object",
            "properties": {
                **BodyParameterSaveToDB["properties"]
            }
        }}
    )
    def post(self, request: Request, groupname: str) -> Response:
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.data)

        try:
            manager = SambaManager()
            manager.create_samba_group(groupname)
            return StandardResponse(
                message=f"گروه سامبا '{groupname}' با موفقیت ایجاد شد.",
                request_data=request_data,
                save_to_db=save_to_db,
                status=201
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                error_code="samba_group_create_failed",
                error_message="خطا در ایجاد گروه سامبا.",
                request_data=request_data,
                save_to_db=save_to_db
            )

    @extend_schema(
        request={"application/json": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["delete"], "description": "عملیات مورد نظر"},
                **BodyParameterSaveToDB["properties"]
            },
            "required": ["action"]
        }}
    )
    def patch(self, request: Request, groupname: str) -> Response:
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        action = get_request_param(request, "action", str, "delete")
        request_data = dict(request.data)

        try:
            manager = SambaManager()
            if action == "delete":
                manager.delete_samba_user_or_group(groupname, is_group=True)
            else:
                return StandardErrorResponse(
                    error_code="invalid_action",
                    error_message="عملیات نامعتبر.",
                    status=400,
                    request_data=request_data,
                    save_to_db=save_to_db
                )
            return StandardResponse(
                message=f"گروه '{groupname}' با موفقیت حذف شد.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                error_code="samba_group_modify_failed",
                error_message="خطا در انجام عملیات روی گروه سامبا.",
                request_data=request_data,
                save_to_db=save_to_db
            )

class SambaSharepointView(APIView):
    """مدیریت مسیرهای اشتراکی سامبا."""

    @extend_schema(
        parameters=[
            OpenApiParameter(name="sharepoint_name", type=str, location="path", required=False),
            ParamAll, ParamProperty,
            OpenApiParameter(name="only_custom", type=bool, required=False, default="false",
                             description="فقط مسیرهای ایجادشده توسط مدیر"),
            OpenApiParameter(name="only_active", type=bool, required=False, default="false",
                             description="فقط مسیرهای فعال (available=yes)")
        ] + QuerySaveToDB
    )
    def get(self, request: Request, sharepoint_name: Optional[str] = None) -> Response:
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        all_props = get_request_param(request, "all", bool, True)
        prop = get_request_param(request, "property", str, None)
        only_custom = get_request_param(request, "only_custom", bool, False)
        only_active = get_request_param(request, "only_active", bool, False)
        request_data = dict(request.query_params)

        try:
            manager = SambaManager()
            data = manager.get_samba_sharepoints(
                sharepoint_name=sharepoint_name,
                all_props=all_props,
                property_name=prop,
                only_custom_shares=only_custom,
                only_active_shares=only_active
            )
            if sharepoint_name and data is None:
                return StandardErrorResponse(
                    error_code="share_not_found",
                    error_message=f"مسیر اشتراکی '{sharepoint_name}' یافت نشد.",
                    status=404,
                    request_data=request_data,
                    save_to_db=save_to_db
                )
            return StandardResponse(
                data=data,
                message="اطلاعات مسیر(های) اشتراکی سامبا با موفقیت بازیابی شد.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                error_code="samba_share_fetch_failed",
                error_message="خطا در دریافت اطلاعات مسیر(های) اشتراکی سامبا.",
                request_data=request_data,
                save_to_db=save_to_db
            )

    @extend_schema(
        request={"application/json": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "مسیر فیزیکی"},
                "valid_users": {"type": "array", "items": {"type": "string"}},
                "valid_groups": {"type": "array", "items": {"type": "string"}},
                "read_only": {"type": "boolean", "default": False},
                "guest_ok": {"type": "boolean", "default": False},
                "browseable": {"type": "boolean", "default": True},
                "max_connections": {"type": "integer"},
                "create_mask": {"type": "string", "default": "0644"},
                "directory_mask": {"type": "string", "default": "0755"},
                "inherit_permissions": {"type": "boolean", "default": False},
                "expiration_time": {"type": "string", "description": "زمان انقضا (اختیاری)"},
                **BodyParameterSaveToDB["properties"]
            },
            "required": ["path"]
        }}
    )
    def post(self, request: Request, sharepoint_name: str) -> Response:
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        path = get_request_param(request, "path", str, None)
        if not path:
            return StandardErrorResponse(
                error_code="missing_path",
                error_message="مسیر فیزیکی (path) اجباری است.",
                status=400,
                request_data=dict(request.data),
                save_to_db=save_to_db
            )
        request_data = dict(request.data)

        try:
            manager = SambaManager()
            manager.create_samba_sharepoint(
                name=sharepoint_name,
                path=path,
                valid_users=get_request_param(request, "valid_users", list, None),
                valid_groups=get_request_param(request, "valid_groups", list, None),
                read_only=get_request_param(request, "read_only", bool, False),
                guest_ok=get_request_param(request, "guest_ok", bool, False),
                browseable=get_request_param(request, "browseable", bool, True),
                max_connections=get_request_param(request, "max_connections", int, None),
                create_mask=get_request_param(request, "create_mask", str, "0644"),
                directory_mask=get_request_param(request, "directory_mask", str, "0755"),
                inherit_permissions=get_request_param(request, "inherit_permissions", bool, False),
                expiration_time=get_request_param(request, "expiration_time", str, None),
            )
            return StandardResponse(
                message=f"مسیر اشتراکی '{sharepoint_name}' با موفقیت ایجاد شد.",
                request_data=request_data,
                save_to_db=save_to_db,
                status=201
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                error_code="samba_share_create_failed",
                error_message="خطا در ایجاد مسیر اشتراکی سامبا.",
                request_data=request_data,
                save_to_db=save_to_db
            )

    @extend_schema(
        request={"application/json": {"type": "object", "additionalProperties": {"type": "string"}}}
    )
    def put(self, request: Request, sharepoint_name: str) -> Response:
        """به‌روزرسانی تمام پراپرتی‌های یک مسیر اشتراکی."""
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.data)

        try:
            manager = SambaManager()
            manager.update_samba_sharepoint(sharepoint_name, **request_data)
            return StandardResponse(
                message=f"مسیر اشتراکی '{sharepoint_name}' با موفقیت به‌روزرسانی شد.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                error_code="samba_share_update_failed",
                error_message="خطا در به‌روزرسانی مسیر اشتراکی سامبا.",
                request_data=request_data,
                save_to_db=save_to_db
            )

    @extend_schema()
    def delete(self, request: Request, sharepoint_name: str) -> Response:
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)

        try:
            manager = SambaManager()
            manager.delete_samba_sharepoint(sharepoint_name)
            return StandardResponse(
                message=f"مسیر اشتراکی '{sharepoint_name}' با موفقیت حذف شد.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                error_code="samba_share_delete_failed",
                error_message="خطا در حذف مسیر اشتراکی سامبا.",
                request_data=request_data,
                save_to_db=save_to_db
            )