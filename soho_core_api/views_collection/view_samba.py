# soho_core_api/views/view_samba.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, inline_serializer
from rest_framework import serializers
from django.utils import timezone

# Core utilities
from pylibs import (
    get_request_param,
    build_standard_error_response,
    QuerySaveToDB,
    BodyParameterSaveToDB,
    StandardResponse,
    StandardErrorResponse,
    CLICommandError,
)
from pylibs.samba import SambaManager
from pylibs.mixins import (
    SambaUserValidationMixin,
    SambaGroupValidationMixin,
    SambaSharepointValidationMixin,
)

from soho_core_api.models import SambaUser, SambaGroup, SambaSharepoint

# ========== OpenAPI Parameters ==========
ParamProperty = OpenApiParameter(
    name="property", type=str, required=False,
    description='نام یک پراپرتی خاص (مثل "Logoff time") یا "all" برای دریافت تمام پراپرتی‌ها.',
    examples=[OpenApiExample("دریافت همه پراپرتی‌ها", value="all"),
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
ParamOnlyActive = OpenApiParameter(
    name="only_active", type=bool, required=False, default="false",
    description="فقط مسیرهای اشتراکی فعال (available=yes)"
)
ParamContainSystemGroups = OpenApiParameter(
    name="contain_system_groups", type=bool, required=False, default="true",
    description="شامل گروه‌های سیستمی باشد یا خیر"
)

# ========== Utility Sync Functions ==========
def _sync_samba_users_to_db(users: List[Dict[str, Any]]) -> None:
    """همگام‌سازی لیست کاربران سامبا با جدول دیتابیس."""
    for u in users:
        SambaUser.objects.update_or_create(
            username=u.get("Unix username", ""),
            defaults={
                "full_name": u.get("Full Name", ""),
                "account_flags": u.get("Account Flags", ""),
                "user_sid": u.get("User SID", ""),
                "primary_group_sid": u.get("Primary Group SID", ""),
                "home_directory": u.get("Home Directory", ""),
                "logon_script": u.get("Logon Script", ""),
                "profile_path": u.get("Profile Path", ""),
                "domain": u.get("Domain", ""),
                "logoff_time": u.get("Logoff time", ""),
                "password_last_set": u.get("Password last set", ""),
                "raw_data": u,
                "last_update": timezone.now(),
            }
        )

def _sync_samba_groups_to_db(groups: List[Dict[str, Any]]) -> None:
    """همگام‌سازی لیست گروه‌های سامبا با جدول دیتابیس."""
    for g in groups:
        SambaGroup.objects.update_or_create(
            name=g["name"],
            defaults={
                "gid": g.get("gid", ""),
                "members": g.get("members", []),
                "raw_data": g,
                "last_update": timezone.now(),
            }
        )

def _sync_samba_sharepoints_to_db(shares: List[Dict[str, Any]]) -> None:
    """همگام‌سازی لیست مسیرهای اشتراکی سامبا با جدول دیتابیس."""
    for s in shares:
        SambaSharepoint.objects.update_or_create(
            name=s["name"],
            defaults={
                "path": s.get("path", ""),
                "read_only": s.get("read only", "no").lower() == "yes",
                "guest_ok": s.get("guest ok", "no").lower() == "yes",
                "browseable": s.get("browseable", "yes").lower() == "yes",
                "available": s.get("available", "yes").lower() == "yes",
                "valid_users": [x.strip() for x in s.get("valid users", "").split(",")] if s.get("valid users") else [],
                "valid_groups": [x.strip() for x in s.get("valid groups", "").split(",")] if s.get("valid groups") else [],
                "max_connections": int(s["max connections"]) if s.get("max connections") else None,
                "create_mask": s.get("create mask", "0644"),
                "directory_mask": s.get("directory mask", "0755"),
                "inherit_permissions": s.get("inherit permissions", "no").lower() == "yes",
                "expiration_time": s.get("expiration_time", ""),
                "created_time": s.get("created_time", ""),
                "raw_data": s,
                "last_update": timezone.now(),
            }
        )

# ========== ViewSets ==========
class SambaUserViewSet(viewsets.ViewSet, SambaUserValidationMixin):
    """
    مدیریت کاربران سامبا از طریق API.
    """

    lookup_field = "username"

    @extend_schema(
        parameters=[ParamProperty] + QuerySaveToDB,
        responses={200: inline_serializer("SambaUserList", {"data": serializers.JSONField()})}
    )
    def list(self, request: Request) -> Response:
        """
        دریافت لیست تمام کاربران سامبا.
        """
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        prop_key = get_request_param(request, "property", str, None)
        if prop_key: prop_key = prop_key.strip()
        request_data = dict(request.query_params)
        try:
            manager = SambaManager()
            data = manager.get_samba_users()
            if prop_key and prop_key.lower() != "all":
                # ✅ فرمت خروجی: {"username": "...", "property": value}
                filtered = [{"username": u.get("Unix username"), prop_key: u.get(prop_key)} for u in data]
                data = filtered
            if save_to_db:
                # فقط در حالت all یا بدون prop، داده‌ها به دیتابیس ذخیره می‌شوند
                users_to_sync = data if not prop_key or prop_key.lower() == "all" else manager.get_samba_users()
                _sync_samba_users_to_db(users_to_sync)
            return StandardResponse(data=data, message="لیست کاربران سامبا با موفقیت بازیابی شد.",
                                    request_data=request_data, save_to_db=save_to_db)
        except Exception as exc:
            return build_standard_error_response(exc=exc, error_code="samba_user_fetch_failed",
                                                 error_message="خطا در دریافت اطلاعات کاربر(ها) سامبا.",
                                                 request_data=request_data, save_to_db=save_to_db)

    @extend_schema(
        parameters=[OpenApiParameter("username", str, "path", True), ParamProperty] + QuerySaveToDB,
        responses={200: inline_serializer("SambaUserDetail", {"data": serializers.JSONField()})}
    )
    def retrieve(self, request: Request, username: str) -> Response:
        """
        دریافت اطلاعات یک کاربر سامبا.
        """
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        prop_key = get_request_param(request, "property", str, None)
        if prop_key: prop_key = prop_key.strip()
        request_data = dict(request.query_params)
        try:
            manager = SambaManager()
            user_data = manager.get_samba_users(username=username)
            if user_data is None:
                return StandardErrorResponse("user_not_found", f"کاربر '{username}' یافت نشد.", 404, request_data, save_to_db)
            if save_to_db:
                _sync_samba_users_to_db([user_data])
            if prop_key and prop_key.lower() != "all":
                val = user_data.get(prop_key)
                if val is None:
                    return StandardErrorResponse("property_not_found", f"پراپرتی '{prop_key}' یافت نشد.", 404, request_data, save_to_db)
                # ✅ فرمت خروجی برای property خاص
                return StandardResponse({"username": username, prop_key: val}, request_data=request_data, save_to_db=save_to_db)
            return StandardResponse(user_data, request_data=request_data, save_to_db=save_to_db)
        except Exception as exc:
            return build_standard_error_response(exc=exc, error_code="samba_user_fetch_failed",
                                                 error_message="خطا در دریافت اطلاعات کاربر سامبا.",
                                                 request_data=request_data, save_to_db=save_to_db)

    @extend_schema(
        request={"type": "object", "properties": {
            "username": {"type": "string"},
            "password": {"type": "string"},
            "full_name": {"type": "string"},
            **BodyParameterSaveToDB["properties"]
        }, "required": ["username", "password"]},
        responses={201: StandardResponse}
    )
    def create(self, request: Request) -> Response:
        """
        ایجاد یک کاربر جدید سامبا.
        """
        username = request.data.get("username")
        if not username:
            return StandardErrorResponse("missing_username", "نام کاربر اجباری است.", 400, dict(request.data), False)
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.data)
        if err := self._validate_samba_username_format(username, save_to_db, request_data): return err
        if err := self._validate_samba_user_exists(username, save_to_db, request_data, False): return err
        if not (pw := get_request_param(request, "password", str)):
            return StandardErrorResponse("missing_password", "رمز عبور اجباری است.", 400, request_data, save_to_db)
        full_name = get_request_param(request, "full_name", str)
        exp = get_request_param(request, "expiration_date", str)
        try:
            SambaManager().create_samba_user(username, pw, full_name, exp)
            if save_to_db:
                user_data = SambaManager().get_samba_users(username=username)
                if user_data:
                    _sync_samba_users_to_db([user_data])
            return StandardResponse(status=201, message=f"کاربر '{username}' ایجاد شد.", request_data=request_data, save_to_db=save_to_db)
        except Exception as e:
            return build_standard_error_response(e, "samba_user_create_failed", "خطا در ایجاد کاربر", request_data, save_to_db)

    @extend_schema(
        methods=["PUT"],
        parameters=[OpenApiParameter("action", str, "query", True, enum=["enable", "disable", "change_password"])] + QuerySaveToDB,
        request={"type": "object", "properties": {"new_password": {"type": "string"}, **BodyParameterSaveToDB["properties"]}},
        responses={200: StandardResponse}
    )
    @action(detail=True, methods=["put"], url_path="update")
    def update_user(self, request: Request, username: str) -> Response:
        """
        به‌روزرسانی یک کاربر سامبا (فعال/غیرفعال یا تغییر رمز).
        """
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        action_name = get_request_param(request, "action", str)
        request_data = dict(request.data)
        if err := self._validate_samba_user_exists(username, save_to_db, request_data, True): return err
        try:
            m = SambaManager()
            if action_name == "enable":
                m.enable_samba_user(username)
                msg = f"کاربر '{username}' فعال شد."
            elif action_name == "disable":
                m.disable_samba_user(username)
                msg = f"کاربر '{username}' غیرفعال شد."
            elif action_name == "change_password":
                if not (np := get_request_param(request, "new_password", str)):
                    return StandardErrorResponse("missing_new_password", "رمز جدید اجباری است.", 400, request_data, save_to_db)
                m.change_samba_user_password(username, np)
                msg = "رمز عبور تغییر کرد."
            else:
                return StandardErrorResponse("invalid_action", "عملیات نامعتبر.", 400, request_data, save_to_db)
            if save_to_db:
                user_data = m.get_samba_users(username=username)
                if user_data:
                    _sync_samba_users_to_db([user_data])
            return StandardResponse(message=msg, request_data=request_data, save_to_db=save_to_db)
        except Exception as e:
            return build_standard_error_response(e, "samba_user_op_failed", "خطا در عملیات کاربر", request_data, save_to_db)

    @extend_schema(parameters=[OpenApiParameter("username", str, "path", True)] + QuerySaveToDB)
    def destroy(self, request: Request, username: str) -> Response:
        """
        حذف یک کاربر سامبا (هم از سامبا و هم از سیستم).
        """
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)
        if err := self._validate_samba_user_exists(username, save_to_db, request_data, True): return err
        try:
            m = SambaManager()
            m.delete_samba_user_from_samba_db(username)
            m.delete_samba_user_from_system(username)
            if save_to_db:
                SambaUser.objects.filter(username=username).delete()
            return StandardResponse(f"کاربر '{username}' حذف شد.", request_data=request_data, save_to_db=save_to_db)
        except Exception as e:
            return build_standard_error_response(e, "samba_del_sys_failed", "خطا در حذف از سیستم", request_data, save_to_db)


