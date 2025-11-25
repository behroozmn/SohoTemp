# soho_core_api/views_collection/view_zpool.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from typing import Dict, Any, List, Optional

from pylibs import StandardResponse, StandardErrorResponse, get_request_param, logger
from pylibs.zpool import ZpoolManager
from pylibs.disk import DiskManager
from pylibs.mixins import ZpoolValidationMixin, DiskValidationMixin


class ZpoolListView(APIView):
    """GET / → لیست تمام poolها"""

    def get(self, request):
        try:
            pools = ZpoolManager().list_all_pools()
            return StandardResponse(data=pools, message="لیست poolها با موفقیت بازیابی شد.")
        except Exception as e:
            logger.error(f"Error in ZpoolListView: {e}")
            return StandardErrorResponse(
                error_code="zpool_list_failed",
                error_message="خطا در دریافت لیست poolها.",
                exception=e,
                status=500,
                request_data=getattr(request, "data", {}),
                save_to_db=get_request_param(request, "save_to_db", bool, False)
            )


class ZpoolDetailView(ZpoolValidationMixin, APIView):
    """GET /<name>/ → جزئیات یک pool"""

    def get(self, request, pool_name: str):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = getattr(request, "data", {})

        zpool_manager_or_error = self.validate_zpool_for_operation(
            pool_name, save_to_db, request_data, must_exist=True
        )
        if isinstance(zpool_manager_or_error, StandardErrorResponse):
            return zpool_manager_or_error

        detail = zpool_manager_or_error.get_pool_detail(pool_name)
        return StandardResponse(data=detail or {}, message=f"جزئیات pool '{pool_name}'.")


class ZpoolDevicesView(ZpoolValidationMixin, APIView):
    """GET /<name>/devices/ → دستگاه‌های یک pool"""

    def get(self, request, pool_name: str):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = getattr(request, "data", {})

        zpool_manager_or_error = self.validate_zpool_for_operation(
            pool_name, save_to_db, request_data, must_exist=True
        )
        if isinstance(zpool_manager_or_error, StandardErrorResponse):
            return zpool_manager_or_error

        devices = zpool_manager_or_error.get_pool_devices(pool_name)
        return StandardResponse(data=devices, message=f"لیست دستگاه‌های pool '{pool_name}'.")


