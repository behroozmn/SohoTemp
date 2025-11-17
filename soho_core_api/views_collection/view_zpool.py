# soho_core_api/views_collection/view_zpool.py
import os
import re
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from pylibs import StandardResponse, StandardErrorResponse, get_request_param, logger
from pylibs.mixins import ZpoolValidationMixin, DiskValidationMixin
from pylibs.zpool import ZpoolManager
from typing import Dict, Any, List, Union, Optional


# ------------------------ View اصلی Zpool (لیست + جزئیات) ------------------------

class ZpoolView(ZpoolValidationMixin, APIView):
    """
    دریافت لیست تمام ZFS Poolها (اگر pool_name داده نشود) یا جزئیات یک pool خاص.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pool_name: Optional[str] = None) -> Union[StandardResponse, StandardErrorResponse]:
        save_to_db: bool = get_request_param(request, "save_to_db", bool, False)
        request_data: Dict[str, Any] = dict(request.query_params)

        if pool_name is None:
            # لیست تمام poolها
            try:
                manager = ZpoolManager()
                pools = manager.list_all_pools()
                return StandardResponse(
                    data=pools,
                    message="لیست ZFS Poolها با موفقیت دریافت شد.",
                    request_data=request_data,
                    save_to_db=save_to_db
                )
            except Exception as e:
                logger.error(f"Error in ZpoolView (list): {e}")
                return StandardErrorResponse(
                    error_code="zpool_list_error",
                    error_message="خطا در دریافت لیست ZFS Poolها.",
                    exception=e,
                    request_data=request_data,
                    save_to_db=save_to_db
                )
        else:
            # جزئیات یک pool خاص
            manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
            if isinstance(manager, StandardErrorResponse):
                return manager
            detail = manager.get_pool_detail(pool_name)
            if detail is None:
                return StandardErrorResponse(
                    error_code="pool_detail_not_found",
                    error_message=f"جزئیات pool '{pool_name}' یافت نشد.",
                    request_data=request_data,
                    status=404,
                    save_to_db=save_to_db
                )
            return StandardResponse(
                data=detail,
                message=f"جزئیات ZFS Pool '{pool_name}' دریافت شد.",
                request_data=request_data,
                save_to_db=save_to_db
            )


# ------------------------ دیسک‌های pool ------------------------

class ZpoolDevicesView(ZpoolValidationMixin, APIView):
    """دریافت لیست تمام دیسک‌های فیزیکی یک ZFS Pool با وضعیت و WWN."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pool_name: str) -> Union[StandardResponse, StandardErrorResponse]:
        save_to_db: bool = get_request_param(request, "save_to_db", bool, False)
        request_data: Dict[str, Any] = dict(request.query_params)

        manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
        if isinstance(manager, StandardErrorResponse):
            return manager

        devices = manager.get_pool_devices(pool_name)
        return StandardResponse(
            data={"pool_name": pool_name, "devices": devices},
            message=f"لیست دیسک‌های ZFS Pool '{pool_name}' دریافت شد.",
            request_data=request_data,
            save_to_db=save_to_db
        )


# ------------------------ ایجاد / حذف ------------------------