class SambaGroupViewSet(viewsets.ViewSet, SambaGroupValidationMixin):
    """
    مدیریت گروه‌های سامبا از طریق API.
    """
    lookup_field = "groupname"

    @extend_schema(
        parameters=[ParamProperty, ParamContainSystemGroups] + QuerySaveToDB
    )
    def list(self, request: Request) -> Response:
        """
        دریافت لیست تمام گروه‌های سامبا.
        """
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        prop_key = get_request_param(request, "property", str, None)
        if prop_key: prop_key = prop_key.strip()
        contain_sys = get_request_param(request, "contain_system_groups", bool, True)
        request_data = dict(request.query_params)
        try:
            m = SambaManager()
            data = m.get_samba_groups(contain_system_groups=contain_sys)
            if prop_key and prop_key.lower() != "all":
                filtered = [{"groupname": g["name"], prop_key: g.get(prop_key)} for g in data]
                data = filtered
            if save_to_db:
                full_data = m.get_samba_groups(contain_system_groups=contain_sys)
                _sync_samba_groups_to_db(full_data)
            return StandardResponse(data, request_data=request_data, save_to_db=save_to_db)
        except Exception as e:
            return build_standard_error_response(e, "samba_group_fetch_failed", "خطا در دریافت گروه‌ها", request_data, save_to_db)

    @extend_schema(
        parameters=[OpenApiParameter("groupname", str, "path", True), ParamProperty, ParamContainSystemGroups] + QuerySaveToDB
    )
    def retrieve(self, request: Request, groupname: str) -> Response:
        """
        دریافت اطلاعات یک گروه سامبا.
        """
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        prop_key = get_request_param(request, "property", str, None)
        if prop_key: prop_key = prop_key.strip()
        contain_sys = get_request_param(request, "contain_system_groups", bool, True)
        request_data = dict(request.query_params)
        try:
            m = SambaManager()
            g = m.get_samba_groups(groupname=groupname, contain_system_groups=contain_sys)
            if g is None:
                return StandardErrorResponse("group_not_found", f"گروه '{groupname}' یافت نشد.", 404, request_data, save_to_db)
            if save_to_db:
                _sync_samba_groups_to_db([g])
            if prop_key and prop_key.lower() != "all":
                val = g.get(prop_key)
                if val is None:
                    return StandardErrorResponse("property_not_found", f"پراپرتی '{prop_key}' یافت نشد.", 404, request_data, save_to_db)
                return StandardResponse({"groupname": groupname, prop_key: val}, request_data=request_data, save_to_db=save_to_db)
            return StandardResponse(g, request_data=request_data, save_to_db=save_to_db)
        except Exception as e:
            return build_standard_error_response(e, "samba_group_fetch_failed", "خطا در دریافت گروه", request_data, save_to_db)

    @extend_schema(
        request={"type": "object", "properties": {
            "groupname": {"type": "string"},
            **BodyParameterSaveToDB["properties"]
        }, "required": ["groupname"]}
    )
    def create(self, request: Request) -> Response:
        """
        ایجاد یک گروه جدید سامبا.
        """
        groupname = request.data.get("groupname")
        if not groupname:
            return StandardErrorResponse("missing_groupname", "نام گروه اجباری است.", 400, dict(request.data), False)
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.data)
        if err := self._validate_samba_groupname_format(groupname, save_to_db, request_data): return err
        if err := self._validate_samba_group_exists(groupname, save_to_db, request_data, False): return err
        try:
            SambaManager().create_samba_group(groupname)
            if save_to_db:
                g = SambaManager().get_samba_groups(groupname=groupname)
                if g:
                    _sync_samba_groups_to_db([g])
            return StandardResponse(status=201, message=f"گروه '{groupname}' ایجاد شد.", request_data=request_data, save_to_db=save_to_db)
        except Exception as e:
            return build_standard_error_response(e, "samba_group_create_failed", "خطا در ایجاد گروه", request_data, save_to_db)

    @extend_schema(
        methods=["PUT"],
        parameters=[OpenApiParameter("action", str, "query", True, enum=["add_user", "remove_user"])] + QuerySaveToDB,
        request={"type": "object", "properties": {"username": {"type": "string"}, **BodyParameterSaveToDB["properties"]}, "required": ["username"]}
    )
    @action(detail=True, methods=["put"], url_path="update")
    def update_group(self, request: Request, groupname: str) -> Response:
        """
        به‌روزرسانی یک گروه سامبا (اضافه/حذف کاربر).
        """
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        action_name = get_request_param(request, "action", str)
        username = get_request_param(request, "username", str)
        request_data = dict(request.data)
        if err := self._validate_samba_group_exists(groupname, save_to_db, request_data, True): return err
        if not username:
            return StandardErrorResponse("missing_username", "نام کاربر اجباری است.", 400, request_data, save_to_db)
        if err := SambaUserValidationMixin()._validate_samba_user_exists(username, save_to_db, request_data, True): return err
        try:
            m = SambaManager()
            if action_name == "add_user":
                m.add_user_to_group(username, groupname)
                msg = f"کاربر '{username}' به گروه اضافه شد."
            elif action_name == "remove_user":
                m.remove_user_from_group(username, groupname)
                msg = f"کاربر '{username}' از گروه حذف شد."
            else:
                return StandardErrorResponse("invalid_action", "عملیات نامعتبر.", 400, request_data, save_to_db)
            if save_to_db:
                g = m.get_samba_groups(groupname=groupname)
                if g:
                    _sync_samba_groups_to_db([g])
            return StandardResponse(msg, request_data=request_data, save_to_db=save_to_db)
        except Exception as e:
            return build_standard_error_response(e, "samba_group_op_failed", "خطا در عملیات گروه", request_data, save_to_db)

    @extend_schema(parameters=[OpenApiParameter("groupname", str, "path", True)] + QuerySaveToDB)
    def destroy(self, request: Request, groupname: str) -> Response:
        """
        حذف یک گروه سامبا.
        """
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)
        if err := self._validate_samba_group_exists(groupname, save_to_db, request_data, True): return err
        try:
            SambaManager().delete_samba_group(groupname)
            if save_to_db:
                SambaGroup.objects.filter(name=groupname).delete()
            return StandardResponse(f"گروه '{groupname}' حذف شد.", request_data=request_data, save_to_db=save_to_db)
        except Exception as e:
            return build_standard_error_response(e, "samba_group_del_failed", "خطا در حذف گروه", request_data, save_to_db)


