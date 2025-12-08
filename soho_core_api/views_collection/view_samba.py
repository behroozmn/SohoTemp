# soho_core_api/views/view_samba.py
from __future__ import annotations
from typing import Any, Dict, List
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, inline_serializer
from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

# Core utilities
from pylibs import (get_request_param, build_standard_error_response, QuerySaveToDB, BodyParameterSaveToDB, StandardResponse, StandardErrorResponse, )
from pylibs.mixins import (SambaUserValidationMixin, SambaGroupValidationMixin, SambaSharepointValidationMixin, )
from pylibs.samba import SambaManager
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

# TODO:// ignore save_to_db  when create or delete or update

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
        save_to_db = get_request_param(request=request, param_name="save_to_db", return_type=bool, default=False)
        prop_key = get_request_param(request=request, param_name="property", return_type=str, default=None)
        if prop_key: prop_key = prop_key.strip()
        request_data = dict(request.query_params)
        try:
            manager = SambaManager()
            data = manager.get_samba_users()
            if prop_key and prop_key.lower() != "all":
                filtered = [{"username": u.get("Unix username"), prop_key: u.get(prop_key)} for u in data]
                data = filtered
            if save_to_db:
                users_to_sync = data if (not prop_key or prop_key.lower() == "all") else manager.get_samba_users()
                _sync_samba_users_to_db(users=users_to_sync)
            return StandardResponse(
                data=data,
                message="لیست کاربران سامبا با موفقیت بازیابی شد.",
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
        parameters=[OpenApiParameter("username", str, "path", True), ParamProperty] + QuerySaveToDB,
        responses={200: inline_serializer("SambaUserDetail", {"data": serializers.JSONField()})}
    )
    def retrieve(self, request: Request, username: str) -> Response:
        """
        دریافت اطلاعات یک کاربر سامبا.
        """
        save_to_db = get_request_param(request=request, param_name="save_to_db", return_type=bool, default=False)
        prop_key = get_request_param(request=request, param_name="property", return_type=str, default=None)
        if prop_key:
            prop_key = prop_key.strip()
        request_data = dict(request.query_params)
        try:
            manager = SambaManager()
            user_data = manager.get_samba_users(username=username)
            if user_data is None:
                return StandardErrorResponse(
                    error_code="user_not_found",
                    error_message=f"کاربر '{username}' یافت نشد.",
                    status=404,
                    request_data=request_data,
                    save_to_db=save_to_db
                )
            if save_to_db:
                _sync_samba_users_to_db(users=[user_data])
            if prop_key and prop_key.lower() != "all":
                val = user_data.get(prop_key)
                if val is None:
                    return StandardErrorResponse(
                        error_code="property_not_found",
                        error_message=f"پراپرتی '{prop_key}' یافت نشد.",
                        status=404,
                        request_data=request_data,
                        save_to_db=save_to_db
                    )
                return StandardResponse(
                    data={"username": username, prop_key: val},
                    request_data=request_data,
                    save_to_db=save_to_db
                )
            return StandardResponse(
                data=user_data,
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                error_code="samba_user_fetch_failed",
                error_message="خطا در دریافت اطلاعات کاربر سامبا.",
                request_data=request_data,
                save_to_db=save_to_db
            )

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
            return StandardErrorResponse(
                error_code="missing_username",
                error_message="نام کاربر اجباری است.",
                status=400,
                request_data=dict(request.data),
                save_to_db=False
            )
        save_to_db = get_request_param(request=request, param_name="save_to_db", return_type=bool, default=False)
        request_data = dict(request.data)
        validation_err = self._validate_samba_username_format(username=username, save_to_db=save_to_db, request_data=request_data)
        if validation_err:
            return validation_err
        validation_err = self.validate_samba_user_exists(username=username, save_to_db=save_to_db, request_data=request_data, must_exist=False)
        if validation_err:
            return validation_err
        pw = get_request_param(request=request, param_name="password", return_type=str, default=None)
        if not pw:
            return StandardErrorResponse(
                error_code="missing_password",
                error_message="رمز عبور اجباری است.",
                status=400,
                request_data=request_data,
                save_to_db=save_to_db
            )
        full_name = get_request_param(request=request, param_name="full_name", return_type=str, default=None)
        exp = get_request_param(request=request, param_name="expiration_date", return_type=str, default=None)
        try:
            SambaManager().create_samba_user(username=username, password=pw, full_name=full_name, expiration_date=exp)
            if save_to_db:
                user_data = SambaManager().get_samba_users(username=username)
                if user_data:
                    _sync_samba_users_to_db(users=[user_data])
            return StandardResponse(
                status=201,
                message=f"کاربر '{username}' ایجاد شد.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="samba_user_create_failed",
                error_message="خطا در ایجاد کاربر",
                request_data=request_data,
                save_to_db=save_to_db
            )

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
        save_to_db = get_request_param(request=request, param_name="save_to_db", return_type=bool, default=False)
        action_name = get_request_param(request=request, param_name="action", return_type=str, default=None)
        request_data = dict(request.data)
        validation_err = self.validate_samba_user_exists(username=username, save_to_db=save_to_db, request_data=request_data, must_exist=True)
        if validation_err:
            return validation_err
        try:
            m = SambaManager()
            if action_name == "enable":
                m.enable_samba_user(username=username)
                msg = f"کاربر '{username}' فعال شد."
            elif action_name == "disable":
                m.disable_samba_user(username=username)
                msg = f"کاربر '{username}' غیرفعال شد."
            elif action_name == "change_password":
                new_password = get_request_param(request=request, param_name="new_password", return_type=str, default=None)
                if not new_password:
                    return StandardErrorResponse(
                        error_code="missing_new_password",
                        error_message="رمز جدید اجباری است.",
                        status=400,
                        request_data=request_data,
                        save_to_db=save_to_db
                    )
                m.change_samba_user_password(username=username, new_password=new_password)
                msg = "رمز عبور تغییر کرد."
            else:
                return StandardErrorResponse(
                    error_code="invalid_action",
                    error_message="عملیات نامعتبر.",
                    status=400,
                    request_data=request_data,
                    save_to_db=save_to_db
                )
            if save_to_db:
                user_data = m.get_samba_users(username=username)
                if user_data:
                    _sync_samba_users_to_db(users=[user_data])
            return StandardResponse(
                message=msg,
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="samba_user_op_failed",
                error_message="خطا در عملیات کاربر",
                request_data=request_data,
                save_to_db=save_to_db
            )

    @extend_schema(parameters=[OpenApiParameter("username", str, "path", True)] + QuerySaveToDB)
    def destroy(self, request: Request, username: str) -> Response:
        """
        حذف یک کاربر سامبا (هم از سامبا و هم از سیستم).
        """
        # TODO:// validation: if have user or group or sharepoint return prompt
        save_to_db = get_request_param(request=request, param_name="save_to_db", return_type=bool, default=False)
        request_data = dict(request.query_params)
        validation_err = self.validate_samba_user_exists(username=username, save_to_db=save_to_db, request_data=request_data, must_exist=True)
        if validation_err:
            return validation_err
        try:
            m = SambaManager()
            m.delete_samba_user_from_samba_db(username=username)
            m.delete_samba_user_from_system(username=username)
            if save_to_db:
                SambaUser.objects.filter(username=username).delete()
            return StandardResponse(
                message=f"کاربر '{username}' حذف شد.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="samba_del_sys_failed",
                error_message="خطا در حذف از سیستم",
                request_data=request_data,
                save_to_db=save_to_db
            )


