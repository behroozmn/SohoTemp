# soho_core_api/views_collection/view_disk.py

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from pylibs import StandardResponse, StandardErrorResponse, get_request_param
from pylibs.disk import DiskManager
from django.utils import timezone
import logging

from soho_core_api.models import Disks

logger = logging.getLogger(__name__)

from typing import List, Dict, Any
from soho_core_api.models import Disks  # فرض: مدل Disk در همان اپلیکیشن تعریف شده


def db_update_disks(disks_info: List[Dict[str, Any]]) -> None:
    """
    ذخیره یا به‌روزرسانی اطلاعات **همه دیسک‌های سیستم** در جدول `disks`.

    این تابع از دیکشنری داده‌های خروجی `DiskManager.get_disks_info_all()` استفاده می‌کند.
    برای هر دیسک، یک رکورد در جدول `disks` ایجاد یا به‌روزرسانی می‌شود.

    Args:
        disks_info (List[Dict[str, Any]]): لیستی از دیکشنری‌ها که هر کدام اطلاعات یک دیسک را شامل می‌شود.
            هر دیکشنری باید حداقل شامل کلید `'disk'` باشد (نام دیسک، مثل `'sda'`).

    Raises:
        ValueError: اگر هر یک از آیتم‌های لیست، دیکشنری نباشد یا کلید `'disk'` را نداشته باشد.
        Exception: در صورت بروز خطا در تعامل با دیتابیس (توسط Django ORM).

    Example:
        >>> manager = DiskManager()
        >>> all_disks = manager.get_disks_info_all()
        >>> db_update_disks(all_disks)
    """
    if not isinstance(disks_info, list):
        raise ValueError("ورودی باید یک لیست از دیکشنری‌ها باشد.")

    for disk_data in disks_info:
        if not isinstance(disk_data, dict):
            raise ValueError("هر آیتم لیست باید یک دیکشنری باشد.")
        if 'disk' not in disk_data:
            raise ValueError("هر دیکشنری باید شامل کلید 'disk' باشد.")

        Disks.objects.update_or_create(
            disk_name=disk_data['disk'],
            defaults={
                'model': disk_data.get('model', ''),
                'vendor': disk_data.get('vendor', ''),
                'state': disk_data.get('state', ''),
                'device_path': disk_data.get('device_path', ''),
                'physical_block_size': disk_data.get('physical_block_size', ''),
                'logical_block_size': disk_data.get('logical_block_size', ''),
                'scheduler': disk_data.get('scheduler', ''),
                'wwid': disk_data.get('wwid', ''),
                'total_bytes': disk_data.get('total_bytes'),
                'temperature_celsius': disk_data.get('temperature_celsius'),
                'wwn': disk_data.get('wwn', ''),
                'uuid': disk_data.get('uuid'),
                'slot_number': disk_data.get('slot_number'),
                'disk_type': disk_data.get('type', ''),
                'has_partition': disk_data.get('has_partition', False),
                'used_bytes': disk_data.get('used_bytes'),
                'free_bytes': disk_data.get('free_bytes'),
                'usage_percent': disk_data.get('usage_percent'),
                'partitions_data': disk_data.get('partitions', []),
            }
        )


def db_update_disk_single(disk_info: Dict[str, Any]) -> None:
    """
    ذخیره یا به‌روزرسانی اطلاعات **یک دیسک خاص** در جدول `disks`.

    این تابع از دیکشنری خروجی `DiskManager.get_disk_info(disk_name)` استفاده می‌کند.

    Args:
        disk_info (Dict[str, Any]): دیکشنری حاوی اطلاعات یک دیسک.
            باید شامل کلید `'disk'` (نام دیسک، مثل `'nvme0n1'`) باشد.

    Raises:
        ValueError: اگر ورودی دیکشنری نباشد یا کلید `'disk'` را نداشته باشد.
        Exception: در صورت بروز خطا در تعامل با دیتابیس (توسط Django ORM).

    Example:
        >>> manager = DiskManager()
        >>> disk_data = manager.get_disk_info('sda')
        >>> db_update_disk_single(disk_data)
    """
    if not isinstance(disk_info, dict):
        raise ValueError("ورودی باید یک دیکشنری باشد.")
    if 'disk' not in disk_info:
        raise ValueError("دیکشنری ورودی باید شامل کلید 'disk' باشد.")

    Disks.objects.update_or_create(
        disk_name=disk_info['disk'],  # ✅ اصلاح شد: 'disk' نه 'disks'
        defaults={
            'model': disk_info.get('model', ''),
            'vendor': disk_info.get('vendor', ''),
            'state': disk_info.get('state', ''),
            'device_path': disk_info.get('device_path', ''),
            'physical_block_size': disk_info.get('physical_block_size', ''),
            'logical_block_size': disk_info.get('logical_block_size', ''),
            'scheduler': disk_info.get('scheduler', ''),
            'wwid': disk_info.get('wwid', ''),
            'total_bytes': disk_info.get('total_bytes'),
            'temperature_celsius': disk_info.get('temperature_celsius'),
            'wwn': disk_info.get('wwn', ''),
            'uuid': disk_info.get('uuid'),
            'slot_number': disk_info.get('slot_number'),
            'disk_type': disk_info.get('type', ''),
            'has_partition': disk_info.get('has_partition', False),
            'used_bytes': disk_info.get('used_bytes'),
            'free_bytes': disk_info.get('free_bytes'),
            'usage_percent': disk_info.get('usage_percent'),
            'partitions_data': disk_info.get('partitions', []),
        }
    )

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


