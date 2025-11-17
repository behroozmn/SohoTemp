# soho_core_api/views_collection/view_zpool.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from pylibs import (StandardResponse, StandardErrorResponse, get_request_param, logger)
from pylibs.mixins import DiskValidationMixin, ZpoolExistsMixin
from pylibs.zpool import ZpoolManager
from typing import Dict, Any, List, Union


# ------------------------ لیست و جزئیات ------------------------

class ZpoolListView(APIView):
    """
    دریافت لیست خلاصه تمام «پول»های  «زد اف اس» سیستم.

    این ویو تمام «پول»های موجود در سیستم را بدون جزئیات کامل برمی‌گرداند.
    برای دریافت جزئیات کامل یک pool خاص، از `ZpoolDetailView` استفاده کنید.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request) -> Union[StandardResponse, StandardErrorResponse]:
        """
        دریافت لیست «پول»ها.

        Args:
            request: درخواست HTTP GET.

        Query Parameters:
            save_to_db (bool): آیا نتیجه باید در دیتابیس ذخیره شود؟ پیش‌فرض: False

        Returns:
            Union[StandardResponse, StandardErrorResponse]:
                - موفقیت: لیست «پول»ها با فیلدهای خلاصه
                - خطا: StandardErrorResponse در صورت بروز مشکل
        """
        save_to_db: bool = get_request_param(request, "save_to_db", bool, False)
        request_data: Dict[str, Any] = dict(request.query_params)
        try:
            manager = ZpoolManager()
            pools: List[Dict[str, Any]] = manager.list_all_pools()
            return StandardResponse(data=pools, message="لیست «پول»ها با موفقیت دریافت شد.", request_data=request_data, save_to_db=save_to_db)
        except Exception as e:
            logger.error(f"Error in ZpoolListView: {e}")
            return StandardErrorResponse(error_code="zpool_list_error", error_message="خطا در دریافت لیست «پول»ها.", exception=e, request_data=request_data, save_to_db=save_to_db)


class ZpoolDetailView(ZpoolExistsMixin, APIView):
    """
    دریافت جزئیات کامل یک ZFS Pool خاص. این ویو تمام ویژگی‌های pool (مانند health, size, autoreplace, bootfs و ...) را برمی‌گرداند.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pool_name: str) -> Union[StandardResponse, StandardErrorResponse]:
        """
        دریافت جزئیات یک pool با نام مشخص.

        Args:
            request: درخواست HTTP GET.
            pool_name (str): نام pool مورد نظر.

        Query Parameters:
            save_to_db (bool): آیا نتیجه باید در دیتابیس ذخیره شود؟ پیش‌فرض: False

        Returns:
            Union[StandardResponse, StandardErrorResponse]:
                - موفقیت: دیکشنری کامل اطلاعات pool
                - خطا: StandardErrorResponse در صورت عدم وجود یا خطا
        """
        save_to_db: bool = get_request_param(request, "save_to_db", bool, False)
        request_data: Dict[str, Any] = dict(request.query_params)
        manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
        if isinstance(manager, StandardErrorResponse):
            return manager
        detail: Dict[str, Any] = manager.get_pool_detail(pool_name)
        return StandardResponse(data=detail, message=f"جزئیات pool '{pool_name}' دریافت شد.", request_data=request_data, save_to_db=save_to_db)


# ------------------------ دیسک‌های pool ------------------------