# ========== SambaGroupViewSet ==========
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
        save_to_db = get_request_param(request=request, param_name="save_to_db", return_type=bool, default=False)
        prop_key = get_request_param(request=request, param_name="property", return_type=str, default=None)
        if prop_key:
            prop_key = prop_key.strip()
        contain_sys = get_request_param(request=request, param_name="contain_system_groups", return_type=bool, default=True)
        request_data = dict(request.query_params)
        try:
            m = SambaManager()
            data = m.get_samba_groups(contain_system_groups=contain_sys)
            if prop_key and prop_key.lower() != "all":
                filtered = [{"groupname": g["name"], prop_key: g.get(prop_key)} for g in data]
                data = filtered
            if save_to_db:
                full_data = m.get_samba_groups(contain_system_groups=contain_sys)
                _sync_samba_groups_to_db(groups=full_data)
            return StandardResponse(
                data=data,
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="samba_group_fetch_failed",
                error_message="خطا در دریافت گروه‌ها",
                request_data=request_data,
                save_to_db=save_to_db
            )

    @extend_schema(
        parameters=[OpenApiParameter("groupname", str, "path", True), ParamProperty, ParamContainSystemGroups] + QuerySaveToDB
    )
    def retrieve(self, request: Request, groupname: str) -> Response:
        """
        دریافت اطلاعات یک گروه سامبا.
        """
        save_to_db = get_request_param(request=request, param_name="save_to_db", return_type=bool, default=False)
        prop_key = get_request_param(request=request, param_name="property", return_type=str, default=None)
        if prop_key:
            prop_key = prop_key.strip()
        contain_sys = get_request_param(request=request, param_name="contain_system_groups", return_type=bool, default=True)
        request_data = dict(request.query_params)
        try:
            m = SambaManager()
            g = m.get_samba_groups(groupname=groupname, contain_system_groups=contain_sys)
            if g is None:
                return StandardErrorResponse(
                    error_code="group_not_found",
                    error_message=f"گروه '{groupname}' یافت نشد.",
                    status=404,
                    request_data=request_data,
                    save_to_db=save_to_db
                )
            if save_to_db:
                _sync_samba_groups_to_db(groups=[g])
            if prop_key and prop_key.lower() != "all":
                val = g.get(prop_key)
                if val is None:
                    return StandardErrorResponse(
                        error_code="property_not_found",
                        error_message=f"پراپرتی '{prop_key}' یافت نشد.",
                        status=404,
                        request_data=request_data,
                        save_to_db=save_to_db
                    )
                return StandardResponse(
                    data={"groupname": groupname, prop_key: val},
                    request_data=request_data,
                    save_to_db=save_to_db
                )
            return StandardResponse(
                data=g,
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="samba_group_fetch_failed",
                error_message="خطا در دریافت گروه",
                request_data=request_data,
                save_to_db=save_to_db
            )

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
            return StandardErrorResponse(
                error_code="missing_groupname",
                error_message="نام گروه اجباری است.",
                status=400,
                request_data=dict(request.data),
                save_to_db=False
            )
        save_to_db = get_request_param(request=request, param_name="save_to_db", return_type=bool, default=False)
        request_data = dict(request.data)
        validation_err = self._validate_samba_groupname_format(groupname=groupname, save_to_db=save_to_db, request_data=request_data)
        if validation_err:
            return validation_err
        validation_err = self._validate_samba_group_exists(groupname=groupname, save_to_db=save_to_db, request_data=request_data, must_exist=False)
        if validation_err:
            return validation_err
        try:
            SambaManager().create_samba_group(groupname=groupname)
            if save_to_db:
                g = SambaManager().get_samba_groups(groupname=groupname)
                if g:
                    _sync_samba_groups_to_db(groups=[g])
            return StandardResponse(
                status=201,
                message=f"گروه '{groupname}' ایجاد شد.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="samba_group_create_failed",
                error_message="خطا در ایجاد گروه",
                request_data=request_data,
                save_to_db=save_to_db
            )

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
        save_to_db = get_request_param(request=request, param_name="save_to_db", return_type=bool, default=False)
        action_name = get_request_param(request=request, param_name="action", return_type=str, default=None)
        username = get_request_param(request=request, param_name="username", return_type=str, default=None)
        request_data = dict(request.data)
        validation_err = self._validate_samba_group_exists(groupname=groupname, save_to_db=save_to_db, request_data=request_data, must_exist=True)
        if validation_err:
            return validation_err
        if not username:
            return StandardErrorResponse(
                error_code="missing_username",
                error_message="نام کاربر اجباری است.",
                status=400,
                request_data=request_data,
                save_to_db=save_to_db
            )
        validation_err = SambaUserValidationMixin().validate_samba_user_exists(username=username, save_to_db=save_to_db, request_data=request_data, must_exist=True)
        if validation_err:
            return validation_err
        try:
            m = SambaManager()
            if action_name == "add_user":
                m.add_user_to_group(username=username, groupname=groupname)
                msg = f"کاربر '{username}' به گروه اضافه شد."
            elif action_name == "remove_user":
                m.remove_user_from_group(username=username, groupname=groupname)
                msg = f"کاربر '{username}' از گروه حذف شد."
            else:
                return StandardErrorResponse(
                    error_code="invalid_action",
                    error_message="عملیات نامعتبر.",
                    status=400,
                    request_data=request_data,
                    save_to_db=save_to_db
                )
            if save_to_db:
                g = m.get_samba_groups(groupname=groupname)
                if g:
                    _sync_samba_groups_to_db(groups=[g])
            return StandardResponse(
                message=msg,
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="samba_group_op_failed",
                error_message="خطا در عملیات گروه",
                request_data=request_data,
                save_to_db=save_to_db
            )

    @extend_schema(parameters=[OpenApiParameter("groupname", str, "path", True)] + QuerySaveToDB)
    def destroy(self, request: Request, groupname: str) -> Response:
        """
        حذف یک گروه سامبا.
        """
        # TODO:// validation: if have user or group or sharepoint return prompt
        save_to_db = get_request_param(request=request, param_name="save_to_db", return_type=bool, default=False)
        request_data = dict(request.query_params)
        validation_err = self._validate_samba_group_exists(groupname=groupname, save_to_db=save_to_db, request_data=request_data, must_exist=True)
        if validation_err:
            return validation_err
        try:
            SambaManager().delete_samba_group(groupname=groupname)
            if save_to_db:
                SambaGroup.objects.filter(name=groupname).delete()
            return StandardResponse(
                message=f"گروه '{groupname}' حذف شد.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="samba_group_del_failed",
                error_message="خطا در حذف گروه",
                request_data=request_data,
                save_to_db=save_to_db
            )