# ------------------------ APIهای عمومی ------------------------


class DiskNameListView(APIView):
    """دریافت لیست نام تمام دیسک‌های فیزیکی (مثل ['sda', 'nvme0n1'])."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)
        try:
            obj_disk = DiskManager()
            return StandardResponse(
                data={"disk_names": obj_disk.disks},
                message="لیست نام دیسک‌ها با موفقیت دریافت شد.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Error in DiskNameListView: {str(e)}")
            return StandardErrorResponse(
                error_code="disk_names_error",
                error_message="خطا در دریافت لیست نام دیسک‌ها.",
                exception=e,
                request_data=request_data,
                save_to_db=save_to_db
            )


class DiskCountView(APIView):
    """دریافت تعداد دیسک‌های فیزیکی سیستم."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)
        try:
            obj_disk = DiskManager()
            count = len(obj_disk.disks)
            return StandardResponse(
                data={"disk_count": count},
                message="تعداد دیسک‌ها با موفقیت شمارش شد.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Error in DiskCountView: {str(e)}")
            return StandardErrorResponse(
                error_code="disk_count_error",
                error_message="خطا در شمارش دیسک‌ها.",
                exception=e,
                request_data=request_data,
                save_to_db=save_to_db
            )


class OSdiskView(APIView):
    """دریافت نام دیسکی که سیستم‌عامل روی آن نصب شده است."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)
        try:
            obj_disk = DiskManager()
            os_disk = obj_disk.os_disk
            return StandardResponse(
                data={"os_disk": os_disk},
                message="دیسک سیستم‌عامل با موفقیت شناسایی شد." if os_disk else "دیسک سیستم‌عامل یافت نشد.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Error in OSdiskView: {str(e)}")
            return StandardErrorResponse(
                error_code="os_disk_error",
                error_message="خطا در شناسایی دیسک سیستم‌عامل.",
                exception=e,
                request_data=request_data,
                save_to_db=save_to_db
            )


class DiskView(DiskValidationMixin, APIView):
    """دریافت لیست تمام دیسک‌ها (اگر disk_name داده نشود) یا جزئیات یک دیسک خاص."""
    permission_classes = [IsAuthenticated]

    def get(self, request, disk_name=None):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)

        if disk_name is None:
            try:
                obj_disk = DiskManager()
                disks_info = obj_disk.get_disks_info_all()

                if save_to_db:
                    db_update_disks(disks_info)

                return StandardResponse(
                    data=disks_info,
                    message="لیست دیسک‌ها با موفقیت دریافت شد.",
                    request_data=request_data,
                    save_to_db=save_to_db
                )
            except Exception as e:
                logger.error(f"Error in DiskView (list): {str(e)}")
                return StandardErrorResponse(
                    error_code="disk_list_error",
                    error_message="خطا در دریافت لیست دیسک‌ها.",
                    exception=e,
                    request_data=request_data,
                    save_to_db=save_to_db
                )

        obj_disk = self.validate_disk_and_get_manager(disk_name, save_to_db, request_data)
        if isinstance(obj_disk, StandardErrorResponse):
            return obj_disk

        disk_info = obj_disk.get_disk_info(disk_name)

        if save_to_db:
            db_update_disk_single(disk_info)

        return StandardResponse(
            data=disk_info,
            message=f"جزئیات دیسک '{disk_name}' با موفقیت دریافت شد.",
            request_data=request_data,
            save_to_db=save_to_db
        )


# ------------------------ APIهای مربوط به یک دیسک خاص ------------------------


class DiskPartitionCountView(DiskValidationMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, disk_name):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)
        obj_disk = self.validate_disk_and_get_manager(disk_name, save_to_db, request_data)
        if isinstance(obj_disk, StandardErrorResponse):
            return obj_disk
        count = obj_disk.get_partition_count(disk_name)
        return StandardResponse(
            data={"disk": disk_name, "partition_count": count},
            message=f"تعداد پارتیشن‌های دیسک '{disk_name}' با موفقیت دریافت شد.",
            request_data=request_data,
            save_to_db=save_to_db
        )


class DiskPartitionNamesView(DiskValidationMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, disk_name):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)
        obj_disk = self.validate_disk_and_get_manager(disk_name, save_to_db, request_data)
        if isinstance(obj_disk, StandardErrorResponse):
            return obj_disk
        names = obj_disk.get_partition_names(disk_name)
        return StandardResponse(
            data={"disk": disk_name, "partition_names": names},
            message=f"لیست پارتیشن‌های دیسک '{disk_name}' با موفقیت دریافت شد.",
            request_data=request_data,
            save_to_db=save_to_db
        )


class DiskTypeView(DiskValidationMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, disk_name):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)
        obj_disk = self.validate_disk_and_get_manager(disk_name, save_to_db, request_data)
        if isinstance(obj_disk, StandardErrorResponse):
            return obj_disk
        disk_type = obj_disk.get_disk_type(disk_name)
        return StandardResponse(
            data={"disk": disk_name, "type": disk_type},
            message=f"نوع دیسک '{disk_name}' با موفقیت دریافت شد.",
            request_data=request_data,
            save_to_db=save_to_db
        )


class DiskTemperatureView(DiskValidationMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, disk_name):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)
        obj_disk = self.validate_disk_and_get_manager(disk_name, save_to_db, request_data)
        if isinstance(obj_disk, StandardErrorResponse):
            return obj_disk
        temp = obj_disk.get_temperature(disk_name)
        return StandardResponse(
            data={"disk": disk_name, "temperature_celsius": temp},
            message=f"دمای دیسک '{disk_name}' با موفقیت دریافت شد." if temp is not None else f"دمای دیسک '{disk_name}' در دسترس نیست.",
            request_data=request_data,
            save_to_db=save_to_db
        )


class DiskHasOSView(DiskValidationMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, disk_name):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)
        obj_disk = self.validate_disk_and_get_manager(disk_name, save_to_db, request_data)
        if isinstance(obj_disk, StandardErrorResponse):
            return obj_disk
        has_os = obj_disk.has_os_on_disk(disk_name)
        return StandardResponse(
            data={"disk": disk_name, "has_os": has_os},
            message=f"دیسک '{disk_name}' {'سیستم‌عامل دارد.' if has_os else 'سیستم‌عامل ندارد.'}",
            request_data=request_data,
            save_to_db=save_to_db
        )


class DiskHasPartitionsView(DiskValidationMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, disk_name):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)
        obj_disk = self.validate_disk_and_get_manager(disk_name, save_to_db, request_data)
        if isinstance(obj_disk, StandardErrorResponse):
            return obj_disk
        has_partitions = obj_disk.has_partitions(disk_name)
        return StandardResponse(
            data={"disk": disk_name, "has_partitions": has_partitions},
            message=f"دیسک '{disk_name}' {'دارای پارتیشن است.' if has_partitions else 'فاقد پارتیشن است.'}",
            request_data=request_data,
            save_to_db=save_to_db
        )


class DiskTotalSizeView(DiskValidationMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, disk_name):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)
        obj_disk = self.validate_disk_and_get_manager(disk_name, save_to_db, request_data)
        if isinstance(obj_disk, StandardErrorResponse):
            return obj_disk
        total_size = obj_disk.get_total_size(disk_name)
        return StandardResponse(
            data={"disk": disk_name, "total_bytes": total_size},
            message=f"حجم کل دیسک '{disk_name}' با موفقیت دریافت شد." if total_size is not None else f"حجم دیسک '{disk_name}' در دسترس نیست.",
            request_data=request_data,
            save_to_db=save_to_db
        )


# ------------------------ APIهای مربوط به پارتیشن ------------------------


class PartitionIsMountedView(APIView):
    """بررسی اینکه آیا یک پارتیشن خاص mount شده است."""
    permission_classes = [IsAuthenticated]

    def get(self, request, partition_name):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)
        if not partition_name or not isinstance(partition_name, str):
            return StandardErrorResponse(
                error_code="invalid_partition_name",
                error_message="نام پارتیشن معتبر نیست.",
                request_data=request_data,
                status=400,
                save_to_db=save_to_db
            )
        try:
            obj_disk = DiskManager()
            mount_info = obj_disk.get_partition_mount_info(partition_name)
            is_mounted = mount_info is not None
            return StandardResponse(
                data={
                    "partition": partition_name,
                    "is_mounted": is_mounted,
                    "mount_info": mount_info
                },
                message=f"پارتیشن '{partition_name}' {'mount شده است.' if is_mounted else 'mount نشده است.'}",
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Error in PartitionIsMountedView for {partition_name}: {str(e)}")
            return StandardErrorResponse(
                error_code="partition_mount_check_error",
                error_message=f"خطا در بررسی mount بودن پارتیشن '{partition_name}'.",
                exception=e,
                request_data=request_data,
                save_to_db=save_to_db
            )


class PartitionTotalSizeView(APIView):
    """دریافت حجم کل یک پارتیشن به بایت."""
    permission_classes = [IsAuthenticated]

    def get(self, request, partition_name):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.query_params)
        if not partition_name or not isinstance(partition_name, str):
            return StandardErrorResponse(
                error_code="invalid_partition_name",
                error_message="نام پارتیشن معتبر نیست.",
                request_data=request_data,
                status=400,
                save_to_db=save_to_db
            )
        try:
            obj_disk = DiskManager()
            total_size = obj_disk.get_total_size(partition_name)
            return StandardResponse(
                data={"partition": partition_name, "total_bytes": total_size},
                message=f"حجم کل پارتیشن '{partition_name}' با موفقیت دریافت شد." if total_size is not None else f"حجم پارتیشن '{partition_name}' در دسترس نیست.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Error in PartitionTotalSizeView for {partition_name}: {str(e)}")
            return StandardErrorResponse(
                error_code="partition_total_size_error",
                error_message=f"خطا در دریافت حجم کل پارتیشن '{partition_name}'.",
                exception=e,
                request_data=request_data,
                save_to_db=save_to_db
            )


# ------------------------ APIهای عملیاتی (POST) ------------------------


class DiskWipeSignaturesView(DiskValidationMixin, OSDiskProtectionMixin, APIView):
    """پاک‌کردن سیگنچرهای دیسک."""
    permission_classes = [IsAuthenticated]

    def post(self, request, disk_name):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = request.data

        obj_disk = self.validate_disk_and_get_manager(disk_name, save_to_db, request_data)
        if isinstance(obj_disk, StandardErrorResponse):
            return obj_disk

        os_error = self.check_os_disk_protection(obj_disk, disk_name, save_to_db, request_data)
        if os_error is not None:
            return os_error

        device_path = f"/dev/{disk_name}"
        success = obj_disk.disk_wipe_signatures(device_path)
        if success:
            return StandardResponse(
                data={"disk": disk_name, "device_path": device_path},
                message=f"تمام سیگنچرهای دیسک '{disk_name}' با موفقیت پاک شد.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        else:
            return StandardErrorResponse(
                error_code="wipe_failed",
                error_message=f"پاک‌کردن سیگنچرهای دیسک '{disk_name}' شکست خورد.",
                request_data=request_data,
                status=500,
                save_to_db=save_to_db
            )


class DiskClearZFSLabelView(DiskValidationMixin, OSDiskProtectionMixin, APIView):
    """پاک‌کردن لیبل ZFS دیسک."""
    permission_classes = [IsAuthenticated]

    def post(self, request, disk_name):
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = request.data

        obj_disk = self.validate_disk_and_get_manager(disk_name, save_to_db, request_data)
        if isinstance(obj_disk, StandardErrorResponse):
            return obj_disk

        os_error = self.check_os_disk_protection(obj_disk, disk_name, save_to_db, request_data)
        if os_error is not None:
            return os_error

        device_path = f"/dev/{disk_name}"
        success = obj_disk.disk_clear_zfs_label(device_path)
        if success:
            return StandardResponse(
                data={"disk": disk_name, "device_path": device_path},
                message=f"لیبل ZFS دیسک '{disk_name}' با موفقیت پاک شد.",
                request_data=request_data,
                save_to_db=save_to_db
            )
        else:
            return StandardErrorResponse(
                error_code="zfs_clear_failed",
                error_message=f"پاک‌کردن لیبل ZFS دیسک '{disk_name}' شکست خورد.",
                request_data=request_data,
                status=500,
                save_to_db=save_to_db
            )
