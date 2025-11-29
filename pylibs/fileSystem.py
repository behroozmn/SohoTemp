from __future__ import annotations
import libzfs
from typing import Dict, Any, List, Optional, Union
from pylibs import logger, CLICommandError, run_cli_command


class FilesystemManager:
    """
    مدیریت فایل‌سیستم‌های ZFS.
    تمام توابع فقط داده خام یا استثنا برمی‌گردانند.
    """

    def __init__(self) -> None:
        self.zfs = libzfs.ZFS()

    def get_filesystem_detail(self, fs_name: str) -> Optional[Dict[str, Any]]:
        """
        دریافت جزئیات یک فایل‌سیستم ZFS با نام کامل (pool/fs).
        شامل تمام پراپرتی‌های مرتبط با حجم، فضا و وضعیت.
        """
        try:
            dataset = self.zfs.get_dataset(fs_name)
            props = dataset.properties
            return {k: str(v.value) for k, v in props.items()}
        except libzfs.ZFSException as e:
            logger.debug(f"فایل‌سیستم یافت نشد: {fs_name} - {e}")
            return None

    def list_filesystems_names(self, contain_poolname: bool) -> List[str]:
        """
        لیستی از نام‌های دیتاست‌های ZFS را برمی‌گرداند.

        اگر ``contain_poolname`` برابر True باشد، همهٔ دیتاست‌ها (شامل روت پول‌ها) برگردانده می‌شوند.
        اگر False باشد، تنها فایل‌سیستم‌های فرزند (دیتاست‌هایی که در نامشان '/' وجود دارد) برگردانده می‌شوند.

        پارامترها:
            contain_poolname (bool): تعیین می‌کند که آیا دیتاست‌های سطح پول (بدون '/') نیز در لیست گنجانده شوند یا خیر.

        بازگشت:
            List[str]: لیستی از نام دیتاست‌ها به صورت رشته.
        """
        # datasets = self.zfs.datasets
        # if contain_poolname: return [str(ds.name) for ds in datasets]
        # else: return [str(ds.name) for ds in datasets if "/" in str(ds.name)]

        return [str(ds.name) for ds in self.zfs.datasets if contain_poolname or "/" in str(ds.name)]

    def get_filesystems_all_detail(self, contain_poolname: bool = False) -> List[Dict[str, Any]]:
        """دریافت جزئیات تمام فایل‌سیستم‌ها."""
        all_details = []
        for name in self.list_filesystems_names(contain_poolname=contain_poolname):
            detail = self.get_filesystem_detail(name)
            if detail is not None:
                all_details.append(detail)
        return all_details

    def create_filesystem(self, pool_name: str, fs_name: str, quota: Optional[str] = None, reservation: Optional[str] = None, mountpoint: Optional[str] = None, ) -> None:
        """
        ساخت یک فایل‌سیستم ZFS جدید.
        """
        full_name = f"{pool_name}/{fs_name}"
        cmd = ["/usr/sbin/zfs", "create"]
        if quota:
            cmd.extend(["-o", f"quota={quota}"])
        if reservation:
            cmd.extend(["-o", f"reservation={reservation}"])
        if mountpoint:
            cmd.extend(["-o", f"mountpoint={mountpoint}"])
        cmd.append(full_name)

        try:
            run_cli_command(cmd, use_sudo=True)
        except CLICommandError as e:
            raise e

    def destroy_filesystem(self, fs_name: str) -> None:
        """حذف یک فایل‌سیستم ZFS."""
        cmd = ["/usr/sbin/zfs", "destroy", "-r", fs_name]
        try:
            run_cli_command(cmd, use_sudo=True)
        except CLICommandError as e:
            raise e

    def get_filesystem_property(self, fs_name: str, prop_key: str) -> Optional[str]:
        """دریافت مقدار یک پراپرتی خاص از فایل‌سیستم."""
        detail = self.get_filesystem_detail(fs_name)
        if detail and prop_key in detail:
            return detail[prop_key]
        return None
