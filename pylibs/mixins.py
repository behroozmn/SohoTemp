# soho_core_api/views_collection/mixins.py
from __future__ import annotations

import re
from pylibs import StandardErrorResponse,logger
from pylibs.disk import DiskManager
from pylibs.zpool import ZpoolManager


class DiskValidationMixin:
    """Mixin برای اعتبارسنجی دیسک. تمام منطق مرتبط با اعتبارسنجی در اینجا متمرکز شده است."""

    def _validate_disk_name(self, disk_name: str) -> tuple[bool, str | None]:
        if not disk_name or not isinstance(disk_name, str):
            return False, "نام دیسک معتبر نیست."
        return True, None

    def _get_disk_manager_and_validate(self, disk_name: str) -> tuple[DiskManager | None, str | None]:
        is_valid, error_msg = self._validate_disk_name(disk_name)
        if not is_valid:
            return None, error_msg

        try:
            obj_disk = DiskManager()
            if disk_name not in obj_disk.disks:
                return None, f"دیسک '{disk_name}' یافت نشد."
            return obj_disk, None
        except Exception as e:
            logger.error(f"Error creating DiskManager: {str(e)}")
            return None, "خطا در ایجاد منیجر دیسک."

    def validate_disk_and_get_manager(
            self,
            disk_name: str,
            save_to_db: bool,
            request_data: dict,
    ) -> DiskManager | StandardErrorResponse:
        obj_disk, error_msg = self._get_disk_manager_and_validate(disk_name)
        if obj_disk is None:
            status_code = 404 if "یافت نشد" in (error_msg or "") else 400
            return StandardErrorResponse(
                error_code="disk_not_found" if "یافت نشد" in (error_msg or "") else "invalid_disk_name",
                error_message=error_msg or "خطا در اعتبارسنجی دیسک.",
                request_data=request_data,
                status=status_code,
                save_to_db=save_to_db
            )
        return obj_disk

class OSDiskProtectionMixin:
    """Mixin برای جلوگیری از عملیات روی دیسک سیستم‌عامل."""

    def check_os_disk_protection(self, obj_disk: DiskManager, disk_name: str, save_to_db: bool, request_data: dict):
        if obj_disk.has_os_on_disk(disk_name):
            return StandardErrorResponse(
                error_code="os_disk_protected",
                error_message=f"پاک‌کردن دیسک سیستم‌عامل ({disk_name}) مجاز نیست.",
                request_data=request_data,
                status=403,
                save_to_db=save_to_db
            )
        return None

class ZpoolNameValidationMixin:
    """اعتبارسنجی نام pool ZFS."""
    POOL_NAME_PATTERN = r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$'

    def _validate_zpool_name(self, pool_name: str) -> tuple[bool, str | None]:
        if not isinstance(pool_name, str) or not pool_name.strip():
            return False, "نام pool نمی‌تواند خالی باشد."
        if not re.match(self.POOL_NAME_PATTERN, pool_name):
            return False, "نام pool فقط می‌تواند شامل حروف، اعداد، نقطه، زیرخط و خط‌تیره باشد و با حرف/عدد شروع شود."
        if len(pool_name) > 255:
            return False, "نام pool نمی‌تواند بیشتر از 255 کاراکتر باشد."
        return True, None

class ZpoolExistsMixin(ZpoolNameValidationMixin):
    """بررسی وجود pool و اعتبارسنجی آن."""
    def _get_zpool_manager_and_validate(self, pool_name: str, must_exist: bool = True) -> tuple[ZpoolManager | None, str | None]:
        is_valid, error = self._validate_zpool_name(pool_name)
        if not is_valid:
            return None, error
        try:
            manager = ZpoolManager()
            exists = manager.pool_exists(pool_name)
            if must_exist and not exists:
                return None, f"Pool '{pool_name}' وجود ندارد."
            if not must_exist and exists:
                return None, f"Pool '{pool_name}' از قبل وجود دارد."
            return manager, None
        except Exception as e:
            logger.error(f"Error initializing ZpoolManager: {e}")
            return None, "خطا در ایجاد منیجر Zpool."

    def validate_zpool_for_operation(
        self, pool_name: str, save_to_db: bool, request_data: dict, must_exist: bool = True
    ):
        manager, error = self._get_zpool_manager_and_validate(pool_name, must_exist)
        if manager is None:
            status = 404 if "وجود ندارد" in (error or "") else 400
            return StandardErrorResponse(
                error_code="pool_not_found" if must_exist else "pool_already_exists",
                error_message=error or "خطا در اعتبارسنجی pool.",
                request_data=request_data,
                status=status,
                save_to_db=save_to_db
            )
        return manager