class ZpoolDevicesView(ZpoolExistsMixin, APIView):
    """
    دریافت لیست تمام دیسک‌های فیزیکی یک ZFS Pool خاص.

    اطلاعات شامل مسیر دستگاه، وضعیت، نوع vdev، و WWN (در صورت وجود).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pool_name: str) -> Union[StandardResponse, StandardErrorResponse]:
        """
        دریافت لیست دیسک‌های یک pool.

        Args:
            request: درخواست HTTP GET.
            pool_name (str): نام pool مورد نظر.

        Returns:
            Union[StandardResponse, StandardErrorResponse]:
                - موفقیت: لیست دیسک‌ها با وضعیت و جزئیات
                - خطا: StandardErrorResponse در صورت عدم وجود یا خطا
        """
        save_to_db: bool = get_request_param(request, "save_to_db", bool, False)
        request_data: Dict[str, Any] = dict(request.query_params)
        manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
        if isinstance(manager, StandardErrorResponse):
            return manager
        devices: List[Dict[str, Any]] = manager.get_pool_devices(pool_name)
        return StandardResponse(data={"pool_name": pool_name, "devices": devices}, message=f"لیست دیسک‌های pool '{pool_name}' دریافت شد.", request_data=request_data, save_to_db=save_to_db)


# ------------------------ ایجاد / حذف ------------------------

class ZpoolCreateView(ZpoolExistsMixin, DiskValidationMixin, APIView):
    """
    ایجاد یک ZFS Pool جدید با دیسک‌های مشخص‌شده.

    از RAID ساده تا mirror، raidz و spare پشتیبانی می‌شود.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request) -> Union[StandardResponse, StandardErrorResponse]:
        """
        ایجاد pool جدید.

        Args:
            request: درخواست HTTP POST با بدنه JSON.

        Request Body:
            pool_name (str): نام pool جدید.
            devices (List[str]): لیست مسیر دستگاه‌ها (مثال: ["/dev/sdb", "/dev/sdc"]).
            vdev_type (str): نوع vdev (disk, mirror, raidz, raidz2, spare). پیش‌فرض: "disk"
            save_to_db (bool): آیا نتیجه باید در دیتابیس ذخیره شود؟

        Returns:
            Union[StandardResponse, StandardErrorResponse]:
                - موفقیت: جزئیات pool ایجادشده
                - خطا: StandardErrorResponse در صورت اعتبارسنجی یا اجرای ناموفق
        """
        save_to_db: bool = get_request_param(request, "save_to_db", bool, False)
        request_data: Dict[str, Any] = request.data

        pool_name: str = get_request_param(request, "pool_name", str, "")
        devices: List[str] = get_request_param(request, "devices", list, [])
        vdev_type: str = get_request_param(request, "vdev_type", str, "disk")

        if not pool_name or not isinstance(devices, list) or not devices:
            return StandardErrorResponse(error_code="invalid_input", error_message="پارامترهای ضروری (pool_name, devices) الزامی هستند.", request_data=request_data, status=400, save_to_db=save_to_db)

        # اعتبارسنجی نام pool
        manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=False)
        if isinstance(manager, StandardErrorResponse):
            return manager

        # اعتبارسنجی دیسک‌ها
        for dev in devices:
            if not dev.startswith("/dev/"):
                return StandardErrorResponse(error_code="invalid_device_path", error_message=f"مسیر دستگاه باید با /dev/ شروع شود: {dev}", request_data=request_data, status=400, save_to_db=save_to_db)
            disk_name: str = dev.replace("/dev/", "")

            disk_obj = self.validate_disk_and_get_manager(disk_name, save_to_db, request_data)
            if isinstance(disk_obj, StandardErrorResponse):
                return disk_obj

            os_error = self.check_os_disk_protection(disk_obj, disk_name, save_to_db, request_data)
            if os_error:
                return os_error

        success, msg = manager.create_pool(pool_name, devices, vdev_type)
        if success:
            return StandardResponse(data={"pool_name": pool_name, "devices": devices, "vdev_type": vdev_type}, message=msg, request_data=request_data, save_to_db=save_to_db)
        else:
            return StandardErrorResponse(error_code="zpool_create_failed", error_message=msg, request_data=request_data, status=500, save_to_db=save_to_db)


