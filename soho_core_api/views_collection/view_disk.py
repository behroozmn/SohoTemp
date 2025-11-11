# soho_core_api/views_collection/view_disk.py

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from pylibs import StandardResponse, StandardErrorResponse
from pylibs.disk import DiskManager
import logging

logger = logging.getLogger(__name__)


def _validate_disk_name(disk_name: str) -> tuple[bool, str | None]:
    """
    اعتبارسنجی نام دیسک.

    Args:
        disk_name (str): نام دیسک برای بررسی.

    Returns:
        tuple[bool, str | None]: (موفقیت, پیام خطا یا None)
    """
    if not disk_name or not isinstance(disk_name, str):
        return False, "نام دیسک معتبر نیست."
    return True, None


def _get_disk_manager_and_validate(disk_name: str) -> tuple[DiskManager | None, str | None]:
    """
    ایجاد DiskManager و اعتبارسنجی وجود دیسک.

    Args:
        disk_name (str): نام دیسک.

    Returns:
        tuple[DiskManager | None, str | None]: (manager یا None, پیام خطا یا None)
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


class DiskListView(APIView):
    """دریافت لیست تمام دیسک‌های سیستم با جزئیات کامل."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            obj_disk = DiskManager()
            disks_info = obj_disk.get_disks_info_all()
            return StandardResponse(
                data=disks_info,
                message="لیست دیسک‌ها با موفقیت دریافت شد.",
                request_data=dict(request.query_params),
                save_to_db=True
            )
        except Exception as e:
            logger.error(f"Error in DiskListView: {str(e)}")
            return StandardErrorResponse(
                error_code="disk_list_error",
                error_message="خطا در دریافت لیست دیسک‌ها.",
                exception=e,
                request_data=dict(request.query_params),
                save_to_db=True
            )


class DiskDetailView(APIView):
    """دریافت جزئیات یک دیسک خاص بر اساس نام آن."""
    permission_classes = [IsAuthenticated]

    def get(self, request, disk_name):
        try:
            obj_disk, error_msg = _get_disk_manager_and_validate(disk_name)
            if obj_disk is None:
                return StandardErrorResponse(
                    error_code="disk_not_found" if "یافت نشد" in (error_msg or "") else "invalid_disk_name",
                    error_message=error_msg or "خطا در اعتبارسنجی دیسک.",
                    request_data=dict(request.query_params),
                    status=404 if "یافت نشد" in (error_msg or "") else 400
                )

            disk_info = obj_disk.get_disk_info(disk_name)
            return StandardResponse(
                data=disk_info,
                message=f"جزئیات دیسک '{disk_name}' با موفقیت دریافت شد.",
                request_data=dict(request.query_params),
                save_to_db=True
            )
        except Exception as e:
            logger.error(f"Error in DiskDetailView for {disk_name}: {str(e)}")
            return StandardErrorResponse(
                error_code="disk_detail_error",
                error_message=f"خطا در دریافت جزئیات دیسک '{disk_name}'.",
                exception=e,
                request_data=dict(request.query_params),
                save_to_db=True
            )


class DiskWipeSignaturesView(APIView):
    """پاک‌کردن تمام سیگنچرهای فایل‌سیستم و پارتیشن از یک دیسک."""
    permission_classes = [IsAuthenticated]

    def post(self, request, disk_name):
        try:
            obj_disk, error_msg = _get_disk_manager_and_validate(disk_name)
            if obj_disk is None:
                status_code = 404 if "یافت نشد" in (error_msg or "") else 400
                return StandardErrorResponse(
                    error_code="disk_not_found" if "یافت نشد" in (error_msg or "") else "invalid_disk_name",
                    error_message=error_msg or "خطا در اعتبارسنجی دیسک.",
                    request_data=request.data,
                    status=status_code
                )

            if obj_disk.has_os_on_disk(disk_name):
                return StandardErrorResponse(
                    error_code="os_disk_protected",
                    error_message=f"پاک‌کردن دیسک سیستم‌عامل ({disk_name}) مجاز نیست.",
                    request_data=request.data,
                    status=403
                )

            device_path = f"/dev/{disk_name}"
            success = obj_disk.disk_wipe_signatures(device_path)
            if success:
                return StandardResponse(
                    data={"disk": disk_name, "device_path": device_path},
                    message=f"تمام سیگنچرهای دیسک '{disk_name}' با موفقیت پاک شد.",
                    request_data=request.data,
                    save_to_db=True
                )
            else:
                return StandardErrorResponse(
                    error_code="wipe_failed",
                    error_message=f"پاک‌کردن سیگنچرهای دیسک '{disk_name}' شکست خورد.",
                    request_data=request.data,
                    status=500
                )
        except Exception as e:
            logger.error(f"Error in DiskWipeSignaturesView for {disk_name}: {str(e)}")
            return StandardErrorResponse(
                error_code="wipe_error",
                error_message=f"خطا در پاک‌کردن سیگنچرهای دیسک '{disk_name}'.",
                exception=e,
                request_data=request.data,
                save_to_db=True
            )


class DiskClearZFSLabelView(APIView):
    """پاک‌کردن لیبل ZFS از یک دیسک."""
    permission_classes = [IsAuthenticated]

    def post(self, request, disk_name):
        try:
            obj_disk, error_msg = _get_disk_manager_and_validate(disk_name)
            if obj_disk is None:
                status_code = 404 if "یافت نشد" in (error_msg or "") else 400
                return StandardErrorResponse(
                    error_code="disk_not_found" if "یافت نشد" in (error_msg or "") else "invalid_disk_name",
                    error_message=error_msg or "خطا در اعتبارسنجی دیسک.",
                    request_data=request.data,
                    status=status_code
                )

            if obj_disk.has_os_on_disk(disk_name):
                return StandardErrorResponse(
                    error_code="os_disk_protected",
                    error_message=f"پاک‌کردن لیبل دیسک سیستم‌عامل ({disk_name}) مجاز نیست.",
                    request_data=request.data,
                    status=403
                )

            device_path = f"/dev/{disk_name}"
            success = obj_disk.disk_clear_zfs_label(device_path)
            if success:
                return StandardResponse(
                    data={"disk": disk_name, "device_path": device_path},
                    message=f"لیبل ZFS دیسک '{disk_name}' با موفقیت پاک شد.",
                    request_data=request.data,
                    save_to_db=True
                )
            else:
                return StandardErrorResponse(
                    error_code="zfs_clear_failed",
                    error_message=f"پاک‌کردن لیبل ZFS دیسک '{disk_name}' شکست خورد.",
                    request_data=request.data,
                    status=500
                )
        except Exception as e:
            logger.error(f"Error in DiskClearZFSLabelView for {disk_name}: {str(e)}")
            return StandardErrorResponse(
                error_code="zfs_clear_error",
                error_message=f"خطا در پاک‌کردن لیبل ZFS دیسک '{disk_name}'.",
                exception=e,
                request_data=request.data,
                save_to_db=True
            )