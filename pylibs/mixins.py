# soho_core_api/views_collection/mixins.py
from __future__ import annotations

import re
import os
from typing import Tuple, Union, Optional, Dict, Any
from pylibs import StandardErrorResponse, logger
from pylibs.disk import DiskManager
from pylibs.zpool import ZpoolManager
from typing import Tuple, Optional, Union, Dict, Any, List


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

    def _resolve_device_path(self, device_path: str) -> Optional[str]:
        """
        تبدیل مسیر لینک (مثل /dev/disk/by-id/wwn-...) به مسیر واقعی بلاک دیوایس (مثل /dev/sdb).
        """
        if not device_path.startswith("/dev/"):
            return None
        try:
            return os.path.realpath(device_path)
        except (OSError, ValueError):
            return None

    def _extract_disk_name_from_real_path(self, real_path: str) -> Optional[str]:
        """
        استخراج نام دیسک (مثل 'sdb', 'nvme0n1') از مسیر واقعی (مثل '/dev/sdb', '/dev/nvme0n1').
        """
        if not real_path.startswith("/dev/"):
            return None
        name = os.path.basename(real_path)
        # بررسی اینکه آیا پارتیشن است یا نه (اگر پارتیشن بود، دیسک اصلی را برمی‌گرداند)
        if name.startswith(("sd", "hd", "vd")) and any(c.isdigit() for c in name):
            return re.sub(r'\d+$', '', name)
        if name.startswith(("nvme", "mmcblk")) and "p" in name:
            return re.sub(r'p\d+$', '', name)
        # اگر خودش دیسک اصلی بود
        if re.match(r'^(sd[a-z]+|nvme\d+n\d+|vd[a-z]+|hd[a-z]+|mmcblk\d+)$', name):
            return name
        return None

    def _normalize_disk_input(self, disk_input: str) -> Tuple[Optional[str], Optional[str]]:
        """
        تبدیل ورودی (نام کوتاه یا مسیر WWN) به نام دیسک استاندارد.

        Returns:
            Tuple[Optional[str], Optional[str]]:
                - (disk_name, None) اگر موفق باشد
                - (None, error_message) اگر شکست بخورد
        """
        if disk_input.startswith("/dev/disk/by-id/"):
            # ورودی یک مسیر WWN/NVMe است
            real_path = self._resolve_device_path(disk_input)
            if not real_path or not real_path.startswith("/dev/"):
                return None, f"دستگاه معتبری برای مسیر '{disk_input}' یافت نشد."

            disk_name = self._extract_disk_name_from_real_path(real_path)
            if not disk_name:
                return None, f"نام دیسک قابل استخراج نیست از مسیر '{real_path}'."

            return disk_name, None
        else:
            # ورودی یک نام کوتاه است (مثل 'sda')
            return disk_input, None

    def _get_disk_manager_and_validate(self, disk_input: str, contain_os_disk: bool = False,) -> Tuple[Optional[DiskManager], Optional[str]]:
        """
        دریافت نمونه DiskManager و اعتبارسنجی وجود دیسک در سیستم.

        Args:
            disk_input (str): نام کوتاه یا مسیر کامل دیسک.
            contain_os_disk: bool = True,

        Returns:
            Tuple[Optional[DiskManager], Optional[str]]:
                - در موفقیت: (نمونه DiskManager, None)
                - در خطا: (None, پیام خطا)
        """
        disk_name, error = self._normalize_disk_input(disk_input)
        if error:
            return None, error

        is_valid, error_msg = self._validate_disk_name(disk_name)
        if not is_valid:
            return None, error_msg

        try:
            obj_disk = DiskManager(contain_os_disk=contain_os_disk)
            if disk_name not in obj_disk.disks:
                return None, f"دیسک '{disk_name}' یافت نشد."
            return obj_disk, None
        except Exception as e:
            logger.error(f"Error creating DiskManager: {str(e)}")
            return None, "خطا در ایجاد منیجر دیسک."

    def validate_disk_and_get_manager(self, disk_input: str, save_to_db: bool, request_data: Dict[str, Any],contain_os_disk: bool = False,) -> Union[DiskManager, StandardErrorResponse]:
        """
        اعتبارسنجی کامل دیسک (با پشتیبانی از WWN/NVMe) و بازگرداندن نمونه مدیر یا خطای استاندارد.

        Args:
            disk_input (str): نام کوتاه یا مسیر کامل WWN دیسک.
            save_to_db (bool): آیا پاسخ باید در دیتابیس ذخیره شود؟
            request_data (Dict[str, Any]): داده درخواست اصلی برای لاگ یا ذخیره.
            contain_os_disk: bool=True

        Returns:
            Union[DiskManager, StandardErrorResponse]:
                - در صورت موفقیت: نمونه DiskManager
                - در صورت خطا: نمونه StandardErrorResponse
        """
        obj_disk, error_msg = self._get_disk_manager_and_validate(disk_input,contain_os_disk=contain_os_disk)
        if obj_disk is None:
            status_code = 404 if "یافت نشد" in (error_msg or "") else 400
            return StandardErrorResponse(
                error_code="disk_not_found" if "یافت نشد" in (error_msg or "") else "invalid_disk_input",
                error_message=error_msg or "خطا در اعتبارسنجی دیسک.",
                request_data=request_data,
                status=status_code,
                save_to_db=save_to_db
            )
        return obj_disk

    def check_os_disk_protection(self, obj_disk: DiskManager, disk_name: str, save_to_db: bool, request_data: Dict[str, Any], ) -> Optional[StandardErrorResponse]:
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