class ZpoolDestroyView(ZpoolExistsMixin, APIView):
    """
    حذف یک ZFS Pool موجود.

    ⚠️ این عملیات غیرقابل بازگشت است و تمام داده‌ها پاک می‌شوند.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pool_name: str) -> Union[StandardResponse, StandardErrorResponse]:
        """
        حذف pool.

        Args:
            request: درخواست HTTP POST.
            pool_name (str): نام pool برای حذف.

        Request Body:
            save_to_db (bool): آیا نتیجه باید در دیتابیس ذخیره شود؟

        Returns:
            Union[StandardResponse, StandardErrorResponse]:
                - موفقیت: تأیید حذف
                - خطا: StandardErrorResponse در صورت شکست
        """
        save_to_db: bool = get_request_param(request, "save_to_db", bool, False)
        request_data: Dict[str, Any] = request.data
        manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
        if isinstance(manager, StandardErrorResponse):
            return manager
        success, msg = manager.destroy_pool(pool_name)
        if success:
            return StandardResponse(data={"pool_name": pool_name}, message=msg, request_data=request_data, save_to_db=save_to_db)
        else:
            return StandardErrorResponse(error_code="zpool_destroy_failed", error_message=msg, request_data=request_data, status=500, save_to_db=save_to_db)


# ------------------------ جایگزینی دیسک ------------------------

class ZpoolReplaceDiskView(ZpoolExistsMixin, DiskValidationMixin, APIView):
    """
    جایگزینی یک دیسک خراب در یک pool با یک دیسک سالم جدید.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pool_name: str) -> Union[StandardResponse, StandardErrorResponse]:
        """
        جایگزینی دیسک خراب با سالم.

        Args:
            request: درخواست HTTP POST.
            pool_name (str): نام pool مورد نظر.

        Request Body:
            old_device (str): مسیر دستگاه خراب (مثال: "/dev/sdb")
            new_device (str): مسیر دستگاه جدید (مثال: "/dev/sdc")
            save_to_db (bool): آیا نتیجه باید در دیتابیس ذخیره شود؟

        Returns:
            Union[StandardResponse, StandardErrorResponse]:
                - موفقیت: اطلاعات جایگزینی
                - خطا: StandardErrorResponse در صورت ناموفقی
        """
        save_to_db: bool = get_request_param(request, "save_to_db", bool, False)
        request_data: Dict[str, Any] = request.data

        old_device: str = request_data.get("old_device")
        new_device: str = request_data.get("new_device")

        if not old_device or not new_device:
            return StandardErrorResponse(error_code="missing_params", error_message="پارامترهای old_device و new_device الزامی هستند.", request_data=request_data, status=400, save_to_db=save_to_db)

        manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
        if isinstance(manager, StandardErrorResponse):
            return manager

        # اعتبارسنجی دیسک جدید
        new_disk_name: str = new_device.replace("/dev/", "")
        disk_obj = self.validate_disk_and_get_manager(new_disk_name, save_to_db, request_data)
        if isinstance(disk_obj, StandardErrorResponse):
            return disk_obj
        os_error = self.check_os_disk_protection(disk_obj, new_disk_name, save_to_db, request_data)
        if os_error:
            return os_error

        success, msg = manager.replace_device(pool_name, old_device, new_device)
        if success:
            return StandardResponse(data={"pool_name": pool_name, "old": old_device, "new": new_device}, message=msg, request_data=request_data, save_to_db=save_to_db)
        else:
            return StandardErrorResponse(error_code="zpool_replace_failed", error_message=msg, request_data=request_data, status=500, save_to_db=save_to_db)


# ------------------------ افزودن spare یا دیسک ------------------------