class ZpoolCreateView(ZpoolValidationMixin, DiskValidationMixin, APIView):
    """ایجاد یک ZFS Pool جدید با پشتیبانی کامل از مسیرهای WWN/NVMe."""
    permission_classes = [IsAuthenticated]

    def post(self, request) -> Union[StandardResponse, StandardErrorResponse]:
        save_to_db: bool = get_request_param(request, "save_to_db", bool, False)
        request_data: Dict[str, Any] = request.data

        pool_name: str = request_data.get("pool_name")
        devices: List[str] = request_data.get("devices", [])
        vdev_type: str = request_data.get("vdev_type", "disk")

        if not pool_name or not isinstance(devices, list) or not devices:
            return StandardErrorResponse(
                error_code="invalid_input",
                error_message="پارامترهای ضروری (pool_name, devices) الزامی هستند.",
                request_data=request_data,
                status=400,
                save_to_db=save_to_db
            )

        # اعتبارسنجی pool (نباید وجود داشته باشد)
        manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=False)
        if isinstance(manager, StandardErrorResponse):
            return manager

        # اعتبارسنجی vdev_type
        vdev_type = self.validate_vdev_type(vdev_type, save_to_db, request_data)
        if isinstance(vdev_type, StandardErrorResponse):
            return vdev_type

        # اعتبارسنجی هر دیسک
        for dev in devices:
            if not dev.startswith("/dev/"):
                return StandardErrorResponse(
                    error_code="invalid_device_path",
                    error_message=f"مسیر دستگاه باید با '/dev/' شروع شود: {dev}",
                    request_data=request_data,
                    status=400,
                    save_to_db=save_to_db
                )

            disk_obj = self.validate_disk_and_get_manager(dev, save_to_db, request_data)
            if isinstance(disk_obj, StandardErrorResponse):
                return disk_obj

            # استخراج نام کوتاه برای محافظت از دیسک سیستم‌عامل
            disk_short_name = self._extract_disk_name_from_real_path(os.path.realpath(dev))
            if not disk_short_name:
                disk_short_name = os.path.basename(dev).split("/")[0]

            os_error = self.check_os_disk_protection(disk_obj, disk_short_name, save_to_db, request_data)
            if os_error:
                return os_error

        # ایجاد pool
        success, msg = manager.create_pool(pool_name, devices, vdev_type)
        if success:
            return StandardResponse(
                data={"pool_name": pool_name, "devices": devices, "vdev_type": vdev_type},
                message=msg,
                request_data=request_data,
                save_to_db=save_to_db
            )
        else:
            return StandardErrorResponse(
                error_code="zpool_create_failed",
                error_message=msg,
                request_data=request_data,
                status=500,
                save_to_db=save_to_db
            )


class ZpoolDestroyView(ZpoolValidationMixin, APIView):
    """حذف یک ZFS Pool موجود — عملیات غیرقابل بازگشت."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pool_name: str) -> Union[StandardResponse, StandardErrorResponse]:
        save_to_db: bool = get_request_param(request, "save_to_db", bool, False)
        request_data: Dict[str, Any] = request.data

        manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
        if isinstance(manager, StandardErrorResponse):
            return manager

        success, msg = manager.destroy_pool(pool_name)
        if success:
            return StandardResponse(
                data={"pool_name": pool_name},
                message=msg,
                request_data=request_data,
                save_to_db=save_to_db
            )
        else:
            return StandardErrorResponse(
                error_code="zpool_destroy_failed",
                error_message=msg,
                request_data=request_data,
                status=500,
                save_to_db=save_to_db
            )


# ------------------------ جایگزینی دیسک ------------------------

class ZpoolReplaceDiskView(ZpoolValidationMixin, DiskValidationMixin, APIView):
    """جایگزینی دیسک خراب با دیسک سالم."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pool_name: str) -> Union[StandardResponse, StandardErrorResponse]:
        save_to_db: bool = get_request_param(request, "save_to_db", bool, False)
        request_data: Dict[str, Any] = request.data

        old_device: str = request_data.get("old_device")
        new_device: str = request_data.get("new_device")

        if not old_device or not new_device:
            return StandardErrorResponse(
                error_code="missing_params",
                error_message="پارامترهای old_device و new_device الزامی هستند.",
                request_data=request_data,
                status=400,
                save_to_db=save_to_db
            )

        manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
        if isinstance(manager, StandardErrorResponse):
            return manager

        if not new_device.startswith("/dev/"):
            return StandardErrorResponse(
                error_code="invalid_device_path",
                error_message=f"مسیر دستگاه جدید باید با '/dev/' شروع شود: {new_device}",
                request_data=request_data,
                status=400,
                save_to_db=save_to_db
            )

        disk_obj = self.validate_disk_and_get_manager(new_device, save_to_db, request_data)
        if isinstance(disk_obj, StandardErrorResponse):
            return disk_obj

        disk_short_name = self._extract_disk_name_from_real_path(os.path.realpath(new_device))
        if not disk_short_name:
            disk_short_name = os.path.basename(new_device)

        os_error = self.check_os_disk_protection(disk_obj, disk_short_name, save_to_db, request_data)
        if os_error:
            return os_error

        success, msg = manager.replace_device(pool_name, old_device, new_device)
        if success:
            return StandardResponse(
                data={"pool_name": pool_name, "old": old_device, "new": new_device},
                message=msg,
                request_data=request_data,
                save_to_db=save_to_db
            )
        else:
            return StandardErrorResponse(
                error_code="zpool_replace_failed",
                error_message=msg,
                request_data=request_data,
                status=500,
                save_to_db=save_to_db
            )


