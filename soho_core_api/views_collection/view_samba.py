# soho_core_api/views/view_samba.py
from __future__ import annotations
from typing import Any, Dict, Optional, List
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
from pylibs.mixins import (
    SambaUserValidationMixin,
    SambaGroupValidationMixin,
    SambaSharepointValidationMixin,
)
from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

# OpenAPI Parameters مشترک
ParamProperty = OpenApiParameter(name="property", type=str, required=False,
                                 description='نام یک پراپرتی خاص (مثل "Logoff time") یا "all" برای دریافت تمام پراپرتی‌ها. اگر ارسال نشود، معادل "all" در نظر گرفته می‌شود.',
                                 examples=[
                                     OpenApiExample("دریافت همه پراپرتی‌ها", value="all"),
                                     OpenApiExample("نام کاربری یونیکس", value="Unix username"),
                                     OpenApiExample("نام کاربری ویندوز (NT)", value="NT username"),
                                     OpenApiExample("پرچم‌های حساب", value="Account Flags"),
                                     OpenApiExample("شناسه کاربر (User SID)", value="User SID"),
                                     OpenApiExample("شناسه گروه اصلی", value="Primary Group SID"),
                                     OpenApiExample("نام کامل", value="Full Name"),
                                     OpenApiExample("مسیر home", value="Home Directory"),
                                     OpenApiExample("درایو home", value="HomeDir Drive"),
                                     OpenApiExample("اسکریپت ورود", value="Logon Script"),
                                     OpenApiExample("مسیر پروفایل", value="Profile Path"),
                                     OpenApiExample("دامنه", value="Domain"),
                                     OpenApiExample("توضیحات حساب", value="Account desc"),
                                     OpenApiExample("ورک‌استیشن‌های مجاز", value="Workstations"),
                                     OpenApiExample("اطلاعات تماس", value="Munged dial"),
                                     OpenApiExample("زمان آخرین ورود", value="Logon time"),
                                     OpenApiExample("زمان انقضا (Logoff time)", value="Logoff time"),
                                     OpenApiExample("زمان حذف اجباری", value="Kickoff time"),
                                     OpenApiExample("آخرین تغییر رمز", value="Password last set"),
                                     OpenApiExample("امکان تغییر رمز", value="Password can change"),
                                     OpenApiExample("تاریخ اجباری تغییر رمز", value="Password must change"),
                                     OpenApiExample("آخرین رمز اشتباه", value="Last bad password"),
                                     OpenApiExample("تعداد رمزهای اشتباه", value="Bad password count"),
                                     OpenApiExample("ساعت‌های مجاز ورود", value="Logon hours"), ])
ParamOnlyCustom = OpenApiParameter(name="only_custom", type=bool, required=False, default="false", description="فقط موارد ایجادشده توسط مدیر سیستم")
ParamOnlyShared = OpenApiParameter(name="only_shared", type=bool, required=False, default="false", description="فقط مواردی که در smb.conf استفاده شده‌اند")
ParamOnlyActive = OpenApiParameter(name="only_active", type=bool, required=False, default="false", description="فقط مسیرهای اشتراکی فعال (available=yes)")