class ZpoolAddVdevView(ZpoolExistsMixin, DiskValidationMixin, APIView):
    """
    افزودن یک vdev جدید (مثل دیسک، mirror، raidz یا spare) به یک pool موجود.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pool_name: str) -> Union[StandardResponse, StandardErrorResponse]:
        """
        افزودن vdev به pool.

        Args:
            request: درخواست HTTP POST.
            pool_name (str): نام pool مورد نظر.

        Request Body:
            devices (List[str]): لیست مسیر دستگاه‌ها
            vdev_type (str): نوع vdev (disk, mirror, raidz, spare و ...)
            save_to_db (bool): آیا نتیجه باید در دیتابیس ذخیره شود؟

        Returns:
            Union[StandardResponse, StandardErrorResponse]:
                - موفقیت: جزئیات vdev اضافه‌شده
                - خطا: StandardErrorResponse در صورت ناموفقی
        """
        save_to_db: bool = get_request_param(request, "save_to_db", bool, False)
        request_data: Dict[str, Any] = request.data

        devices: List[str] = request_data.get("devices", [])
        vdev_type: str = request_data.get("vdev_type", "disk")

        if not isinstance(devices, list) or not devices:
            return StandardErrorResponse(error_code="invalid_devices", error_message="پارامتر devices باید لیستی از مسیرهای دستگاه باشد.", request_data=request_data, status=400, save_to_db=save_to_db)

        manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
        if isinstance(manager, StandardErrorResponse):
            return manager

        for dev in devices:
            disk_name: str = dev.replace("/dev/", "")
            disk_obj = self.validate_disk_and_get_manager(disk_name, save_to_db, request_data)
            if isinstance(disk_obj, StandardErrorResponse):
                return disk_obj
            os_error = self.check_os_disk_protection(disk_obj, disk_name, save_to_db, request_data)
            if os_error:
                return os_error

        success, msg = manager.add_vdev(pool_name, devices, vdev_type)
        if success:
            return StandardResponse(data={"pool_name": pool_name, "devices": devices, "vdev_type": vdev_type}, message=msg, request_data=request_data, save_to_db=save_to_db)
        else:
            return StandardErrorResponse(error_code="zpool_add_failed", error_message=msg, request_data=request_data, status=500, save_to_db=save_to_db)


# ------------------------ تنظیم ویژگی ------------------------

class ZpoolSetPropertyView(ZpoolExistsMixin, APIView):
    """
    تغییر یک ویژگی ZFS Pool (مثل autoreplace=on یا failmode=continue).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pool_name: str) -> Union[StandardResponse, StandardErrorResponse]:
        """
        تنظیم یک ویژگی pool.

        Args:
            request: درخواست HTTP POST.
            pool_name (str): نام pool مورد نظر.

        Request Body:
            property (str): نام ویژگی (مثال: "autoreplace")
            value (str): مقدار جدید (مثال: "on")
            save_to_db (bool): آیا نتیجه باید در دیتابیس ذخیره شود؟

        Returns:
            Union[StandardResponse, StandardErrorResponse]:
                - موفقیت: جزئیات ویژگی تنظیم‌شده
                - خطا: StandardErrorResponse در صورت ناموفقی
        """
        save_to_db: bool = get_request_param(request, "save_to_db", bool, False)
        request_data: Dict[str, Any] = request.data

        prop: str = request_data.get("property")
        value: str = request_data.get("value")

        if not prop or not value:
            return StandardErrorResponse(error_code="missing_property", error_message="پارامترهای property و value الزامی هستند.", request_data=request_data, status=400, save_to_db=save_to_db)

        manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
        if isinstance(manager, StandardErrorResponse):
            return manager

        success, msg = manager.set_property(pool_name, prop, value)
        if success:
            return StandardResponse(data={"pool_name": pool_name, "property": prop, "value": value}, message=msg, request_data=request_data, save_to_db=save_to_db)
        else:
            return StandardErrorResponse(error_code="zpool_set_property_failed", error_message=msg, request_data=request_data, status=500, save_to_db=save_to_db)

# تست: آیا این کلاس واقعاً لود می‌شود؟
print("✅ ZpoolCreateView loaded:", ZpoolCreateView)