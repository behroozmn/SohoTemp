# soho_core_api/views_collection/view_zpool.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from pylibs import StandardResponse, StandardErrorResponse, get_request_param,logger
from pylibs.zpool import ZpoolManager
from pylibs.mixins import ZpoolNameValidationMixin, ZpoolExistsMixin
from .view_disk import DiskValidationMixin, OSDiskProtectionMixin
from pylibs.disk import DiskManager
import logging


# ------------------------ لیست و جزئیات ------------------------
class ZpoolListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)
        try:
            manager = ZpoolManager()
            pools = manager.list_all_pools()
            return StandardResponse(
                data=pools,
                message="لیست poolها با موفقیت دریافت شد.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Error in ZpoolListView: {e}")
            return StandardErrorResponse(
                error_code="zpool_list_error",
                error_message="خطا در دریافت لیست poolها.",
                exception=e,
                request_data=request_data,
                save_to_db=save_to_db
            )

class ZpoolDetailView(ZpoolExistsMixin, APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pool_name):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)
        manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
        if isinstance(manager, StandardErrorResponse):
            return manager
        detail = manager.get_pool_detail(pool_name)
        return StandardResponse(
            data=detail,
            message=f"جزئیات pool '{pool_name}' دریافت شد.",
            request_data=request_data,
            save_to_db=save_to_db
        )

# ------------------------ دیسک‌های pool ------------------------
class ZpoolDevicesView(ZpoolExistsMixin, APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pool_name):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)
        manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
        if isinstance(manager, StandardErrorResponse):
            return manager
        devices = manager.get_pool_devices(pool_name)
        return StandardResponse(
            data={"pool_name": pool_name, "devices": devices},
            message=f"لیست دیسک‌های pool '{pool_name}' دریافت شد.",
            request_data=request_data,
            save_to_db=save_to_db
        )

# ------------------------ ایجاد / حذف ------------------------
class ZpoolCreateView(ZpoolExistsMixin, DiskValidationMixin, OSDiskProtectionMixin, APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = request.data

        pool_name = request_data.get("pool_name")
        devices = request_data.get("devices", [])
        vdev_type = request_data.get("vdev_type", "disk")

        if not pool_name or not isinstance(devices, list) or not devices:
            return StandardErrorResponse(
                error_code="invalid_input",
                error_message="پارامترهای ضروری (pool_name, devices) الزامی هستند.",
                request_data=request_data,
                status=400,
                save_to_db=save_to_db
            )

        # اعتبارسنجی نام pool
        manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=False)
        if isinstance(manager, StandardErrorResponse):
            return manager

        # اعتبارسنجی دیسک‌ها
        disk_manager = DiskManager()
        for dev in devices:
            if not dev.startswith("/dev/"):
                return StandardErrorResponse(
                    error_code="invalid_device_path",
                    error_message=f"مسیر دستگاه باید با /dev/ شروع شود: {dev}",
                    request_data=request_data,
                    status=400,
                    save_to_db=save_to_db
                )
            disk_name = dev.replace("/dev/", "")
            disk_obj = self.validate_disk_and_get_manager(disk_name, save_to_db, request_data)
            if isinstance(disk_obj, StandardErrorResponse):
                return disk_obj
            os_error = self.check_os_disk_protection(disk_obj, disk_name, save_to_db, request_data)
            if os_error:
                return os_error

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

class ZpoolDestroyView(ZpoolExistsMixin, APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pool_name):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = request.data
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
class ZpoolReplaceDiskView(ZpoolExistsMixin, DiskValidationMixin, OSDiskProtectionMixin, APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pool_name):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = request.data

        old_device = request_data.get("old_device")
        new_device = request_data.get("new_device")

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

        # اعتبارسنجی دیسک جدید
        new_disk_name = new_device.replace("/dev/", "")
        disk_obj = self.validate_disk_and_get_manager(new_disk_name, save_to_db, request_data)
        if isinstance(disk_obj, StandardErrorResponse):
            return disk_obj
        os_error = self.check_os_disk_protection(disk_obj, new_disk_name, save_to_db, request_data)
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

# ------------------------ افزودن spare یا دیسک ------------------------
class ZpoolAddVdevView(ZpoolExistsMixin, DiskValidationMixin, OSDiskProtectionMixin, APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pool_name):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = request.data

        devices = request_data.get("devices", [])
        vdev_type = request_data.get("vdev_type", "disk")  # می‌تواند: disk, mirror, raidz, spare

        if not isinstance(devices, list) or not devices:
            return StandardErrorResponse(
                error_code="invalid_devices",
                error_message="پارامتر devices باید لیستی از مسیرهای دستگاه باشد.",
                request_data=request_data,
                status=400,
                save_to_db=save_to_db
            )

        manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
        if isinstance(manager, StandardErrorResponse):
            return manager

        # اعتبارسنجی هر دیسک
        disk_manager = DiskManager()
        for dev in devices:
            disk_name = dev.replace("/dev/", "")
            disk_obj = self.validate_disk_and_get_manager(disk_name, save_to_db, request_data)
            if isinstance(disk_obj, StandardErrorResponse):
                return disk_obj
            os_error = self.check_os_disk_protection(disk_obj, disk_name, save_to_db, request_data)
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
class ZpoolSetPropertyView(ZpoolExistsMixin, APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pool_name):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = request.data

        prop = request_data.get("property")
        value = request_data.get("value")

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