# ========== SambaSharepointViewSet ==========
class SambaSharepointViewSet(viewsets.ViewSet, SambaSharepointValidationMixin):
    """
    مدیریت مسیرهای اشتراکی سامبا از طریق API.
    """
    lookup_field = "sharepoint_name"

    @extend_schema(parameters=[ParamProperty, ParamOnlyActive] + QuerySaveToDB)
    def list(self, request: Request) -> Response:
        """
        دریافت لیست تمام مسیرهای اشتراکی سامبا.
        """
        save_to_db = get_request_param(request=request, param_name="save_to_db", return_type=bool, default=False)
        prop_key = get_request_param(request=request, param_name="property", return_type=str, default=None)
        if prop_key:
            prop_key = prop_key.strip()
        only_active = get_request_param(request=request, param_name="only_active", return_type=bool, default=False)
        request_data = dict(request.query_params)
        try:
            m = SambaManager()
            data = m.get_samba_sharepoints(only_active_shares=only_active)
            if prop_key and prop_key.lower() != "all":
                filtered = [{"sharepoint_name": s["name"], prop_key: s.get(prop_key)} for s in data]
                data = filtered
            if save_to_db:
                full_data = m.get_samba_sharepoints(only_active_shares=only_active)
                _sync_samba_sharepoints_to_db(shares=full_data)
            return StandardResponse(
                data=data,
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="samba_share_fetch_failed",
                error_message="خطا در دریافت مسیرها",
                request_data=request_data,
                save_to_db=save_to_db
            )

    @extend_schema(parameters=[OpenApiParameter("sharepoint_name", str, "path", True), ParamProperty, ParamOnlyActive] + QuerySaveToDB)
    def retrieve(self, request: Request, sharepoint_name: str) -> Response:
        """
        دریافت اطلاعات یک مسیر اشتراکی سامبا.
        """
        save_to_db = get_request_param(request=request, param_name="save_to_db", return_type=bool, default=False)
        prop_key = get_request_param(request=request, param_name="property", return_type=str, default=None)
        if prop_key:
            prop_key = prop_key.strip()
        only_active = get_request_param(request=request, param_name="only_active", return_type=bool, default=False)
        request_data = dict(request.query_params)
        try:
            m = SambaManager()
            s = m.get_samba_sharepoints(sharepoint_name=sharepoint_name, only_active_shares=only_active)
            if s is None:
                return StandardErrorResponse(
                    error_code="share_not_found",
                    error_message=f"مسیر '{sharepoint_name}' یافت نشد.",
                    status=404,
                    request_data=request_data,
                    save_to_db=save_to_db
                )
            if save_to_db:
                _sync_samba_sharepoints_to_db(shares=[s])
            if prop_key and prop_key.lower() != "all":
                val = s.get(prop_key)
                if val is None:
                    return StandardErrorResponse(
                        error_code="property_not_found",
                        error_message=f"پراپرتی '{prop_key}' یافت نشد.",
                        status=404,
                        request_data=request_data, save_to_db=save_to_db)
                return StandardResponse(
                    data={"sharepoint_name": sharepoint_name, prop_key: val},
                    request_data=request_data,
                    save_to_db=save_to_db
                )
            return StandardResponse(
                data=s,
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="samba_share_fetch_failed",
                error_message="خطا در دریافت مسیر",
                request_data=request_data,
                save_to_db=save_to_db
            )

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
            return StandardErrorResponse(
                error_code="missing_sharepoint_name",
                error_message="نام مسیر اشتراکی اجباری است.",
                status=400,
                request_data=dict(request.data),
                save_to_db=False
            )
        save_to_db = get_request_param(request=request, param_name="save_to_db", return_type=bool, default=False)
        request_data = dict(request.data)
        validation_err = self._validate_samba_sharepoint_name_format(share_name=sharepoint_name, save_to_db=save_to_db, request_data=request_data)
        if validation_err:
            return validation_err
        validation_err = self._validate_samba_sharepoint_exists(share_name=sharepoint_name, save_to_db=save_to_db, request_data=request_data, must_exist=False)
        if validation_err:
            return validation_err
        path = get_request_param(request=request, param_name="path", return_type=str, default=None)
        if not path:
            return StandardErrorResponse(
                error_code="missing_path",
                error_message="مسیر اجباری است.",
                status=400,
                request_data=request_data,
                save_to_db=save_to_db
            )
        valid_users = get_request_param(request=request, param_name="valid_users", return_type=list, default=None)
        valid_groups = get_request_param(request=request, param_name="valid_groups", return_type=list, default=None)
        read_only = get_request_param(request=request, param_name="read_only", return_type=bool, default=False)
        guest_ok = get_request_param(request=request, param_name="guest_ok", return_type=bool, default=False)
        browseable = get_request_param(request=request, param_name="browseable", return_type=bool, default=True)
        max_connections = get_request_param(request=request, param_name="max_connections", return_type=int, default=None)
        create_mask = get_request_param(request=request, param_name="create_mask", return_type=str, default="0644")
        directory_mask = get_request_param(request=request, param_name="directory_mask", return_type=str, default="0755")
        inherit_permissions = get_request_param(request=request, param_name="inherit_permissions", return_type=bool, default=False)
        expiration_time = get_request_param(request=request, param_name="expiration_time", return_type=str, default=None)
        available = get_request_param(request=request, param_name="available", return_type=bool, default=True)

        try:
            SambaManager().create_samba_sharepoint(
                name=sharepoint_name,
                path=path,
                valid_users=valid_users,
                valid_groups=valid_groups,
                read_only=read_only,
                guest_ok=guest_ok,
                browseable=browseable,
                max_connections=max_connections,
                create_mask=create_mask,
                directory_mask=directory_mask,
                inherit_permissions=inherit_permissions,
                expiration_time=expiration_time,
                available=available,
            )
            if save_to_db:
                s = SambaManager().get_samba_sharepoints(sharepoint_name=sharepoint_name)
                if s:
                    _sync_samba_sharepoints_to_db(shares=[s])
            return StandardResponse(
                status=201,
                message=f"مسیر '{sharepoint_name}' ایجاد شد.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="samba_share_create_failed",
                error_message="خطا در ایجاد مسیر",
                request_data=request_data,
                save_to_db=save_to_db
            )

    @extend_schema(
        methods=["PUT"],
        request={"type": "object", "additionalProperties": {"type": "string"}, "properties": BodyParameterSaveToDB["properties"]}
    )
    @action(detail=True, methods=["put"], url_path="update")
    def update_sharepoint(self, request: Request, sharepoint_name: str) -> Response:
        """
        به‌روزرسانی یک مسیر اشتراکی سامبا.
        """
        save_to_db = get_request_param(request=request, param_name="save_to_db", return_type=bool, default=False)
        request_data = dict(request.data)
        validation_err = self._validate_samba_sharepoint_exists(share_name=sharepoint_name, save_to_db=save_to_db, request_data=request_data, must_exist=True)
        if validation_err:
            return validation_err
        try:
            SambaManager().update_samba_sharepoint(sharepoint_name=sharepoint_name, **request_data)
            if save_to_db:
                s = SambaManager().get_samba_sharepoints(sharepoint_name=sharepoint_name)
                if s:
                    _sync_samba_sharepoints_to_db(shares=[s])
            return StandardResponse(
                message=f"مسیر '{sharepoint_name}' به‌روزرسانی شد.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="samba_share_update_failed",
                error_message="خطا در به‌روزرسانی",
                request_data=request_data,
                save_to_db=save_to_db
            )

    @extend_schema(parameters=[OpenApiParameter("sharepoint_name", str, "path", True)] + QuerySaveToDB)
    def destroy(self, request: Request, sharepoint_name: str) -> Response:
        """
        حذف یک مسیر اشتراکی سامبا.
        """
        # TODO:// validation: if have user or group or sharepoint return prompt

        save_to_db = get_request_param(request=request, param_name="save_to_db", return_type=bool, default=False)
        request_data = dict(request.query_params)
        validation_err = self._validate_samba_sharepoint_exists(share_name=sharepoint_name, save_to_db=save_to_db, request_data=request_data, must_exist=True)
        if validation_err:
            return validation_err
        try:
            SambaManager().delete_samba_sharepoint(name=sharepoint_name)
            if save_to_db:
                SambaSharepoint.objects.filter(name=sharepoint_name).delete()
            return StandardResponse(
                message=f"مسیر '{sharepoint_name}' حذف شد.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="samba_share_del_failed",
                error_message="خطا در حذف مسیر",
                request_data=request_data,
                save_to_db=save_to_db
            )