# ========== User View ==========
class SambaUserView(APIView, SambaUserValidationMixin):
    @extend_schema(
        parameters=[OpenApiParameter(name="username", type=str, location="path", required=False), ParamProperty, ParamOnlyCustom, ParamOnlyShared, ] + QuerySaveToDB,
        responses={200: inline_serializer("SambaUserResponse", {"data": serializers.JSONField()})})
    def get(self, request: Request, username: Optional[str] = None) -> Response:
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        prop_key = get_request_param(request, "property", str, None)
        if prop_key:
            prop_key = prop_key.strip()
        only_custom = get_request_param(request, "only_custom", bool, False)
        only_shared = get_request_param(request, "only_shared", bool, False)
        request_data = dict(request.query_params)

        try:
            manager = SambaManager()

            if username:
                # --- اعتبارسنجی وجود کاربر ---
                error_resp = self._validate_samba_user_exists(username, save_to_db, request_data, must_exist=True)
                if error_resp:
                    return error_resp

                # --- دریافت پراپرتی خاص ---
                if prop_key and prop_key.lower() != "all":
                    value = manager.get_samba_user_property(username, prop_key)
                    if value is None:
                        return StandardErrorResponse(
                            request_data=request_data,
                            save_to_db=save_to_db,
                            status=404,
                            error_code="property_not_found",
                            error_message=f"پراپرتی '{prop_key}' در کاربر '{username}' یافت نشد."
                        )
                    return StandardResponse(
                        data={prop_key: value},
                        request_data=request_data,
                        save_to_db=save_to_db,
                        message=f"پراپرتی '{prop_key}' با موفقیت بازیابی شد."
                    )
                else:
                    # --- دریافت تمام اطلاعات کاربر ---
                    data = manager.get_samba_users(
                        username=username,
                        only_custom_users=only_custom,
                        only_shared_users=only_shared,
                    )
                    if data is None:
                        return StandardErrorResponse(
                            request_data=request_data,
                            save_to_db=save_to_db,
                            status=404,
                            error_code="user_not_found",
                            error_message=f"کاربر '{username}' یافت نشد."
                        )
                    return StandardResponse(
                        data=data,
                        request_data=request_data,
                        save_to_db=save_to_db,
                        message="جزئیات کاربر سامبا با موفقیت بازیابی شد."
                    )
            else:
                # --- لیست کاربران ---
                data = manager.get_samba_users(
                    only_custom_users=only_custom,
                    only_shared_users=only_shared,
                )
                if prop_key and prop_key.lower() != "all":
                    # فیلتر لیست بر اساس پراپرتی
                    filtered = []
                    for user_dict in data:
                        if isinstance(user_dict, dict):
                            uname = user_dict.get("Unix username")
                            if uname is not None:
                                value = user_dict.get(prop_key)
                                filtered.append({"username": uname, prop_key: value})
                            else:
                                filtered.append({"username": "unknown", prop_key: None})
                        else:
                            filtered.append({"username": "unknown", prop_key: None})
                    data = filtered

                return StandardResponse(
                    data=data,
                    request_data=request_data,
                    save_to_db=save_to_db,
                    message="لیست کاربران سامبا با موفقیت بازیابی شد."
                )

        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                request_data=request_data,
                save_to_db=save_to_db,
                error_code="samba_user_fetch_failed",
                error_message="خطا در دریافت اطلاعات کاربر(ها) سامبا."
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
        prop_key = get_request_param(request, "property", str, None)
        if prop_key:
            prop_key = prop_key.strip()
        only_custom = get_request_param(request, "only_custom", bool, False)
        only_shared = get_request_param(request, "only_shared", bool, False)
        request_data = dict(request.query_params)

        try:
            manager = SambaManager()

            if groupname:
                error_resp = self._validate_samba_group_exists(groupname, save_to_db, request_data, must_exist=True)
                if error_resp:
                    return error_resp

                if prop_key and prop_key.lower() != "all":
                    value = manager.get_samba_group_property(groupname, prop_key)
                    if value is None:
                        return StandardErrorResponse(
                            request_data=request_data,
                            save_to_db=save_to_db,
                            status=404,
                            error_code="property_not_found",
                            error_message=f"پراپرتی '{prop_key}' در گروه '{groupname}' یافت نشد."
                        )
                    return StandardResponse(
                        data={prop_key: value},
                        request_data=request_data,
                        save_to_db=save_to_db,
                        message=f"پراپرتی '{prop_key}' با موفقیت بازیابی شد."
                    )
                else:
                    data = manager.get_samba_groups(
                        groupname=groupname,
                        only_custom_groups=only_custom,
                        only_shared_groups=only_shared,
                    )
                    if data is None:
                        return StandardErrorResponse(
                            request_data=request_data,
                            save_to_db=save_to_db,
                            status=404,
                            error_code="group_not_found",
                            error_message=f"گروه '{groupname}' یافت نشد."
                        )
                    return StandardResponse(
                        data=data,
                        request_data=request_data,
                        save_to_db=save_to_db,
                        message="جزئیات گروه سامبا با موفقیت بازیابی شد."
                    )
            else:
                data = manager.get_samba_groups(
                    only_custom_groups=only_custom,
                    only_shared_groups=only_shared,
                )
                if prop_key and prop_key.lower() != "all":
                    filtered = []
                    for group_dict in data:
                        if isinstance(group_dict, dict):
                            gname = group_dict.get("name")
                            if gname is not None:
                                value = group_dict.get(prop_key)
                                filtered.append({"groupname": gname, prop_key: value})
                            else:
                                filtered.append({"groupname": "unknown", prop_key: None})
                        else:
                            filtered.append({"groupname": "unknown", prop_key: None})
                    data = filtered

                return StandardResponse(
                    data=data,
                    request_data=request_data,
                    save_to_db=save_to_db,
                    message="لیست گروه‌های سامبا با موفقیت بازیابی شد."
                )

        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                request_data=request_data,
                save_to_db=save_to_db,
                error_code="samba_group_fetch_failed",
                error_message="خطا در دریافت اطلاعات گروه(ها) سامبا."
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
        prop_key = get_request_param(request, "property", str, None)
        if prop_key:
            prop_key = prop_key.strip()
        only_custom = get_request_param(request, "only_custom", bool, False)
        only_active = get_request_param(request, "only_active", bool, False)
        request_data = dict(request.query_params)

        try:
            manager = SambaManager()

            if sharepoint_name:
                error_resp = self._validate_samba_sharepoint_exists(sharepoint_name, save_to_db, request_data, must_exist=True)
                if error_resp:
                    return error_resp

                if prop_key and prop_key.lower() != "all":
                    value = manager.get_samba_sharepoint_property(sharepoint_name, prop_key)
                    if value is None:
                        return StandardErrorResponse(
                            request_data=request_data,
                            save_to_db=save_to_db,
                            status=404,
                            error_code="property_not_found",
                            error_message=f"پراپرتی '{prop_key}' در مسیر اشتراکی '{sharepoint_name}' یافت نشد."
                        )
                    return StandardResponse(
                        data={prop_key: value},
                        request_data=request_data,
                        save_to_db=save_to_db,
                        message=f"پراپرتی '{prop_key}' با موفقیت بازیابی شد."
                    )
                else:
                    data = manager.get_samba_sharepoints(
                        sharepoint_name=sharepoint_name,
                        only_custom_shares=only_custom,
                        only_active_shares=only_active,
                    )
                    if data is None:
                        return StandardErrorResponse(
                            request_data=request_data,
                            save_to_db=save_to_db,
                            status=404,
                            error_code="share_not_found",
                            error_message=f"مسیر اشتراکی '{sharepoint_name}' یافت نشد."
                        )
                    return StandardResponse(
                        data=data,
                        request_data=request_data,
                        save_to_db=save_to_db,
                        message="جزئیات مسیر اشتراکی سامبا با موفقیت بازیابی شد."
                    )
            else:
                data = manager.get_samba_sharepoints(
                    only_custom_shares=only_custom,
                    only_active_shares=only_active,
                )
                if prop_key and prop_key.lower() != "all":
                    filtered = []
                    for share_dict in data:
                        if isinstance(share_dict, dict):
                            sname = share_dict.get("name")
                            if sname is not None:
                                value = share_dict.get(prop_key)
                                filtered.append({"sharepoint_name": sname, prop_key: value})
                            else:
                                filtered.append({"sharepoint_name": "unknown", prop_key: None})
                        else:
                            filtered.append({"sharepoint_name": "unknown", prop_key: None})
                    data = filtered

                return StandardResponse(
                    data=data,
                    request_data=request_data,
                    save_to_db=save_to_db,
                    message="لیست مسیرهای اشتراکی سامبا با موفقیت بازیابی شد."
                )

        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                request_data=request_data,
                save_to_db=save_to_db,
                error_code="samba_share_fetch_failed",
                error_message="خطا در دریافت اطلاعات مسیر(های) اشتراکی سامبا."
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
