# soho_core_api/views_collection/mixins.py
from __future__ import annotations

import re
from typing import Tuple, Union, Optional, Dict, Any
from pylibs import StandardErrorResponse, logger
from pylibs.disk import DiskManager
from pylibs.zpool import ZpoolManager


class DiskValidationMixin:
    """
    Mixin برای اعتبارسنجی دیسک.

    این کلاس تمام منطق مرتبط با تأیید صحت نام دیسک و وجود آن در سیستم را مدیریت می‌کند.
    به‌عنوان یک کامپوننت قابل استفاده در APIViewها طراحی شده است.
    """

    def _validate_disk_name(self, disk_name: str) -> Tuple[bool, Optional[str]]:
        """
        اعتبارسنجی ساختاری نام دیسک.

        Args:
            disk_name (str): نام دیسک برای بررسی (مثال: 'sda', 'nvme0n1').

        Returns:
            Tuple[bool, Optional[str]]:
                - اگر معتبر باشد: (True, None)
                - اگر نامعتبر باشد: (False, پیام خطا)
        """
        if not disk_name or not isinstance(disk_name, str):
            return False, "نام دیسک معتبر نیست."
        return True, None

    def _get_disk_manager_and_validate(self, disk_name: str) -> Tuple[Optional[DiskManager], Optional[str]]:
        """
        دریافت نمونه DiskManager و اعتبارسنجی وجود دیسک در سیستم.

        Args:
            disk_name (str): نام دیسک برای بررسی.

        Returns:
            Tuple[Optional[DiskManager], Optional[str]]:
                - در موفقیت: (نمونه DiskManager, None)
                - در خطا: (None, پیام خطا)
        """
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
            request_data: Dict[str, Any],
    ) -> Union[DiskManager, StandardErrorResponse]:
        """
        اعتبارسنجی کامل دیسک و بازگرداندن نمونه مدیر یا خطای استاندارد.

        Args:
            disk_name (str): نام دیسک.
            save_to_db (bool): آیا پاسخ باید در دیتابیس ذخیره شود؟
            request_data (Dict[str, Any]): داده درخواست اصلی برای لاگ یا ذخیره.

        Returns:
            Union[DiskManager, StandardErrorResponse]:
                - در صورت موفقیت: نمونه DiskManager
                - در صورت خطا: نمونه StandardErrorResponse
        """
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
    """
    Mixin برای جلوگیری از انجام عملیات خطرناک روی دیسک سیستم‌عامل.

    این کلاس از اشتباهات رایج کاربران جلوگیری می‌کند که بخواهند دیسک بوت را پاک یا تغییر دهند.
    """

    def check_os_disk_protection(
            self,
            obj_disk: DiskManager,
            disk_name: str,
            save_to_db: bool,
            request_data: Dict[str, Any],
    ) -> Optional[StandardErrorResponse]:
        """
        بررسی اینکه آیا دیسک مورد نظر، دیسک سیستم‌عامل است یا خیر.

        Args:
            obj_disk (DiskManager): نمونه فعلی مدیر دیسک.
            disk_name (str): نام دیسک برای بررسی.
            save_to_db (bool): آیا پاسخ باید در دیتابیس ذخیره شود؟
            request_data (Dict[str, Any]): داده درخواست اصلی.

        Returns:
            Optional[StandardErrorResponse]:
                - اگر دیسک سیستم‌عامل باشد: خطای ممنوعیت (403)
                - اگر نباشد: None
        """
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
    """
    Mixin برای اعتبارسنجی نام ZFS Pool.

    نام‌های معتبر ZFS باید:
        - با حرف یا عدد شروع شوند.
        - فقط شامل حروف، اعداد، نقطه، زیرخط و خط‌تیره باشند.
        - حداکثر 255 کاراکتر طول داشته باشند.
    """

    POOL_NAME_PATTERN: str = r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$'
    """الگوی منظم برای تأیید نام معتبر ZFS Pool."""

    def _validate_zpool_name(self, pool_name: str) -> Tuple[bool, Optional[str]]:
        """
        اعتبارسنجی نام ZFS Pool بر اساس قوانین رسمی ZFS.

        Args:
            pool_name (str): نام pool پیشنهادی.

        Returns:
            Tuple[bool, Optional[str]]:
                - در صورت معتبر بودن: (True, None)
                - در صورت نامعتبر بودن: (False, پیام خطا)
        """
        if not isinstance(pool_name, str) or not pool_name.strip():
            return False, "نام pool نمی‌تواند خالی باشد."
        if not re.match(self.POOL_NAME_PATTERN, pool_name):
            return False, "نام pool فقط می‌تواند شامل حروف، اعداد، نقطه، زیرخط و خط‌تیره باشد و با حرف/عدد شروع شود."
        if len(pool_name) > 255:
            return False, "نام pool نمی‌تواند بیشتر از 255 کاراکتر باشد."
        return True, None


class ZpoolExistsMixin(ZpoolNameValidationMixin):
    """
    Mixin برای اعتبارسنجی وجود یا عدم وجود یک ZFS Pool.

    این کلاس از ZpoolNameValidationMixin ارث‌بری می‌کند و قابلیت بررسی وجود pool را اضافه می‌کند.
    برای عملیاتی مانند ایجاد (نیاز به عدم وجود) یا حذف/جایگزینی (نیاز به وجود) کاربرد دارد.
    """

    def _get_zpool_manager_and_validate(self, pool_name: str, must_exist: bool = True) -> Tuple[Optional[ZpoolManager], Optional[str]]:
        """
        دریافت نمونه ZpoolManager و اعتبارسنجی وجود/عدم وجود pool.

        Args:
            pool_name (str): نام pool مورد نظر.
            must_exist (bool): آیا pool باید وجود داشته باشد؟
                - True: برای عملیاتی مانند destroy یا replace.
                - False: برای عملیاتی مانند create.

        Returns:
            Tuple[Optional[ZpoolManager], Optional[str]]:
                - در موفقیت: (نمونه ZpoolManager, None)
                - در خطا: (None, پیام خطا)
        """
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
            self,
            pool_name: str,
            save_to_db: bool,
            request_data: Dict[str, Any],
            must_exist: bool = True
    ) -> Union[ZpoolManager, StandardErrorResponse]:
        """
        اعتبارسنجی کامل pool برای یک عملیات و بازگرداندن مدیر یا خطا.

        Args:
            pool_name (str): نام pool.
            save_to_db (bool): آیا پاسخ باید در دیتابیس ذخیره شود؟
            request_data (Dict[str, Any]): داده درخواست کاربر.
            must_exist (bool): آیا pool باید از قبل وجود داشته باشد؟

        Returns:
            Union[ZpoolManager, StandardErrorResponse]:
                - در صورت موفقیت: نمونه ZpoolManager
                - در صورت خطا: نمونه StandardErrorResponse
        """
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
