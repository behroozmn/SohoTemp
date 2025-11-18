# soho_core_api/views_collection/view_zpool.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from typing import Dict, Any, List, Optional

from pylibs.zpool import ZpoolManager
from pylibs.disk import DiskManager
from pylibs.mixins import ZpoolValidationMixin, DiskValidationMixin
from pylibs import StandardErrorResponse, logger


def _get_save_to_db_flag(request) -> bool:
    """استخراج save_to_db فقط در POST، در غیر این صورت False."""
    return request.data.get("save_to_db", False) is True if request.method in ("POST", "PUT", "PATCH") else False


class ZpoolInfoView(ZpoolValidationMixin, APIView):
    """مدیریت تمام درخواست‌های خواندنی (GET)."""

    def get(self, request, pool_name: Optional[str] = None, action: Optional[str] = None):
        save_to_db = False  # GET هرگز save_to_db=True نیست
        request_data = getattr(request, "data", {})

        try:
            zpool_manager = ZpoolManager()
        except Exception as e:
            logger.error(f"Failed to initialize ZpoolManager: {e}")
            return Response(
                StandardErrorResponse(
                    error_code="zpool_init_failed",
                    error_message="خطا در راه‌اندازی مدیر ZFS.",
                    request_data=request_data,
                    status=500,
                    save_to_db=save_to_db
                ).to_dict(),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # GET / → لیست تمام poolها
        if pool_name is None and action is None:
            pools = zpool_manager.list_all_pools()
            return Response(pools, status=status.HTTP_200_OK)

        # بررسی وجود pool
        if not zpool_manager.pool_exists(pool_name):
            return Response(
                StandardErrorResponse(
                    error_code="pool_not_found",
                    error_message=f"Pool '{pool_name}' وجود ندارد.",
                    request_data=request_data,
                    status=404,
                    save_to_db=save_to_db
                ).to_dict(),
                status=status.HTTP_404_NOT_FOUND
            )

        # GET /<name>/ → جزئیات
        if action is None:
            detail = zpool_manager.get_pool_detail(pool_name)
            return Response(detail or {}, status=status.HTTP_200_OK)

        # GET /<name>/devices/ → دستگاه‌ها
        if action == "devices":
            devices = zpool_manager.get_pool_devices(pool_name)
            return Response(devices, status=status.HTTP_200_OK)

        return Response(
            StandardErrorResponse(
                error_code="invalid_action",
                error_message="اکشن درخواستی معتبر نیست.",
                request_data=request_data,
                status=400,
                save_to_db=save_to_db
            ).to_dict(),
            status=status.HTTP_400_BAD_REQUEST
        )


class ZpoolActionView(ZpoolValidationMixin, DiskValidationMixin, APIView):
    """مدیریت تمام عملیات تغییر‌دهنده (POST)."""

    def post(self, request, pool_name: Optional[str] = None, action: Optional[str] = None):
        save_to_db = _get_save_to_db_flag(request)
        request_data = request.data

        # --- ایجاد pool (action=None و pool_name=None، URL: /create/) ---
        if action is None and pool_name is None:
            return self._handle_create_pool(request, save_to_db, request_data)

        # --- بقیه اکشن‌ها نیاز به pool_name دارند ---
        if pool_name is None:
            return Response(
                StandardErrorResponse(
                    error_code="missing_pool_name",
                    error_message="نام pool الزامی است.",
                    request_data=request_data,
                    status=400,
                    save_to_db=save_to_db
                ).to_dict(),
                status=status.HTTP_400_BAD_REQUEST
            )

        # اعتبارسنجی pool (باید وجود داشته باشد)
        zpool_manager_or_error = self.validate_zpool_for_operation(
            pool_name=pool_name,
            save_to_db=save_to_db,
            request_data=request_data,
            must_exist=True
        )
        if isinstance(zpool_manager_or_error, StandardErrorResponse):
            return Response(zpool_manager_or_error.to_dict(), status=zpool_manager_or_error.status)

        zpool_manager = zpool_manager_or_error

        # --- اکشن‌های مختلف ---
        if action == "destroy":
            return self._handle_destroy_pool(zpool_manager, pool_name, save_to_db, request_data)
        elif action == "replace":
            return self._handle_replace_disk(zpool_manager, pool_name, request, save_to_db, request_data)
        elif action == "add":
            return self._handle_add_vdev(zpool_manager, pool_name, request, save_to_db, request_data)
        elif action == "set-property":
            return self._handle_set_property(zpool_manager, pool_name, request, save_to_db, request_data)
        else:
            return Response(
                StandardErrorResponse(
                    error_code="invalid_action",
                    error_message="اکشن درخواستی معتبر نیست.",
                    request_data=request_data,
                    status=400,
                    save_to_db=save_to_db
                ).to_dict(),
                status=status.HTTP_400_BAD_REQUEST
            )

    # --- Handlers ---
    def _handle_create_pool(self, request, save_to_db: bool, request_data: Dict[str, Any]):
        pool_name = request_data.get("pool_name")
        devices = request_data.get("devices", [])
        vdev_type = request_data.get("vdev_type", "disk")

        # اعتبارسنجی pool (نباید وجود داشته باشد)
        zpool_manager_or_error = self.validate_zpool_for_operation(
            pool_name=pool_name,
            save_to_db=save_to_db,
            request_data=request_data,
            must_exist=False
        )
        if isinstance(zpool_manager_or_error, StandardErrorResponse):
            return Response(zpool_manager_or_error.to_dict(), status=zpool_manager_or_error.status)

        # اعتبارسنجی دستگاه‌ها
        validated_devices = self.validate_zpool_devices(devices, save_to_db, request_data)
        if isinstance(validated_devices, StandardErrorResponse):
            return Response(validated_devices.to_dict(), status=validated_devices.status)

        # اعتبارسنجی vdev_type
        vdev_valid = self.validate_vdev_type(vdev_type, save_to_db, request_data)
        if isinstance(vdev_valid, StandardErrorResponse):
            return Response(vdev_valid.to_dict(), status=vdev_valid.status)

        full_paths = [path for path, _ in validated_devices]

        # بررسی OS disk
        for _, disk_name in validated_devices:
            try:
                disk_manager = DiskManager()
                os_error = self.check_os_disk_protection(disk_manager, disk_name, save_to_db, request_data)
                if os_error:
                    return Response(os_error.to_dict(), status=os_error.status)
            except Exception as e:
                logger.error(f"DiskManager error for {disk_name}: {e}")
                return Response(
                    StandardErrorResponse(
                        error_code="disk_check_failed",
                        error_message=f"خطا در بررسی دیسک {disk_name}.",
                        request_data=request_data,
                        status=500,
                        save_to_db=save_to_db
                    ).to_dict(),
                    status=500
                )

        # ایجاد pool
        try:
            zpool_manager_or_error.create_pool(pool_name, full_paths, vdev_valid)
        except Exception as e:
            logger.error(f"Create pool failed: {e}")
            return Response(
                StandardErrorResponse(
                    error_code="zpool_create_failed",
                    error_message=str(e),
                    request_data=request_data,
                    status=500,
                    save_to_db=save_to_db
                ).to_dict(),
                status=500
            )

        return Response({"message": f"Pool '{pool_name}' با موفقیت ایجاد شد."}, status=201)

    def _handle_destroy_pool(self, zpool_manager, pool_name: str, save_to_db: bool, request_data: Dict[str, Any]):
        try:
            zpool_manager.destroy_pool(pool_name)
        except Exception as e:
            logger.error(f"Destroy pool failed: {e}")
            return Response(
                StandardErrorResponse(
                    error_code="zpool_destroy_failed",
                    error_message=str(e),
                    request_data=request_data,
                    status=500,
                    save_to_db=save_to_db
                ).to_dict(),
                status=500
            )
        return Response({"message": f"Pool '{pool_name}' حذف شد."}, status=200)

    def _handle_replace_disk(self, zpool_manager, pool_name: str, request, save_to_db: bool, request_data: Dict[str, Any]):
        old_device = request_data.get("old_device")
        new_device = request_data.get("new_device")

        if not old_device or not new_device:
            return Response(
                StandardErrorResponse(
                    error_code="missing_params",
                    error_message="پارامترهای old_device و new_device الزامی هستند.",
                    request_data=request_data,
                    status=400,
                    save_to_db=save_to_db
                ).to_dict(),
                status=400
            )

        # اعتبارسنجی دستگاه‌ها
        for dev, label in [(old_device, "old_device"), (new_device, "new_device")]:
            disk_name, error = self._validate_and_extract_disk_info(dev)
            if error:
                return Response(
                    StandardErrorResponse(
                        error_code="invalid_device_path",
                        error_message=f"دستگاه {label}: {error}",
                        request_data=request_data,
                        status=400,
                        save_to_db=save_to_db
                    ).to_dict(),
                    status=400
                )
            # بررسی OS برای دیسک جدید (قدیمی ممکن است خراب باشد)
            if label == "new_device":
                try:
                    disk_manager = DiskManager()
                    os_error = self.check_os_disk_protection(disk_manager, disk_name, save_to_db, request_data)
                    if os_error:
                        return Response(os_error.to_dict(), status=os_error.status)
                except Exception as e:
                    logger.error(f"Disk check failed for {disk_name}: {e}")
                    return Response(
                        StandardErrorResponse(
                            error_code="disk_check_failed",
                            error_message=f"خطا در بررسی دیسک جدید ({disk_name}).",
                            request_data=request_data,
                            status=500,
                            save_to_db=save_to_db
                        ).to_dict(),
                        status=500
                    )

        try:
            zpool_manager.replace_device(pool_name, old_device, new_device)
        except Exception as e:
            logger.error(f"Replace device failed: {e}")
            return Response(
                StandardErrorResponse(
                    error_code="zpool_replace_failed",
                    error_message=str(e),
                    request_data=request_data,
                    status=500,
                    save_to_db=save_to_db
                ).to_dict(),
                status=500
            )
        return Response({"message": "دیسک با موفقیت جایگزین شد."}, status=200)

    def _handle_add_vdev(self, zpool_manager, pool_name: str, request, save_to_db: bool, request_data: Dict[str, Any]):
        devices = request_data.get("devices", [])
        vdev_type = request_data.get("vdev_type", "disk")

        validated_devices = self.validate_zpool_devices(devices, save_to_db, request_data)
        if isinstance(validated_devices, StandardErrorResponse):
            return Response(validated_devices.to_dict(), status=validated_devices.status)

        vdev_valid = self.validate_vdev_type(vdev_type, save_to_db, request_data)
        if isinstance(vdev_valid, StandardErrorResponse):
            return Response(vdev_valid.to_dict(), status=vdev_valid.status)

        full_paths = [path for path, _ in validated_devices]

        # بررسی OS برای دیسک‌های جدید
        for _, disk_name in validated_devices:
            try:
                disk_manager = DiskManager()
                os_error = self.check_os_disk_protection(disk_manager, disk_name, save_to_db, request_data)
                if os_error:
                    return Response(os_error.to_dict(), status=os_error.status)
            except Exception as e:
                logger.error(f"Disk check failed for {disk_name}: {e}")
                return Response(
                    StandardErrorResponse(
                        error_code="disk_check_failed",
                        error_message=f"خطا در بررسی دیسک {disk_name}.",
                        request_data=request_data,
                        status=500,
                        save_to_db=save_to_db
                    ).to_dict(),
                    status=500
                )

        try:
            zpool_manager.add_vdev(pool_name, full_paths, vdev_valid)
        except Exception as e:
            logger.error(f"Add vdev failed: {e}")
            return Response(
                StandardErrorResponse(
                    error_code="zpool_add_vdev_failed",
                    error_message=str(e),
                    request_data=request_data,
                    status=500,
                    save_to_db=save_to_db
                ).to_dict(),
                status=500
            )
        return Response({"message": "vdev با موفقیت اضافه شد."}, status=200)

    def _handle_set_property(self, zpool_manager, pool_name: str, request, save_to_db: bool, request_data: Dict[str, Any]):
        prop = request_data.get("property")
        value = request_data.get("value")

        if not prop or not value:
            return Response(
                StandardErrorResponse(
                    error_code="missing_params",
                    error_message="پارامترهای property و value الزامی هستند.",
                    request_data=request_data,
                    status=400,
                    save_to_db=save_to_db
                ).to_dict(),
                status=400
            )

        try:
            zpool_manager.set_property(pool_name, prop, value)
        except Exception as e:
            logger.error(f"Set property failed: {e}")
            return Response(
                StandardErrorResponse(
                    error_code="zpool_set_property_failed",
                    error_message=str(e),
                    request_data=request_data,
                    status=500,
                    save_to_db=save_to_db
                ).to_dict(),
                status=500
            )
        return Response({"message": f"ویژگی '{prop}' با مقدار '{value}' تنظیم شد."}, status=200)