class ZpoolCreateView(ZpoolValidationMixin, DiskValidationMixin, APIView):
    """POST /create/ → ایجاد pool جدید"""

    def post(self, request):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = request.data

        pool_name = get_request_param(request, param_name="pool_name", return_type=str, default="pool_name_not_found")
        devices = get_request_param(request, param_name="devices", return_type=list[str], default=[])

        vdev_type = get_request_param(request, param_name="vdev_type", return_type=str, default="disk")

        zpool_manager_or_error = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=False)
        if isinstance(zpool_manager_or_error, StandardErrorResponse):
            return zpool_manager_or_error

        validated_devices = self.validate_zpool_devices(devices, save_to_db, request_data)
        if isinstance(validated_devices, StandardErrorResponse):
            return validated_devices

        vdev_valid = self.validate_vdev_type(vdev_type, save_to_db, request_data)
        if isinstance(vdev_valid, StandardErrorResponse):
            return vdev_valid

        full_paths = [path for path, _ in validated_devices]

        for _, disk_name in validated_devices:
            disk_manager = DiskManager()
            os_error = self.check_os_disk_protection(disk_manager, disk_name, save_to_db, request_data)
            if os_error:
                return os_error

        try:
            std_out, std_error = zpool_manager_or_error.create_pool(pool_name, full_paths, vdev_valid)
            return StandardResponse(
                message=f"Pool '{pool_name}' با موفقیت ایجاد شد.",
                status=201,
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Zpool create failed: {e}")
            return StandardErrorResponse(
                error_code="zpool_create_failed",
                error_message="خطا در ایجاد pool.",
                exception=e,
                status=500,
                request_data=request_data,
                save_to_db=save_to_db
            )


class ZpoolManageView(ZpoolValidationMixin, DiskValidationMixin, APIView):
    """
    کلاس یکپارچه برای عملیات POST روی pool موجود.
    پارامتر endpoint_type از طریق as_view(endpoint_type=...) تنظیم می‌شود.
    """

    endpoint_type: Optional[str] = None

    def __init__(self, **kwargs):
        self.endpoint_type = kwargs.pop('endpoint_type', None)
        super().__init__(**kwargs)

    def post(self, request, pool_name: str):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = request.data

        zpool_manager_or_error = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
        if isinstance(zpool_manager_or_error, StandardErrorResponse):
            return zpool_manager_or_error

        zpool_manager = zpool_manager_or_error
        et = self.endpoint_type

        if et == "destroy":
            try:
                std_out, std_error =zpool_manager.destroy_pool(pool_name)
                return StandardResponse(message=f"Pool '{pool_name}' با موفقیت حذف شد.", save_to_db=save_to_db)
            except Exception as e:
                return StandardErrorResponse(
                    error_code="zpool_destroy_failed",
                    error_message="خطا در حذف pool.",
                    exception=e,
                    status=500,
                    request_data=request_data,
                    save_to_db=save_to_db
                )

        elif et == "replace":
            old_device = get_request_param(request, param_name="old_device", return_type=str, default="old_device")
            new_device = get_request_param(request, param_name="new_device", return_type=str, default="new_device")
            if not old_device or not new_device:
                return StandardErrorResponse(
                    error_code="missing_params",
                    error_message="پارامترهای old_device و new_device الزامی هستند.",
                    status=400,
                    request_data=request_data,
                    save_to_db=save_to_db
                )

            for dev in [old_device, new_device]:
                _, err = self._validate_and_extract_disk_info(dev)
                if err:
                    return StandardErrorResponse(
                        error_code="invalid_device_path",
                        error_message=err,
                        status=400,
                        request_data=request_data,
                        save_to_db=save_to_db
                    )

            _, disk_name = self._validate_and_extract_disk_info(new_device)
            disk_manager = DiskManager()
            os_error = self.check_os_disk_protection(disk_manager, disk_name, save_to_db, request_data)
            if os_error:
                return os_error

            try:
                std_out, std_error = zpool_manager.replace_device(pool_name, old_device, new_device)
                return StandardResponse(message="دیسک با موفقیت جایگزین شد.", save_to_db=save_to_db)
            except Exception as e:
                return StandardErrorResponse(
                    error_code="zpool_replace_failed",
                    error_message="خطا در جایگزینی دیسک.",
                    exception=e,
                    status=500,
                    request_data=request_data,
                    save_to_db=save_to_db
                )

        elif et == "add":
            devices = get_request_param(request, param_name="devices", return_type=list[str], default=[])
            vdev_type = get_request_param(request, param_name="vdev_type", return_type=str, default="disk")

            validated = self.validate_zpool_devices(devices, save_to_db, request_data)
            if isinstance(validated, StandardErrorResponse):
                return validated

            vdev_ok = self.validate_vdev_type(vdev_type, save_to_db, request_data)
            if isinstance(vdev_ok, StandardErrorResponse):
                return vdev_ok

            full_paths = [p for p, _ in validated]
            for _, dn in validated:
                dm = DiskManager()
                os_err = self.check_os_disk_protection(dm, dn, save_to_db, request_data)
                if os_err:
                    return os_err

            try:
                std_out, std_error =zpool_manager.add_vdev(pool_name, full_paths, vdev_ok)
                return StandardResponse(message="vdev با موفقیت اضافه شد.", save_to_db=save_to_db)
            except Exception as e:
                return StandardErrorResponse(
                    error_code="zpool_add_vdev_failed",
                    error_message="خطا در افزودن vdev.",
                    exception=e,
                    exception_details=f'pool_name: {pool_name}, vdev_ok: {vdev_ok}, full_paths: {full_paths}',
                    status=500,
                    request_data=request_data,
                    save_to_db=save_to_db

                )

        elif et == "set-property":
            prop = get_request_param(request, param_name="prop", return_type=str, default="prop_not_found")
            value = get_request_param(request, param_name="value", return_type=str, default="value_not_found")
            if not prop or not value:
                return StandardErrorResponse(
                    error_code="missing_params",
                    error_message="پارامترهای property و value الزامی هستند.",
                    status=400,
                    request_data=request_data,
                    save_to_db=save_to_db
                )

            try:
                std_out, std_error =zpool_manager.set_property(pool_name, prop, value)
                return StandardResponse(
                    message=f"ویژگی '{prop}' با مقدار '{value}' تنظیم شد.",
                    save_to_db=save_to_db
                )
            except Exception as e:
                return StandardErrorResponse(
                    error_code="zpool_set_property_failed",
                    error_message="خطا در تنظیم ویژگی pool.",
                    exception=e,
                    status=500,
                    request_data=request_data,
                    save_to_db=save_to_db
                )

        else:
            return StandardErrorResponse(
                error_code="invalid_endpoint_type",
                error_message=f"نوع endpoint نامعتبر: {et}",
                status=400,
                request_data=request_data,
                save_to_db=save_to_db
            )
