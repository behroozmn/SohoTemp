# soho_core_api/views/view_samba.py
from __future__ import annotations
from typing import Any, Dict, Optional, List
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from pylibs import (get_request_param, build_standard_error_response, QuerySaveToDB, BodyParameterSaveToDB, StandardResponse, StandardErrorResponse, )
from pylibs.samba import SambaManager
from pylibs.mixins import (SambaUserValidationMixin, SambaGroupValidationMixin, SambaSharepointValidationMixin, )
from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

# OpenAPI Parameters مشترک
ParamProperty = OpenApiParameter(name="property", type=str, required=False,
                                 description='نام یک پراپرتی خاص (مثل "Domain") یا "all" برای دریافت تمام پراپرتی‌ها. اگر ارسال نشود، معادل "all" در نظر گرفته می‌شود.',
                                 examples=[OpenApiExample("مثال all", value="all"),
                                           OpenApiExample("مثال پراپرتی خاص", value="Full Name"), ])
ParamOnlyCustom = OpenApiParameter(name="only_custom", type=bool, required=False, default="false", description="فقط موارد ایجادشده توسط مدیر سیستم")
ParamOnlyShared = OpenApiParameter(name="only_shared", type=bool, required=False, default="false", description="فقط مواردی که در smb.conf استفاده شده‌اند")
ParamOnlyActive = OpenApiParameter(name="only_active", type=bool, required=False, default="false", description="فقط مسیرهای اشتراکی فعال (available=yes)")


# ========== User View ==========
class SambaUserView(APIView, SambaUserValidationMixin):
    @extend_schema(
        parameters=[OpenApiParameter(name="username", type=str, location="path", required=False),
                    ParamProperty, ParamOnlyCustom, ParamOnlyShared, ] + QuerySaveToDB,
        responses={200: inline_serializer("SambaUserResponse", {"data": serializers.JSONField()})}
    )
    def get(self, request: Request, username: Optional[str] = None) -> Response:
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        prop = get_request_param(request, "property", str, None)
        only_custom = get_request_param(request, "only_custom", bool, False)
        only_shared = get_request_param(request, "only_shared", bool, False)
        request_data = dict(request.query_params)

        try:
            manager = SambaManager()
            data = manager.get_samba_users(
                username=username,
                all_props=(not prop or prop.lower() == "all"),
                property_name=prop if prop and prop.lower() != "all" else None,
                only_custom_users=only_custom,
                only_shared_users=only_shared,
            )

            if username:
                error_resp = self._validate_samba_user_exists(username, save_to_db, request_data, must_exist=True)
                if error_resp:
                    return error_resp

            # اگر prop خاصی درخواست شده باشد و data dict باشد
            if prop and prop.lower() != "all" and isinstance(data, dict):
                value = data.get(prop)
                if value is None:
                    return StandardErrorResponse(
                        error_code="property_not_found",
                        error_message=f"پراپرتی '{prop}' برای کاربر '{username or 'all'}' یافت نشد.",
                        status=404,
                        request_data=request_data,
                        save_to_db=save_to_db,
                    )
                data = {prop: value}

            return StandardResponse(
                data=data,
                message="اطلاعات کاربر(ها) سامبا با موفقیت بازیابی شد.",
                request_data=request_data,
                save_to_db=save_to_db,
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                error_code="samba_user_fetch_failed",
                error_message="خطا در دریافت اطلاعات کاربر(ها) سامبا.",
                request_data=request_data,
                save_to_db=save_to_db,
            )

    @extend_schema(
        request={"application/json": {
            "type": "object",
            "properties": {
                "password": {"type": "string", "description": "رمز عبور کاربر"},
                "full_name": {"type": "string"},
                "expiration_date": {"type": "string", "format": "date"},
                **BodyParameterSaveToDB["properties"]
            },
            "required": ["password"]
        }},
        responses={201: StandardResponse}
    )
    def post(self, request: Request, username: str) -> Response:
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.data)

        error = self._validate_samba_username_format(username, save_to_db, request_data)
        if error: return error
        error = self._validate_samba_user_exists(username, save_to_db, request_data, must_exist=False)
        if error: return error

        password = get_request_param(request, "password", str, None)
        error = self._validate_samba_password_provided(password, save_to_db, request_data, "password")
        if error: return error

        full_name = get_request_param(request, "full_name", str, None)
        expiration = get_request_param(request, "expiration_date", str, None)

        try:
            SambaManager().create_samba_user(username, password, full_name, expiration)
            return StandardResponse(
                message=f"کاربر سامبا '{username}' با موفقیت ایجاد شد.",
                request_data=request_data,
                save_to_db=save_to_db,
                status=201,
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                error_code="samba_user_create_failed",
                error_message="خطا در ایجاد کاربر سامبا.",
                request_data=request_data,
                save_to_db=save_to_db,
            )