class SambaSharepointViewSet(viewsets.ViewSet, SambaSharepointValidationMixin):
    """
    مدیریت مسیرهای اشتراکی سامبا از طریق API.
    """
    lookup_field = "sharepoint_name"

    @extend_schema(
        parameters=[ParamProperty, ParamOnlyActive] + QuerySaveToDB
    )
    def list(self, request: Request) -> Response:
        """
        دریافت لیست تمام مسیرهای اشتراکی سامبا.
        """
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        prop_key = get_request_param(request, "property", str, None)
        if prop_key: prop_key = prop_key.strip()
        only_active = get_request_param(request, "only_active", bool, False)
        request_data = dict(request.query_params)
        try:
            m = SambaManager()
            data = m.get_samba_sharepoints(only_active_shares=only_active)
            if prop_key and prop_key.lower() != "all":
                filtered = [{"sharepoint_name": s["name"], prop_key: s.get(prop_key)} for s in data]
                data = filtered
            if save_to_db:
                full_data = m.get_samba_sharepoints(only_active_shares=only_active)
                _sync_samba_sharepoints_to_db(full_data)
            return StandardResponse(data, request_data=request_data, save_to_db=save_to_db)
        except Exception as e:
            return build_standard_error_response(e, "samba_share_fetch_failed", "خطا در دریافت مسیرها", request_data, save_to_db)

    @extend_schema(
        parameters=[OpenApiParameter("sharepoint_name", str, "path", True), ParamProperty, ParamOnlyActive] + QuerySaveToDB
    )
    def retrieve(self, request: Request, sharepoint_name: str) -> Response:
        """
        دریافت اطلاعات یک مسیر اشتراکی سامبا.
        """
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        prop_key = get_request_param(request, "property", str, None)
        if prop_key: prop_key = prop_key.strip()
        only_active = get_request_param(request, "only_active", bool, False)
        request_data = dict(request.query_params)
        try:
            m = SambaManager()
            s = m.get_samba_sharepoints(sharepoint_name=sharepoint_name, only_active_shares=only_active)
            if s is None:
                return StandardErrorResponse("share_not_found", f"مسیر '{sharepoint_name}' یافت نشد.", 404, request_data, save_to_db)
            if save_to_db:
                _sync_samba_sharepoints_to_db([s])
            if prop_key and prop_key.lower() != "all":
                val = s.get(prop_key)
                if val is None:
                    return StandardErrorResponse("property_not_found", f"پراپرتی '{prop_key}' یافت نشد.", 404, request_data, save_to_db)
                return StandardResponse({"sharepoint_name": sharepoint_name, prop_key: val}, request_data=request_data, save_to_db=save_to_db)
            return StandardResponse(s, request_data=request_data, save_to_db=save_to_db)
        except Exception as e:
            return build_standard_error_response(e, "samba_share_fetch_failed", "خطا در دریافت مسیر", request_data, save_to_db)

    @extend_schema(
        request={"type": "object", "properties": {
            "sharepoint_name": {"type": "string"},
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
            "available": {"type": "boolean", "default": True},
            **BodyParameterSaveToDB["properties"]
        }, "required": ["sharepoint_name", "path"]}
    )
    def create(self, request: Request) -> Response:
        """
        ایجاد یک مسیر اشتراکی جدید سامبا.
        """
        sharepoint_name = request.data.get("sharepoint_name")
        if not sharepoint_name:
            return StandardErrorResponse("missing_sharepoint_name", "نام مسیر اشتراکی اجباری است.", 400, dict(request.data), False)
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.data)
        if err := self._validate_samba_sharepoint_name_format(sharepoint_name, save_to_db, request_data): return err
        if err := self._validate_samba_sharepoint_exists(sharepoint_name, save_to_db, request_data, False): return err
        if not (path := get_request_param(request, "path", str)):
            return StandardErrorResponse("missing_path", "مسیر اجباری است.", 400, request_data, save_to_db)
        try:
            SambaManager().create_samba_sharepoint(
                name=sharepoint_name, path=path,
                valid_users=get_request_param(request, "valid_users", list),
                valid_groups=get_request_param(request, "valid_groups", list),
                read_only=get_request_param(request, "read_only", bool, False),
                guest_ok=get_request_param(request, "guest_ok", bool, False),
                browseable=get_request_param(request, "browseable", bool, True),
                max_connections=get_request_param(request, "max_connections", int),
                create_mask=get_request_param(request, "create_mask", str, "0644"),
                directory_mask=get_request_param(request, "directory_mask", str, "0755"),
                inherit_permissions=get_request_param(request, "inherit_permissions", bool, False),
                expiration_time=get_request_param(request, "expiration_time", str),
                available=get_request_param(request, "available", bool, True),
            )
            if save_to_db:
                s = SambaManager().get_samba_sharepoints(sharepoint_name=sharepoint_name)
                if s:
                    _sync_samba_sharepoints_to_db([s])
            return StandardResponse(status=201, message=f"مسیر '{sharepoint_name}' ایجاد شد.", request_data=request_data, save_to_db=save_to_db)
        except Exception as e:
            return build_standard_error_response(e, "samba_share_create_failed", "خطا در ایجاد مسیر", request_data, save_to_db)

    @extend_schema(
        methods=["PUT"],
        request={"type": "object", "additionalProperties": {"type": "string"}, "properties": BodyParameterSaveToDB["properties"]}
    )
    @action(detail=True, methods=["put"], url_path="update")
    def update_sharepoint(self, request: Request, sharepoint_name: str) -> Response:
        """
        به‌روزرسانی یک مسیر اشتراکی سامبا.
        """
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.data)
        if err := self._validate_samba_sharepoint_exists(sharepoint_name, save_to_db, request_data, True): return err
        try:
            SambaManager().update_samba_sharepoint(sharepoint_name, **request_data)
            if save_to_db:
                s = SambaManager().get_samba_sharepoints(sharepoint_name=sharepoint_name)
                if s:
                    _sync_samba_sharepoints_to_db([s])
            return StandardResponse(f"مسیر '{sharepoint_name}' به‌روزرسانی شد.", request_data=request_data, save_to_db=save_to_db)
        except Exception as e:
            return build_standard_error_response(e, "samba_share_update_failed", "خطا در به‌روزرسانی", request_data, save_to_db)

    @extend_schema(parameters=[OpenApiParameter("sharepoint_name", str, "path", True)] + QuerySaveToDB)
    def destroy(self, request: Request, sharepoint_name: str) -> Response:
        """
        حذف یک مسیر اشتراکی سامبا.
        """
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)
        if err := self._validate_samba_sharepoint_exists(sharepoint_name, save_to_db, request_data, True): return err
        try:
            SambaManager().delete_samba_sharepoint(sharepoint_name)
            if save_to_db:
                SambaSharepoint.objects.filter(name=sharepoint_name).delete()
            return StandardResponse(f"مسیر '{sharepoint_name}' حذف شد.", request_data=request_data, save_to_db=save_to_db)
        except Exception as e:
            return build_standard_error_response(e, "samba_share_del_failed", "خطا در حذف مسیر", request_data, save_to_db)