# soho_core_api/views/view_filesystem.py

from __future__ import annotations

from typing import Any, Dict, Optional, List, Union
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response

from pylibs import get_request_param, build_standard_error_response, logger
from pylibs.fileSystem import FilesystemManager
from pylibs.zpool import ZpoolManager
from pylibs.mixins import ZpoolValidationMixin, FilesystemValidationMixin
from pylibs import StandardResponse, StandardErrorResponse


class FilesystemListView(APIView, ZpoolValidationMixin, FilesystemValidationMixin):
    """View برای عملیات دسته‌جمعی روی فایل‌سیستم‌ها."""

    def get(self, request: Request) -> Response:
        """دریافت لیست نام تمام فایل‌سیستم‌ها یا جزئیات کامل آن‌ها."""
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        detail = get_request_param(request, "detail", bool, False)
        contain_poolname = get_request_param(request, "contain_poolname", bool, False)

        try:
            fs_manager = FilesystemManager()
            if detail:
                data = fs_manager.get_filesystems_all_detail(contain_poolname=contain_poolname)
            else:
                data = fs_manager.list_filesystems_names(contain_poolname=contain_poolname)

            return StandardResponse(
                data=data,
                save_to_db=save_to_db,
                message="لیست فایل‌سیستم‌ها با موفقیت بازیابی شد.",
                request_data=dict(request.data) if hasattr(request, 'data') else {},
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                request_data=dict(request.data) if hasattr(request, 'data') else {},
                save_to_db=save_to_db,
                error_code="filesystem_list_failed",
                error_message="خطا در دریافت لیست فایل‌سیستم‌ها."
            )


class FilesystemDetailView(APIView, ZpoolValidationMixin, FilesystemValidationMixin):
    """View برای عملیات روی یک فایل‌سیستم خاص."""

    def get(self, request: Request, pool_name: str, fs_name: str) -> Response:
        """دریافت جزئیات یک فایل‌سیستم."""
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        prop_key = get_request_param(request, "property", str, None)
        request_data = dict(request.query_params)

        try:
            pool_manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
            if isinstance(pool_manager, StandardErrorResponse):
                return pool_manager

            full_name = f"{pool_name}/{fs_name}"
            fs_manager = FilesystemManager()

            if prop_key:
                value = fs_manager.get_filesystem_property(full_name, prop_key)
                if value is None:
                    return StandardErrorResponse(
                        request_data=request_data,
                        save_to_db=save_to_db,
                        status=404,
                        error_code="property_not_found",
                        error_message=f"پراپرتی '{prop_key}' در فایل‌سیستم '{full_name}' یافت نشد."
                    )
                return StandardResponse(
                    request_data=request_data,
                    save_to_db=save_to_db,
                    data={prop_key: value},
                    message=f"پراپرتی '{prop_key}' با موفقیت بازیابی شد."
                )
            else:
                detail = fs_manager.get_filesystem_detail(full_name)
                if detail is None:
                    return StandardErrorResponse(
                        request_data=request_data,
                        save_to_db=save_to_db,
                        status=404,
                        error_code="filesystem_not_found",
                        error_message=f"فایل‌سیستم '{full_name}' یافت نشد."
                    )
                return StandardResponse(
                    request_data=request_data,
                    save_to_db=save_to_db,
                    data=detail,
                    message="جزئیات فایل‌سیستم با موفقیت بازیابی شد."
                )

        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                request_data=request_data,
                save_to_db=save_to_db,
                error_code="filesystem_detail_failed",
                error_message="خطا در دریافت جزئیات فایل‌سیستم."
            )

    def post(self, request: Request, pool_name: str, fs_name: str) -> Response:
        """ساخت فایل‌سیستم جدید."""
        save_to_db: bool = get_request_param(request, "save_to_db", bool, False)
        quota = get_request_param(request, "quota", str, None)
        reservation = get_request_param(request, "reservation", str, None)
        mountpoint: str = get_request_param(request, "mountpoint", str, None)

        request_data = dict(request.data)

        pool_manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
        if isinstance(pool_manager, StandardErrorResponse):
            return pool_manager

        name_check = self._validate_filesystem_name_availability(
            pool_name, fs_name, save_to_db, request_data, must_not_exist=True
        )
        if name_check:
            return name_check

        # ✅ اینجا pool_name را هم پاس می‌دهیم
        quota_check = self._validate_quota_against_pool_capacity(
            pool_manager, pool_name, quota, save_to_db, request_data
        )
        if quota_check:
            return quota_check

        try:
            fs_manager = FilesystemManager()
            fs_manager.create_filesystem(pool_name, fs_name, quota=quota, reservation=reservation, mountpoint=mountpoint)
            return StandardResponse(
                request_data=request_data,
                save_to_db=save_to_db,
                message=f"فایل‌سیستم '{pool_name}/{fs_name}' با موفقیت ایجاد شد."
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                request_data=request_data,
                save_to_db=save_to_db,
                error_code="filesystem_creation_failed",
                error_message="خطا در ساخت فایل‌سیستم."
            )

    def delete(self, request: Request, pool_name: str, fs_name: str) -> Response:
        """حذف فایل‌سیستم."""
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.data)

        pool_manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
        if isinstance(pool_manager, StandardErrorResponse):
            return pool_manager

        full_name = f"{pool_name}/{fs_name}"

        name_check = self._validate_filesystem_name_availability(
            pool_name, fs_name, save_to_db, request_data, must_not_exist=False
        )
        if name_check:
            return name_check

        fs_manager = FilesystemManager()
        detail = fs_manager.get_filesystem_detail(full_name)
        mountpoint = detail.get("mountpoint") if detail else None

        if mountpoint and mountpoint != "none":
            samba_check = self._is_filesystem_used_in_samba(mountpoint, save_to_db, request_data)
            if samba_check:
                return samba_check

        try:
            fs_manager.destroy_filesystem(full_name)
            return StandardResponse(
                request_data=request_data,
                save_to_db=save_to_db,
                message=f"فایل‌سیستم '{full_name}' با موفقیت حذف شد."
            )
        except Exception as exc:
            return build_standard_error_response(
                exc=exc,
                request_data=request_data,
                save_to_db=save_to_db,
                error_code="filesystem_deletion_failed",
                error_message="خطا در حذف فایل‌سیستم."
            )