# ========== Group View ==========
class SambaGroupView(APIView, SambaGroupValidationMixin):
    @extend_schema(
        parameters=[
                       OpenApiParameter(name="groupname", type=str, location="path", required=False),
                       ParamProperty,
                       ParamOnlyCustom,
                       ParamOnlyShared,
                   ] + QuerySaveToDB
    )
    def get(self, request: Request, groupname: Optional[str] = None) -> Response:
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        prop = get_request_param(request, "property", str, None)
        only_custom = get_request_param(request, "only_custom", bool, False)
        only_shared = get_request_param(request, "only_shared", bool, False)
        request_data = dict(request.query_params)

        try:
            manager = SambaManager()
            data = manager.get_samba_groups(
                groupname=groupname,
                all_props=(not prop or prop.lower() == "all"),
                property_name=prop if prop and prop.lower() != "all" else None,
                only_custom_groups=only_custom,
                only_shared_groups=only_shared,
            )

            if groupname:
                error_resp = self._validate_samba_group_exists(groupname, save_to_db, request_data, must_exist=True)
                if error_resp:
                    return error_resp

            if prop and prop.lower() != "all" and isinstance(data, dict):
                value = data.get(prop)
                if value is None:
                    return StandardErrorResponse(
                        error_code="property_not_found",
                        error_message=f"پراپرتی '{prop}' برای گروه '{groupname or 'all'}' یافت نشد.",
                        status=404,
                        request_data=request_data,
                        save_to_db=save_to_db,
                    )
                data = {prop: value}

            return StandardResponse(
                data=data,
                message="اطلاعات گروه(ها) سامبا با موفقیت بازیابی شد.",
                request_data=request_data,
                save_to_db=save_to_db,
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                error_code="samba_group_fetch_failed",
                error_message="خطا در دریافت اطلاعات گروه(ها) سامبا.",
                request_data=request_data,
                save_to_db=save_to_db,
            )

    @extend_schema(
        request={"application/json": {
            "type": "object",
            "properties": {**BodyParameterSaveToDB["properties"]},
            "required": []
        }}
    )
    def post(self, request: Request, groupname: str) -> Response:
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.data)

        error = self._validate_samba_groupname_format(groupname, save_to_db, request_data)
        if error: return error
        error = self._validate_samba_group_exists(groupname, save_to_db, request_data, must_exist=False)
        if error: return error

        try:
            SambaManager().create_samba_group(groupname)
            return StandardResponse(
                message=f"گروه سامبا '{groupname}' با موفقیت ایجاد شد.",
                request_data=request_data,
                save_to_db=save_to_db,
                status=201,
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                error_code="samba_group_create_failed",
                error_message="خطا در ایجاد گروه سامبا.",
                request_data=request_data,
                save_to_db=save_to_db,
            )