# ------------------------ افزودن spare یا vdev ------------------------

class ZpoolAddVdevView(ZpoolValidationMixin, DiskValidationMixin, APIView):
    """افزودن یک vdev جدید (مثل spare, mirror, raidz) به pool موجود."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pool_name: str) -> Union[StandardResponse, StandardErrorResponse]:
        save_to_db: bool = get_request_param(request, "save_to_db", bool, False)
        request_data: Dict[str, Any] = request.data

        devices: List[str] = request_data.get("devices", [])
        vdev_type: str = request_data.get("vdev_type", "disk")

        if not isinstance(devices, list) or not devices:
            return StandardErrorResponse(
                error_code="invalid_devices",
                error_message="پارامتر devices باید لیستی غیرخالی از مسیرهای دستگاه باشد.",
                request_data=request_data,
                status=400,
                save_to_db=save_to_db
            )

        manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
        if isinstance(manager, StandardErrorResponse):
            return manager

        vdev_type = self.validate_vdev_type(vdev_type, save_to_db, request_data)
        if isinstance(vdev_type, StandardErrorResponse):
            return vdev_type

        for dev in devices:
            if not dev.startswith("/dev/"):
                return StandardErrorResponse(
                    error_code="invalid_device_path",
                    error_message=f"مسیر دستگاه باید با '/dev/' شروع شود: {dev}",
                    request_data=request_data,
                    status=400,
                    save_to_db=save_to_db
                )

            disk_obj = self.validate_disk_and_get_manager(dev, save_to_db, request_data)
            if isinstance(disk_obj, StandardErrorResponse):
                return disk_obj

            disk_short_name = self._extract_disk_name_from_real_path(os.path.realpath(dev))
            if not disk_short_name:
                disk_short_name = os.path.basename(dev)

            os_error = self.check_os_disk_protection(disk_obj, disk_short_name, save_to_db, request_data)
            if os_error:
                return os_error

        success, msg = manager.add_vdev(pool_name, devices, vdev_type)
        if success:
            return StandardResponse(
                data={"pool_name": pool_name, "devices": devices, "vdev_type": vdev_type},
                message=msg,
                request_data=request_data,
                save_to_db=save_to_db
            )
        else:
            return StandardErrorResponse(
                error_code="zpool_add_failed",
                error_message=msg,
                request_data=request_data,
                status=500,
                save_to_db=save_to_db
            )


# ------------------------ تنظیم ویژگی ------------------------

class ZpoolSetPropertyView(ZpoolValidationMixin, APIView):
    """تنظیم یک ویژگی ZFS Pool (مثل autoreplace=on یا failmode=continue)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pool_name: str) -> Union[StandardResponse, StandardErrorResponse]:
        save_to_db: bool = get_request_param(request, "save_to_db", bool, False)
        request_data: Dict[str, Any] = request.data

        prop: str = request_data.get("property")
        value: str = request_data.get("value")

        if not prop or not value:
            return StandardErrorResponse(
                error_code="missing_property",
                error_message="پارامترهای property و value الزامی هستند.",
                request_data=request_data,
                status=400,
                save_to_db=save_to_db
            )

        manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
        if isinstance(manager, StandardErrorResponse):
            return manager

        success, msg = manager.set_property(pool_name, prop, value)
        if success:
            return StandardResponse(
                data={"pool_name": pool_name, "property": prop, "value": value},
                message=msg,
                request_data=request_data,
                save_to_db=save_to_db
            )
        else:
            return StandardErrorResponse(
                error_code="zpool_set_property_failed",
                error_message=msg,
                request_data=request_data,
                status=500,
                save_to_db=save_to_db
            )