# soho_core_api/pylibs/zpool.py

import subprocess
import logging
import os
import glob
import re
from typing import Dict, Any, List, Optional
import libzfs

logger = logging.getLogger(__name__)


def _get_wwn_from_device_path(device_path: str) -> str:
    """
    دریافت شناسه منحصربه‌فرد (WWN یا NVMe ID) یک دستگاه بلاکی از `/dev/disk/by-id`.

    Args:
        device_path (str): مسیر دستگاه در سیستم فایل (مثال: "/dev/sda1").

    Returns:
        str: نام لینک منحصربه‌فرد (مثل "wwn-0x5002538d40000000") یا رشته خالی در صورت عدم یافتن.
    """
    by_id_path = "/dev/disk/by-id"
    if not os.path.exists(by_id_path):
        return ""
    try:
        target_real_path = os.path.realpath(device_path)
        all_links = glob.glob(os.path.join(by_id_path, "*"))
        for link in all_links:
            try:
                link_real = os.path.realpath(link)
                if link_real == target_real_path:
                    basename = os.path.basename(link)
                    if basename.startswith(("wwn-", "nvme-")):
                        return basename
            except (OSError, IOError):
                continue
    except Exception as e:
        logger.warning(f"Error in _get_wwn_from_device_path for {device_path}: {e}")
    return ""


class ZpoolManager:
    """
    تمام متدهای تغییر‌دهنده (مثل create, destroy) در صورت شکست، Exception پرتاب می‌کنند.
    متدهای خواندنی (مثل list_all_pools) داده خام یا None برمی‌گردانند.
    تمام مسیرهای دستگاه باید از نوع `/dev/disk/by-id/...` باشند.
    """

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
                        disk_name = path_clean.replace("/dev/", "")
                        wwn = _get_wwn_from_device_path(vdev.path)
                        devices.append({
                            "path": vdev.path,
                            "disk": disk_name,
                            "status": getattr(vdev, 'status', 'UNKNOWN'),
                            "type": vdev.type,
                            "parent_vdev": parent_type,
                            "wwn": wwn,
                        })
                    elif hasattr(vdev, 'children') and vdev.children:
                        for child in vdev.children:
                            traverse_vdevs(child, parent_type=vdev.type)

                traverse_vdevs(p.root_vdev)
                return devices
        return []

    def create_pool(self, pool_name: str, devices: List[str], vdev_type: str = "disk") -> None:
        """
        ایجاد یک ZFS Pool جدید با استفاده از مسیرهای WWN/NVMe.

        Args:
            pool_name (str): نام pool جدید.
            devices (List[str]): لیست مسیرهای کامل (مثل ["/dev/disk/by-id/wwn-0x5000c500e8272848", ...])
            vdev_type (str): نوع vdev (disk, mirror, raidz, ...)

        Raises:
            subprocess.CalledProcessError: در صورت شکست دستور zpool
            ValueError: در صورت ورودی‌های نامعتبر
            Exception: در صورت خطای غیرمنتظره
        """
        if not pool_name or not devices or not isinstance(devices, list):
            raise ValueError("پارامترهای pool_name و devices الزامی و معتبر هستند.")

        if vdev_type == "disk":
            cmd = ["/usr/bin/sudo", "/usr/bin/zpool", "create", "-f", pool_name] + devices
        else:
            cmd = ["/usr/bin/sudo", "/usr/bin/zpool", "create", "-f", pool_name, vdev_type] + devices

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)
        except subprocess.CalledProcessError as e:
            raise subprocess.CalledProcessError(
                e.returncode,
                e.cmd,
                f"خطا در ایجاد pool: {e.stderr.strip()}"
            )
        except Exception as e:
            raise Exception(f"خطای غیرمنتظره در ایجاد pool: {str(e)}")

    def destroy_pool(self, pool_name: str) -> None:
        """
        حذف یک ZFS Pool موجود.

        ⚠️ این عملیات غیرقابل بازگشت است.

        Args:
            pool_name (str): نام pool برای حذف.

        Raises:
            subprocess.CalledProcessError: در صورت شکست دستور zpool
        """
        cmd = ["/usr/bin/sudo", "/usr/bin/zpool", "destroy", "-f", pool_name]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)
        except subprocess.CalledProcessError as e:
            raise subprocess.CalledProcessError(
                e.returncode,
                e.cmd,
                f"خطا در حذف pool: {e.stderr.strip()}"
            )
        except Exception as e:
            raise Exception(f"خطای غیرمنتظره در حذف pool: {str(e)}")

    def replace_device(self, pool_name: str, old_device: str, new_device: str) -> None:
        """
        جایگزینی یک دیسک خراب با یک دیسک سالم.

        Args:
            pool_name (str): نام pool مورد نظر.
            old_device (str): مسیر کامل دستگاه خراب (مثل /dev/disk/by-id/wwn-...)
            new_device (str): مسیر کامل دستگاه جدید

        Raises:
            subprocess.CalledProcessError: در صورت شکست دستور zpool
        """
        cmd = [
            "/usr/bin/sudo", "/usr/bin/zpool", "replace", "-f",
            pool_name, old_device, new_device
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
        except subprocess.CalledProcessError as e:
            raise subprocess.CalledProcessError(
                e.returncode,
                e.cmd,
                f"خطا در جایگزینی دیسک: {e.stderr.strip()}"
            )
        except Exception as e:
            raise Exception(f"خطای غیرمنتظره در جایگزینی دیسک: {str(e)}")

    def add_vdev(self, pool_name: str, devices: List[str], vdev_type: str = "disk") -> None:
        """
        افزودن یک vdev جدید به یک pool موجود.

        Args:
            pool_name (str): نام pool مورد نظر.
            devices (List[str]): لیست مسیرهای کامل دستگاه‌ها
            vdev_type (str): نوع vdev (disk, mirror, raidz, spare, ...)

        Raises:
            subprocess.CalledProcessError: در صورت شکست دستور zpool
        """
        if vdev_type == "spare":
            cmd = ["/usr/bin/sudo", "/usr/bin/zpool", "add", "-f", pool_name, "spare"] + devices
        elif vdev_type == "disk":
            cmd = ["/usr/bin/sudo", "/usr/bin/zpool", "add", "-f", pool_name] + devices
        else:
            cmd = ["/usr/bin/sudo", "/usr/bin/zpool", "add", "-f", pool_name, vdev_type] + devices

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)
        except subprocess.CalledProcessError as e:
            raise subprocess.CalledProcessError(
                e.returncode,
                e.cmd,
                f"خطا در افزودن vdev: {e.stderr.strip()}"
            )
        except Exception as e:
            raise Exception(f"خطای غیرمنتظره در افزودن vdev: {str(e)}")

    def set_property(self, pool_name: str, prop: str, value: str) -> None:
        """
        تنظیم یک ویژگی ZFS Pool.

        Args:
            pool_name (str): نام pool مورد نظر.
            prop (str): نام ویژگی (مثل "autoreplace")
            value (str): مقدار جدید (مثل "on")

        Raises:
            subprocess.CalledProcessError: در صورت شکست دستور zpool
        """
        cmd = ["/usr/bin/sudo", "/usr/bin/zpool", "set", f"{prop}={value}", pool_name]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=10)
        except subprocess.CalledProcessError as e:
            raise subprocess.CalledProcessError(
                e.returncode,
                e.cmd,
                f"خطا در تنظیم ویژگی: {e.stderr.strip()}"
            )
        except Exception as e:
            raise Exception(f"خطای غیرمنتظره در تنظیم ویژگی: {str(e)}")