# ========== Sharepoint View ==========
class SambaSharepointView(APIView, SambaSharepointValidationMixin):
    @extend_schema(
        parameters=[
                       OpenApiParameter(name="sharepoint_name", type=str, location="path", required=False),
                       ParamProperty,
                       ParamOnlyCustom,
                       ParamOnlyActive,
                   ] + QuerySaveToDB
    )
    def get(self, request: Request, sharepoint_name: Optional[str] = None) -> Response:
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        prop = get_request_param(request, "property", str, None)
        only_custom = get_request_param(request, "only_custom", bool, False)
        only_active = get_request_param(request, "only_active", bool, False)
        request_data = dict(request.query_params)

        try:
            manager = SambaManager()
            data = manager.get_samba_sharepoints(
                sharepoint_name=sharepoint_name,
                all_props=(not prop or prop.lower() == "all"),
                property_name=prop if prop and prop.lower() != "all" else None,
                only_custom_shares=only_custom,
                only_active_shares=only_active,
            )

            if sharepoint_name:
                error_resp = self._validate_samba_sharepoint_exists(sharepoint_name, save_to_db, request_data, must_exist=True)
                if error_resp:
                    return error_resp

            if prop and prop.lower() != "all" and isinstance(data, dict):
                value = data.get(prop)
                if value is None:
                    return StandardErrorResponse(
                        error_code="property_not_found",
                        error_message=f"پراپرتی '{prop}' برای مسیر اشتراکی '{sharepoint_name or 'all'}' یافت نشد.",
                        status=404,
                        request_data=request_data,
                        save_to_db=save_to_db,
                    )
                data = {prop: value}

            return StandardResponse(
                data=data,
                message="اطلاعات مسیر(های) اشتراکی سامبا با موفقیت بازیابی شد.",
                request_data=request_data,
                save_to_db=save_to_db,
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                error_code="samba_share_fetch_failed",
                error_message="خطا در دریافت اطلاعات مسیر(های) اشتراکی سامبا.",
                request_data=request_data,
                save_to_db=save_to_db,
            )

    @extend_schema(
        request={"application/json": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "valid_users": {"type": "array", "items": {"type": "string"}},
                "valid_groups": {"type": "array", "items": {"type": "string"}},
                "read_only": {"type": "boolean", "default": False},
                "guest_ok": {"type": "boolean", "default": False},
                "browseable": {"type": "boolean", "default": True},
                "max_connections": {"type": "integer"},
                "create_mask": {"type": "string", "default": "0644"},
                "directory_mask": {"type": "string", "default": "0755"},
                "inherit_permissions": {"type": "boolean", "default": False},
                "expiration_time": {"type": "string"},
                **BodyParameterSaveToDB["properties"]
            },
            "required": ["path"]
        }}
    )
    def post(self, request: Request, sharepoint_name: str) -> Response:
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.data)

        error = self._validate_samba_sharepoint_name_format(sharepoint_name, save_to_db, request_data)
        if error: return error
        error = self._validate_samba_sharepoint_exists(sharepoint_name, save_to_db, request_data, must_exist=False)
        if error: return error

        path = get_request_param(request, "path", str, None)
        error = self._validate_samba_path_provided(path, save_to_db, request_data)
        if error: return error

        try:
            SambaManager().create_samba_sharepoint(
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
                status=201,
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                error_code="samba_share_create_failed",
                error_message="خطا در ایجاد مسیر اشتراکی سامبا.",
                request_data=request_data,
                save_to_db=save_to_db,
            )

    @extend_schema(
        request={"application/json": {"type": "object", "additionalProperties": {"type": "string"}}}
    )
    def put(self, request: Request, sharepoint_name: str) -> Response:
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.data)

        error = self._validate_samba_sharepoint_exists(sharepoint_name, save_to_db, request_data, must_exist=True)
        if error: return error

        try:
            SambaManager().update_samba_sharepoint(sharepoint_name, **request_data)
            return StandardResponse(
                message=f"مسیر اشتراکی '{sharepoint_name}' با موفقیت به‌روزرسانی شد.",
                request_data=request_data,
                save_to_db=save_to_db,
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                error_code="samba_share_update_failed",
                error_message="خطا در به‌روزرسانی مسیر اشتراکی سامبا.",
                request_data=request_data,
                save_to_db=save_to_db,
            )

    @extend_schema()
    def delete(self, request: Request, sharepoint_name: str) -> Response:
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)

        error = self._validate_samba_sharepoint_exists(sharepoint_name, save_to_db, request_data, must_exist=True)
        if error: return error

        try:
            SambaManager().delete_samba_sharepoint(sharepoint_name)
            return StandardResponse(
                message=f"مسیر اشتراکی '{sharepoint_name}' با موفقیت حذف شد.",
                request_data=request_data,
                save_to_db=save_to_db,
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                error_code="samba_share_delete_failed",
                error_message="خطا در حذف مسیر اشتراکی سامبا.",
                request_data=request_data,
                save_to_db=save_to_db,
            )
