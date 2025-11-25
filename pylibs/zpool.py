# soho_core_api/pylibs/zpool.py

import subprocess
import logging
import os
import glob
import re
from typing import Dict, Any, List, Optional, Tuple
import libzfs

from pylibs import run_cli_command
from pylibs.disk import DiskManager

logger = logging.getLogger(__name__)


class ZpoolManager:
    """
    تمام متدهای تغییر‌دهنده (مثل create, destroy) در صورت شکست، Exception پرتاب می‌کنند.
    متدهای خواندنی (مثل list_all_pools) داده خام یا None برمی‌گردانند.
    تمام مسیرهای دستگاه باید از نوع `/dev/disk/by-id/...` باشند.
    """

    obj_disk = DiskManager()

    def __init__(self) -> None:
        """سازنده کلاس — ایجاد نمونه ZFS از libzfs."""
        self.zfs = libzfs.ZFS()

    def list_all_pools(self) -> List[Dict[str, Any]]:
        """
        دریافت لیست خلاصه تمام ZFS Poolهای موجود در سیستم.

        Returns:
            List[Dict[str, Any]]: لیستی از دیکشنری‌ها با فیلدهای زیر:
                - name (str): نام pool
                - health (str): وضعیت سلامت
                - size (str): حجم کل
                - allocated (str): حجم استفاده‌شده
                - free (str): فضای آزاد
                - capacity (str): درصد پر شدن
                - guid (str): شناسه منحصربه‌فرد
        """
        pools = []
        try:
            for p in self.zfs.pools:
                props = p.properties
                pools.append({
                    "name": str(props["name"].value),
                    "health": str(props["health"].value),
                    "size": str(props["size"].value),
                    "allocated": str(props["allocated"].value),
                    "free": str(props["free"].value),
                    "capacity": str(props["capacity"].value),
                    "guid": str(props["guid"].value),
                    "disks": self.get_pool_devices(props["name"].value)
                })
        except Exception as e:
            logger.warning(f"Error reading ZFS pools in list_all_pools: {e}")
        return pools

    def get_pool_detail(self, pool_name: str) -> Optional[Dict[str, Any]]:
        """
        دریافت تمام ویژگی‌های یک ZFS Pool خاص.

        Args:
            pool_name (str): نام pool مورد نظر.

        Returns:
            Optional[Dict[str, Any]]: دیکشنری کامل ویژگی‌ها یا None اگر pool یافت نشود.
        """
        for p in self.zfs.pools:
            if str(p.properties["name"].value) == pool_name:
                props = p.properties
                return {k: str(v.value) for k, v in props.items()}
        return None

    def pool_exists(self, pool_name: str) -> bool:
        """
        بررسی وجود یک ZFS Pool با نام داده‌شده.

        Args:
            pool_name (str): نام pool برای جستجو.

        Returns:
            bool: True اگر pool وجود داشته باشد، در غیر این صورت False.
        """
        return any(str(p.properties["name"].value) == pool_name for p in self.zfs.pools)

    def get_pool_devices(self, pool_name: str) -> List[Dict[str, Any]]:
        """
        دریافت لیست تمام دیسک‌های فیزیکی یک ZFS Pool با وضعیت و WWN.

        Args:
            pool_name (str): نام pool مورد نظر.

        Returns:
            List[Dict[str, Any]]: لیست دیسک‌ها با جزئیات.
        """
        for p in self.zfs.pools:
            if str(p.properties["name"].value) == pool_name:
                devices = []

                def traverse_vdevs(vdev, parent_type: str = "root"):
                    if vdev.type in ("disk", "file"):
                        path_clean = re.sub(r'\d+$', '', vdev.path)
                        wwn = self.obj_disk.get_wwn_by_entry(vdev.path.replace("/dev/", ""))
                        path_name = self.obj_disk.get_disk_name_by_wwn(wwn)
                        disk_name = self.obj_disk.get_disk_name_from_partition(path_name)
                        devices.append({
                            "full_path_wwn": vdev.path,
                            "full_disk_wwn": vdev.path.replace("-part1", ""),
                            "wwn": wwn,
                            "full_path_name": f"/dev/{path_name}",
                            "full_disk_name": f"/dev/{disk_name}",
                            "disk_name": disk_name,
                            "status": getattr(vdev, 'status', 'UNKNOWN'),
                            "type": vdev.type,
                        })
                    elif hasattr(vdev, 'children') and vdev.children:
                        for child in vdev.children:
                            traverse_vdevs(child, parent_type=vdev.type)

                traverse_vdevs(p.root_vdev)
                return devices
        return []

    def create_pool(self, pool_name: str, devices: List[str], vdev_type: str = "disk") -> Tuple[str, str]:
        """
        ایجاد یک ZFS Pool جدید با استفاده از مسیرهای WWN/NVMe.

        Args:
            pool_name (str): نام pool جدید.
            devices (List[str]): لیست مسیرهای کامل (مثل ["/dev/disk/by-id/wwn-0x5000c500e8272848", ...])
            vdev_type (str): نوع vdev (disk, mirror, raidz, ...)

        Raises:
            CLICommandError
        """
        if not pool_name or not devices or not isinstance(devices, list):
            raise ValueError("پارامترهای pool_name و devices الزامی و معتبر هستند.")

        if vdev_type == "disk":
            cmd = ["/usr/bin/zpool", "create", "-f", pool_name] + devices
        else:
            cmd = ["/usr/bin/zpool", "create", "-f", pool_name, vdev_type] + devices

        std_out, std_error = run_cli_command(cmd, use_sudo=True)
        return std_out, std_error

    def destroy_pool(self, pool_name: str) -> Tuple[str, str]:
        """
        حذف یک ZFS Pool موجود.

        ⚠️ این عملیات غیرقابل بازگشت است.

        Args:
            pool_name (str): نام pool برای حذف.

        Raises:
            CLICommandError
        """
        cmd = ["/usr/bin/zpool", "destroy", "-f", pool_name]
        std_out, std_error = run_cli_command(cmd, use_sudo=True)
        return std_out, std_error

    def replace_device(self, pool_name: str, old_device: str, new_device: str) -> Tuple[str, str]:
        """
        جایگزینی یک دیسک خراب با یک دیسک سالم.

        Args:
            pool_name (str): نام pool مورد نظر.
            old_device (str): مسیر کامل دستگاه خراب (مثل /dev/disk/by-id/wwn-...)
            new_device (str): مسیر کامل دستگاه جدید

        Raises:
            CLICommandError
        """
        cmd = ["/usr/bin/zpool", "replace", "-f", pool_name, old_device, new_device]
        std_out, std_error = run_cli_command(cmd, use_sudo=True)
        return std_out, std_error

    def add_vdev(self, pool_name: str, devices: List[str], vdev_type: str = "disk") -> Tuple[str, str]:
        """
        افزودن یک vdev جدید به یک pool موجود.

        Args:
            pool_name (str): نام pool مورد نظر.
            devices (List[str]): لیست مسیرهای کامل دستگاه‌ها
            vdev_type (str): نوع vdev (disk, mirror, raidz, spare, ...)

        Raises:
            CLICommandError
        """
        if vdev_type == "spare":
            cmd = ["/usr/bin/sudo", "/usr/bin/zpool", "add", "-f", pool_name, "spare"] + devices
        elif vdev_type == "disk":
            cmd = ["/usr/bin/sudo", "/usr/bin/zpool", "add", "-f", pool_name] + devices
        else:
            cmd = ["/usr/bin/sudo", "/usr/bin/zpool", "add", "-f", pool_name, vdev_type] + devices

        std_out, std_error = run_cli_command(cmd, use_sudo=True)
        return std_out, std_error

    def set_property(self, pool_name: str, prop: str, value: str) -> Tuple[str, str]:
        """
        تنظیم یک ویژگی ZFS Pool.

        Args:
            pool_name (str): نام pool مورد نظر.
            prop (str): نام ویژگی (مثل "autoreplace")
            value (str): مقدار جدید (مثل "on")

        Raises:
            CLICommandError
        """
        cmd = ["/usr/bin/sudo", "/usr/bin/zpool", "set", f"{prop}={value}", pool_name]
        std_out, std_error = run_cli_command(cmd, use_sudo=True)
        return std_out, std_error
