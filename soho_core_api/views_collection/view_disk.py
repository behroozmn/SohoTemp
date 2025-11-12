# soho_core_api/views_collection/view_disk.py

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from pylibs import StandardResponse, StandardErrorResponse
from pylibs.disk import DiskManager
import logging

logger = logging.getLogger(__name__)


def _str_to_bool(value) -> bool:
    """فقط در صورتی True برمی‌گرداند که مقدار دقیقاً 'true' باشد (بدون حساسیت به کوچک/بزرگی)."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return False


def _get_save_to_db_flag(request) -> bool:
    """
    استخراج و تبدیل مقدار save_to_db از بدنه یا query_params.
    این تابع به‌صورت خودکار تشخیص می‌دهد که درخواست GET است یا POST
    و مقدار را از محل مناسب می‌خواند.
    """
    try:
        if hasattr(request, "method"):
            if request.method.upper() == "GET":
                raw_value = request.query_params.get("save_to_db", False)
            else:
                raw_value = request.data.get("save_to_db", request.query_params.get("save_to_db", False))
        elif isinstance(request, dict):
            raw_value = request.get("save_to_db", False)
        else:
            raw_value = False
    except Exception as e:
        logger.warning(f"Error parsing save_to_db flag: {e}")
        raw_value = False
    return _str_to_bool(raw_value)


def _validate_disk_name(disk_name: str) -> tuple[bool, str | None]:
    """
    اعتبارسنجی نام دیسک.یعنی بررسی می‌کند که: ۱-آیا نام دیسک وجود دارد(خالی یا نان نباشد) ۲-رشته باشد
    چرا نیاز است؟ برای جلوگیری از خطا در مراحل بعدی وقتی ورودی کاربر مخرب یا نامعتبر باشد.

    Args:
        disk_name (str): نام دیسک برای بررسی.

    Returns: tuple[bool, str | None]:
        Validate: (True, None)
        Invalidate: (False, "نام دیسک معتبر نیست.")
    """
    if not disk_name or not isinstance(disk_name, str):
        return False, "نام دیسک معتبر نیست."
    return True, None


def _get_disk_manager_and_validate(disk_name: str) -> tuple[DiskManager | None, str | None]:
    """
    ایجاد DiskManager و اعتبارسنجی وجود دیسک.

    Args:
        disk_name (str): نام دیسک.

    Returns: tuple[DiskManager | None, str | None]
        Validate: (<DiskManager object>, None)
        Invalidate: (None, "متن خطا")
    """
    is_valid, error_msg = _validate_disk_name(disk_name)
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


# ------------------------ APIهای عمومی ------------------------


class DiskListView(APIView):
    """دریافت لیست تمام دیسک‌های سیستم با جزئیات کامل."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        save_to_db = _get_save_to_db_flag(request)
        try:
            obj_disk = DiskManager()
            disks_info = obj_disk.get_disks_info_all()
            return StandardResponse(
                data=disks_info,
                message="لیست دیسک‌ها با موفقیت دریافت شد.",
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Error in DiskListView: {str(e)}")
            return StandardErrorResponse(
                error_code="disk_list_error",
                error_message="خطا در دریافت لیست دیسک‌ها.",
                exception=e,
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )


class DiskNameListView(APIView):
    """دریافت لیست نام تمام دیسک‌های فیزیکی (مثل ['sda', 'nvme0n1'])."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        save_to_db = _get_save_to_db_flag(request)
        try:
            obj_disk = DiskManager()
            disk_names = obj_disk.disks
            return StandardResponse(
                data={"disk_names": disk_names},
                message="لیست نام دیسک‌ها با موفقیت دریافت شد.",
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Error in DiskNameListView: {str(e)}")
            return StandardErrorResponse(
                error_code="disk_names_error",
                error_message="خطا در دریافت لیست نام دیسک‌ها.",
                exception=e,
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )


class DiskCountView(APIView):
    """دریافت تعداد دیسک‌های فیزیکی سیستم."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        save_to_db = _get_save_to_db_flag(request)
        try:
            obj_disk = DiskManager()
            count = len(obj_disk.disks)
            return StandardResponse(
                data={"disk_count": count},
                message="تعداد دیسک‌ها با موفقیت شمارش شد.",
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Error in DiskCountView: {str(e)}")
            return StandardErrorResponse(
                error_code="disk_count_error",
                error_message="خطا در شمارش دیسک‌ها.",
                exception=e,
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )


class OSdiskView(APIView):
    """دریافت نام دیسکی که سیستم‌عامل روی آن نصب شده است."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        save_to_db = _get_save_to_db_flag(request)
        try:
            obj_disk = DiskManager()
            os_disk = obj_disk.os_disk
            return StandardResponse(
                data={"os_disk": os_disk},
                message="دیسک سیستم‌عامل با موفقیت شناسایی شد." if os_disk else "دیسک سیستم‌عامل یافت نشد.",
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Error in OSdiskView: {str(e)}")
            return StandardErrorResponse(
                error_code="os_disk_error",
                error_message="خطا در شناسایی دیسک سیستم‌عامل.",
                exception=e,
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )


# ------------------------ APIهای مربوط به دیسک خاص ------------------------


class DiskDetailView(APIView):
    """دریافت جزئیات یک دیسک خاص بر اساس نام آن."""
    permission_classes = [IsAuthenticated]

    def get(self, request, disk_name):
        save_to_db = _get_save_to_db_flag(request)
        try:
            obj_disk, error_msg = _get_disk_manager_and_validate(disk_name)
            if obj_disk is None:
                status_code = 404 if "یافت نشد" in (error_msg or "") else 400
                return StandardErrorResponse(
                    error_code="disk_not_found" if "یافت نشد" in (error_msg or "") else "invalid_disk_name",
                    error_message=error_msg or "خطا در اعتبارسنجی دیسک.",
                    request_data=dict(request.query_params),
                    status=status_code,
                    save_to_db=save_to_db
                )
            disk_info = obj_disk.get_disk_info(disk_name)
            return StandardResponse(
                data=disk_info,
                message=f"جزئیات دیسک '{disk_name}' با موفقیت دریافت شد.",
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Error in DiskDetailView for {disk_name}: {str(e)}")
            return StandardErrorResponse(
                error_code="disk_detail_error",
                error_message=f"خطا در دریافت جزئیات دیسک '{disk_name}'.",
                exception=e,
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )


class DiskPartitionCountView(APIView):
    """دریافت تعداد پارتیشن‌های یک دیسک بر اساس نام آن."""
    permission_classes = [IsAuthenticated]

    def get(self, request, disk_name):
        save_to_db = _get_save_to_db_flag(request)
        try:
            obj_disk, error_msg = _get_disk_manager_and_validate(disk_name)
            if obj_disk is None:
                status_code = 404 if "یافت نشد" in (error_msg or "") else 400
                return StandardErrorResponse(
                    error_code="disk_not_found" if "یافت نشد" in (error_msg or "") else "invalid_disk_name",
                    error_message=error_msg or "خطا در اعتبارسنجی دیسک.",
                    request_data=dict(request.query_params),
                    status=status_code,
                    save_to_db=save_to_db
                )
            count = obj_disk.get_partition_count(disk_name)
            return StandardResponse(
                data={"disk": disk_name, "partition_count": count},
                message=f"تعداد پارتیشن‌های دیسک '{disk_name}' با موفقیت دریافت شد.",
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Error in DiskPartitionCountView for {disk_name}: {str(e)}")
            return StandardErrorResponse(
                error_code="partition_count_error",
                error_message=f"خطا در دریافت تعداد پارتیشن‌های دیسک '{disk_name}'.",
                exception=e,
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )


class DiskPartitionNamesView(APIView):
    """دریافت لیست نام پارتیشن‌های یک دیسک بر اساس نام آن."""
    permission_classes = [IsAuthenticated]

    def get(self, request, disk_name):
        save_to_db = _get_save_to_db_flag(request)
        try:
            obj_disk, error_msg = _get_disk_manager_and_validate(disk_name)
            if obj_disk is None:
                status_code = 404 if "یافت نشد" in (error_msg or "") else 400
                return StandardErrorResponse(
                    error_code="disk_not_found" if "یافت نشد" in (error_msg or "") else "invalid_disk_name",
                    error_message=error_msg or "خطا در اعتبارسنجی دیسک.",
                    request_data=dict(request.query_params),
                    status=status_code,
                    save_to_db=save_to_db
                )
            names = obj_disk.get_partition_names(disk_name)
            return StandardResponse(
                data={"disk": disk_name, "partition_names": names},
                message=f"لیست پارتیشن‌های دیسک '{disk_name}' با موفقیت دریافت شد.",
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Error in DiskPartitionNamesView for {disk_name}: {str(e)}")
            return StandardErrorResponse(
                error_code="partition_names_error",
                error_message=f"خطا در دریافت لیست پارتیشن‌های دیسک '{disk_name}'.",
                exception=e,
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )


class DiskTypeView(APIView):
    """دریافت نوع دیسک (NVMe, SATA, SCSI, USB, ...)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, disk_name):
        save_to_db = _get_save_to_db_flag(request)
        try:
            obj_disk, error_msg = _get_disk_manager_and_validate(disk_name)
            if obj_disk is None:
                status_code = 404 if "یافت نشد" in (error_msg or "") else 400
                return StandardErrorResponse(
                    error_code="disk_not_found" if "یافت نشد" in (error_msg or "") else "invalid_disk_name",
                    error_message=error_msg or "خطا در اعتبارسنجی دیسک.",
                    request_data=dict(request.query_params),
                    status=status_code,
                    save_to_db=save_to_db
                )
            disk_type = obj_disk.get_disk_type(disk_name)
            return StandardResponse(
                data={"disk": disk_name, "type": disk_type},
                message=f"نوع دیسک '{disk_name}' با موفقیت دریافت شد.",
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Error in DiskTypeView for {disk_name}: {str(e)}")
            return StandardErrorResponse(
                error_code="disk_type_error",
                error_message=f"خطا در دریافت نوع دیسک '{disk_name}'.",
                exception=e,
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )


class DiskTemperatureView(APIView):
    """دریافت دمای دیسک (در صورت پشتیبانی)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, disk_name):
        save_to_db = _get_save_to_db_flag(request)
        try:
            obj_disk, error_msg = _get_disk_manager_and_validate(disk_name)
            if obj_disk is None:
                status_code = 404 if "یافت نشد" in (error_msg or "") else 400
                return StandardErrorResponse(
                    error_code="disk_not_found" if "یافت نشد" in (error_msg or "") else "invalid_disk_name",
                    error_message=error_msg or "خطا در اعتبارسنجی دیسک.",
                    request_data=dict(request.query_params),
                    status=status_code,
                    save_to_db=save_to_db
                )
            temp = obj_disk.get_temperature(disk_name)
            return StandardResponse(
                data={"disk": disk_name, "temperature_celsius": temp},
                message=f"دمای دیسک '{disk_name}' با موفقیت دریافت شد." if temp is not None else f"دمای دیسک '{disk_name}' در دسترس نیست.",
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Error in DiskTemperatureView for {disk_name}: {str(e)}")
            return StandardErrorResponse(
                error_code="disk_temperature_error",
                error_message=f"خطا در دریافت دمای دیسک '{disk_name}'.",
                exception=e,
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )


class DiskHasOSView(APIView):
    """بررسی اینکه آیا سیستم‌عامل روی دیسک نصب شده است."""
    permission_classes = [IsAuthenticated]

    def get(self, request, disk_name):
        save_to_db = _get_save_to_db_flag(request)
        try:
            obj_disk, error_msg = _get_disk_manager_and_validate(disk_name)
            if obj_disk is None:
                status_code = 404 if "یافت نشد" in (error_msg or "") else 400
                return StandardErrorResponse(
                    error_code="disk_not_found" if "یافت نشد" in (error_msg or "") else "invalid_disk_name",
                    error_message=error_msg or "خطا در اعتبارسنجی دیسک.",
                    request_data=dict(request.query_params),
                    status=status_code,
                    save_to_db=save_to_db
                )
            has_os = obj_disk.has_os_on_disk(disk_name)
            return StandardResponse(
                data={"disk": disk_name, "has_os": has_os},
                message=f"دیسک '{disk_name}' {'سیستم‌عامل دارد.' if has_os else 'سیستم‌عامل ندارد.'}",
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Error in DiskHasOSView for {disk_name}: {str(e)}")
            return StandardErrorResponse(
                error_code="disk_has_os_error",
                error_message=f"خطا در بررسی وجود سیستم‌عامل روی دیسک '{disk_name}'.",
                exception=e,
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )


class DiskHasPartitionsView(APIView):
    """بررسی اینکه آیا دیسک پارتیشن دارد."""
    permission_classes = [IsAuthenticated]

    def get(self, request, disk_name):
        save_to_db = _get_save_to_db_flag(request)
        try:
            obj_disk, error_msg = _get_disk_manager_and_validate(disk_name)
            if obj_disk is None:
                status_code = 404 if "یافت نشد" in (error_msg or "") else 400
                return StandardErrorResponse(
                    error_code="disk_not_found" if "یافت نشد" in (error_msg or "") else "invalid_disk_name",
                    error_message=error_msg or "خطا در اعتبارسنجی دیسک.",
                    request_data=dict(request.query_params),
                    status=status_code,
                    save_to_db=save_to_db
                )
            has_partitions = obj_disk.has_partitions(disk_name)
            return StandardResponse(
                data={"disk": disk_name, "has_partitions": has_partitions},
                message=f"دیسک '{disk_name}' {'دارای پارتیشن است.' if has_partitions else 'فاقد پارتیشن است.'}",
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Error in DiskHasPartitionsView for {disk_name}: {str(e)}")
            return StandardErrorResponse(
                error_code="disk_has_partitions_error",
                error_message=f"خطا در بررسی وجود پارتیشن روی دیسک '{disk_name}'.",
                exception=e,
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )


class DiskTotalSizeView(APIView):
    """دریافت حجم کل دیسک به بایت."""
    permission_classes = [IsAuthenticated]

    def get(self, request, disk_name):
        save_to_db = _get_save_to_db_flag(request)
        try:
            obj_disk, error_msg = _get_disk_manager_and_validate(disk_name)
            if obj_disk is None:
                status_code = 404 if "یافت نشد" in (error_msg or "") else 400
                return StandardErrorResponse(
                    error_code="disk_not_found" if "یافت نشد" in (error_msg or "") else "invalid_disk_name",
                    error_message=error_msg or "خطا در اعتبارسنجی دیسک.",
                    request_data=dict(request.query_params),
                    status=status_code,
                    save_to_db=save_to_db
                )
            total_size = obj_disk.get_total_size(disk_name)
            return StandardResponse(
                data={"disk": disk_name, "total_bytes": total_size},
                message=f"حجم کل دیسک '{disk_name}' با موفقیت دریافت شد." if total_size is not None else f"حجم دیسک '{disk_name}' در دسترس نیست.",
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Error in DiskTotalSizeView for {disk_name}: {str(e)}")
            return StandardErrorResponse(
                error_code="disk_total_size_error",
                error_message=f"خطا در دریافت حجم کل دیسک '{disk_name}'.",
                exception=e,
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )


# ------------------------ APIهای مربوط به پارتیشن ------------------------


class PartitionIsMountedView(APIView):
    """بررسی اینکه آیا یک پارتیشن خاص mount شده است."""
    permission_classes = [IsAuthenticated]

    def get(self, request, partition_name):
        save_to_db = _get_save_to_db_flag(request)
        if not partition_name or not isinstance(partition_name, str):
            return StandardErrorResponse(
                error_code="invalid_partition_name",
                error_message="نام پارتیشن معتبر نیست.",
                request_data=dict(request.query_params),
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
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Error in PartitionIsMountedView for {partition_name}: {str(e)}")
            return StandardErrorResponse(
                error_code="partition_mount_check_error",
                error_message=f"خطا در بررسی mount بودن پارتیشن '{partition_name}'.",
                exception=e,
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )


class PartitionTotalSizeView(APIView):
    """دریافت حجم کل یک پارتیشن به بایت."""
    permission_classes = [IsAuthenticated]

    def get(self, request, partition_name):
        save_to_db = _get_save_to_db_flag(request)
        if not partition_name or not isinstance(partition_name, str):
            return StandardErrorResponse(
                error_code="invalid_partition_name",
                error_message="نام پارتیشن معتبر نیست.",
                request_data=dict(request.query_params),
                status=400,
                save_to_db=save_to_db
            )

        try:
            obj_disk = DiskManager()
            total_size = obj_disk.get_total_size(partition_name)
            return StandardResponse(
                data={"partition": partition_name, "total_bytes": total_size},
                message=f"حجم کل پارتیشن '{partition_name}' با موفقیت دریافت شد." if total_size is not None else f"حجم پارتیشن '{partition_name}' در دسترس نیست.",
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )
        except Exception as e:
            logger.error(f"Error in PartitionTotalSizeView for {partition_name}: {str(e)}")
            return StandardErrorResponse(
                error_code="partition_total_size_error",
                error_message=f"خطا در دریافت حجم کل پارتیشن '{partition_name}'.",
                exception=e,
                request_data=dict(request.query_params),
                save_to_db=save_to_db
            )


# ------------------------ APIهای عملیاتی (POST) ------------------------


class DiskWipeSignaturesView(APIView):
    """پاک‌کردن تمام سیگنچرهای فایل‌سیستم و پارتیشن از یک دیسک."""
    permission_classes = [IsAuthenticated]

    def post(self, request, disk_name):
        save_to_db = _get_save_to_db_flag(request)
        try:
            obj_disk, error_msg = _get_disk_manager_and_validate(disk_name)
            if obj_disk is None:
                status_code = 404 if "یافت نشد" in (error_msg or "") else 400
                return StandardErrorResponse(
                    error_code="disk_not_found" if "یافت نشد" in (error_msg or "") else "invalid_disk_name",
                    error_message=error_msg or "خطا در اعتبارسنجی دیسک.",
                    request_data=request.data,
                    status=status_code,
                    save_to_db=save_to_db
                )

            if obj_disk.has_os_on_disk(disk_name):
                return StandardErrorResponse(
                    error_code="os_disk_protected",
                    error_message=f"پاک‌کردن دیسک سیستم‌عامل ({disk_name}) مجاز نیست.",
                    request_data=request.data,
                    status=403,
                    save_to_db=save_to_db
                )

            device_path = f"/dev/{disk_name}"
            success = obj_disk.disk_wipe_signatures(device_path)
            if success:
                return StandardResponse(
                    data={"disk": disk_name, "device_path": device_path},
                    message=f"تمام سیگنچرهای دیسک '{disk_name}' با موفقیت پاک شد.",
                    request_data=request.data,
                    save_to_db=save_to_db
                )
            else:
                return StandardErrorResponse(
                    error_code="wipe_failed",
                    error_message=f"پاک‌کردن سیگنچرهای دیسک '{disk_name}' شکست خورد.",
                    request_data=request.data,
                    status=500,
                    save_to_db=save_to_db
                )
        except Exception as e:
            logger.error(f"Error in DiskWipeSignaturesView for {disk_name}: {str(e)}")
            return StandardErrorResponse(
                error_code="wipe_error",
                error_message=f"خطا در پاک‌کردن سیگنچرهای دیسک '{disk_name}'.",
                exception=e,
                request_data=request.data,
                save_to_db=save_to_db
            )


class DiskClearZFSLabelView(APIView):
    """پاک‌کردن لیبل ZFS از یک دیسک."""
    permission_classes = [IsAuthenticated]

    def post(self, request, disk_name):
        save_to_db = _get_save_to_db_flag(request)
        try:
            obj_disk, error_msg = _get_disk_manager_and_validate(disk_name)
            if obj_disk is None:
                status_code = 404 if "یافت نشد" in (error_msg or "") else 400
                return StandardErrorResponse(
                    error_code="disk_not_found" if "یافت نشد" in (error_msg or "") else "invalid_disk_name",
                    error_message=error_msg or "خطا در اعتبارسنجی دیسک.",
                    request_data=request.data,
                    status=status_code,
                    save_to_db=save_to_db
                )

            if obj_disk.has_os_on_disk(disk_name):
                return StandardErrorResponse(
                    error_code="os_disk_protected",
                    error_message=f"پاک‌کردن لیبل دیسک سیستم‌عامل ({disk_name}) مجاز نیست.",
                    request_data=request.data,
                    status=403,
                    save_to_db=save_to_db
                )

            device_path = f"/dev/{disk_name}"
            success = obj_disk.disk_clear_zfs_label(device_path)
            if success:
                return StandardResponse(
                    data={"disk": disk_name, "device_path": device_path},
                    message=f"لیبل ZFS دیسک '{disk_name}' با موفقیت پاک شد.",
                    request_data=request.data,
                    save_to_db=save_to_db
                )
            else:
                return StandardErrorResponse(
                    error_code="zfs_clear_failed",
                    error_message=f"پاک‌کردن لیبل ZFS دیسک '{disk_name}' شکست خورد.",
                    request_data=request.data,
                    status=500,
                    save_to_db=save_to_db
                )
        except Exception as e:
            logger.error(f"Error in DiskClearZFSLabelView for {disk_name}: {str(e)}")
            return StandardErrorResponse(
                error_code="zfs_clear_error",
                error_message=f"خطا در پاک‌کردن لیبل ZFS دیسک '{disk_name}'.",
                exception=e,
                request_data=request.data,
                save_to_db=save_to_db
            )