class ZpoolValidationMixin:
    """
    میکسین جامع برای اعتبارسنجی ZFS Pool و دیسک‌های مرتبط با آن.

    این کلاس تمام منطق مورد نیاز برای ایمن‌سازی عملیات Zpool را فراهم می‌کند:
        - اعتبارسنجی نام pool (طول، کاراکتر، ساختار)
        - بررسی وجود یا عدم وجود pool
        - اعتبارسنجی مسیرهای دیسک (فقط /dev/ و زیرشاخه‌های معتبر)
        - پشتیبانی کامل از مسیرهای WWN و NVMe در /dev/disk/by-id/
        - استخراج نام کوتاه دیسک برای استفاده در DiskManager
        - اعتبارسنجی vdev_type معتبر
    """

    POOL_NAME_PATTERN: str = r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$'
    """الگوی منظم برای نام‌های معتبر ZFS Pool."""

    VALID_VDEV_TYPES: set = {"disk", "mirror", "raidz", "raidz2", "raidz3", "spare"}
    """لیست انواع معتبر vdev در ZFS."""

    def _validate_zpool_name(self, pool_name: str) -> Tuple[bool, Optional[str]]:
        """اعتبارسنجی ساختاری و طول نام pool."""
        if not isinstance(pool_name, str) or not pool_name.strip():
            return False, "نام pool نمی‌تواند خالی باشد."
        if not re.match(self.POOL_NAME_PATTERN, pool_name):
            return False, "نام pool فقط می‌تواند شامل حروف، اعداد، نقطه، زیرخط و خط‌تیره باشد و با حرف/عدد شروع شود."
        if len(pool_name) > 255:
            return False, "نام pool نمی‌تواند بیشتر از 255 کاراکتر باشد."
        return True, None

    def _validate_vdev_type(self, vdev_type: str) -> Tuple[bool, Optional[str]]:
        """اعتبارسنجی نوع vdev بر اساس لیست مجاز."""
        if vdev_type not in self.VALID_VDEV_TYPES:
            return False, f"نوع vdev '{vdev_type}' معتبر نیست. انواع مجاز: {', '.join(self.VALID_VDEV_TYPES)}"
        return True, None

    def _resolve_device_path(self, device_path: str) -> Optional[str]:
        """حل لینک نمادین به مسیر واقعی (مثل /dev/disk/by-id/wwn-... → /dev/sdb)."""
        if not device_path.startswith("/dev/"):
            return None
        try:
            return os.path.realpath(device_path)
        except (OSError, ValueError):
            return None

    def _extract_disk_name_from_real_path(self, real_path: str) -> Optional[str]:
        """استخراج نام دیسک اصلی (sda, nvme0n1) از مسیر واقعی."""
        if not real_path.startswith("/dev/"):
            return None
        name = os.path.basename(real_path)
        if name.startswith(("sd", "hd", "vd")) and any(c.isdigit() for c in name):
            return re.sub(r'\d+$', '', name)
        if name.startswith(("nvme", "mmcblk")) and "p" in name:
            return re.sub(r'p\d+$', '', name)
        if re.match(r'^(sd[a-z]+|nvme\d+n\d+|vd[a-z]+|hd[a-z]+|mmcblk\d+)$', name):
            return name
        return None

    def _validate_and_extract_disk_info(self, device_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        اعتبارسنجی یک مسیر دیسک و استخراج نام کوتاه آن.

        Returns:
            (disk_short_name, error_message)
        """
        if not isinstance(device_path, str) or not device_path.startswith("/dev/"):
            return None, f"مسیر دستگاه باید با '/dev/' شروع شود: {device_path}"

        real_path = self._resolve_device_path(device_path)
        if not real_path or not real_path.startswith("/dev/"):
            return None, f"دستگاه معتبری برای مسیر '{device_path}' یافت نشد."

        disk_name = self._extract_disk_name_from_real_path(real_path)
        if not disk_name:
            return None, f"نام دیسک قابل استخراج نیست از مسیر '{real_path}'."

        return disk_name, None

    def _get_zpool_manager_and_validate(self, pool_name: str, must_exist: bool = True) -> Tuple[Optional[ZpoolManager], Optional[str]]:
        """اعتبارسنجی نام pool و بررسی وجود آن در سیستم."""
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

    def validate_zpool_for_operation(self, pool_name: str, save_to_db: bool, request_data: Dict[str, Any], must_exist: bool = True) -> Union[ZpoolManager, StandardErrorResponse]:
        """اعتبارسنجی کامل pool برای یک عملیات."""
        manager, error = self._get_zpool_manager_and_validate(pool_name, must_exist)
        if manager is None:
            status = 404 if "وجود ندارد" in (error or "") else 400
            return StandardErrorResponse(
                error_code="pool_not_found" if must_exist else "pool_already_exists",
                error_message=error or "خطا در اعتبارسنجی pool.",
                request_data=request_data, status=status, save_to_db=save_to_db)
        return manager

    def validate_zpool_devices(self, devices: List[str], save_to_db: bool, request_data: Dict[str, Any]) -> Union[List[Tuple[str, str]], StandardErrorResponse]:
        """
        اعتبارسنجی لیست دستگاه‌های ورودی و بازگرداندن لیست (device_path, disk_short_name).

        Returns:
            - در موفقیت: لیستی از تاپل‌ها: [(full_path, short_name), ...]
            - در خطا: StandardErrorResponse
        """
        if not isinstance(devices, list) or not devices:
            return StandardErrorResponse(
                error_code="invalid_devices",
                error_message="پارامتر devices باید لیستی غیرخالی از مسیرهای دستگاه باشد.",
                request_data=request_data, status=400, save_to_db=save_to_db)

        validated = []
        for dev in devices:
            disk_name, error = self._validate_and_extract_disk_info(dev)
            if error:
                return StandardErrorResponse(
                    error_code="invalid_device_path",
                    error_message=error,
                    request_data=request_data, status=400, save_to_db=save_to_db)
            validated.append((dev, disk_name))
        return validated

    def validate_vdev_type(self, vdev_type: str, save_to_db: bool, request_data: Dict[str, Any]) -> Union[str, StandardErrorResponse]:
        """اعتبارسنجی نوع vdev."""
        is_valid, error = self._validate_vdev_type(vdev_type)
        if not is_valid:
            return StandardErrorResponse(
                error_code="invalid_vdev_type",
                error_message=error,
                request_data=request_data, status=400, save_to_db=save_to_db)
        return vdev_type

    def _is_valid_wwn_path(self, path: str) -> bool:
        return bool(re.match(r'^/dev/disk/by-id/(wwn-|nvme-)', path))
