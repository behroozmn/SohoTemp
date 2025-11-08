#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import libzfs
from typing import Any, Dict, Optional
import subprocess
import os

from pylibs.file import File_Temp


def ok(data: Any) -> Dict[str, Any]:
    """Return a success envelope (DRF-ready)."""
    return {"ok": True, "error": None, "data": data, "details": {}}


def fail(message: str, code: str = "zpool_error", extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a failure envelope (DRF-ready)."""
    return {"ok": False, "error": {"code": code, "message": message, "extra": extra or {}}, "data": None, "details": {}}


def _get_wwn_from_device_path(device_path: str) -> str:
    """
    استخراج WWN از مسیر دستگاه (حتی اگر پارتیشن باشد، مثل /dev/sda1).
    """
    try:
        # استخراج نام دیسک اصلی از مسیر (مثلاً از sda1 → sda)
        if device_path.startswith("/dev/"):
            dev_name = os.path.basename(device_path)
        else:
            dev_name = device_path

        # حذف شماره پارتیشن: sda1 → sda, nvme0n1p1 → nvme0n1
        import re
        disk_name = re.sub(r'[0-9]+$', '', dev_name)  # برای sda1, sdb2, ...
        disk_name = re.sub(r'p[0-9]+$', '', disk_name)  # برای nvme0n1p1

        # جلوگیری از نام‌های نامعتبر (مثل "sda" که به "sd" تبدیل نشود)
        if not disk_name or disk_name == dev_name:
            disk_name = dev_name

        # مسیر sysfs برای دیسک اصلی
        wwn_path = f"/sys/block/{disk_name}/device/wwid"
        if os.path.exists(wwn_path):
            with open(wwn_path, "r") as f:
                wwn = f.read().strip()
                if wwn:
                    return wwn.replace("naa.", "wwn-0x")

        # fallback: سریال دیسک (اگر WWN نبود)
        serial_path = f"/sys/block/{disk_name}/device/serial"
        if os.path.exists(serial_path):
            with open(serial_path, "r") as f:
                serial = f.read().strip()
                if serial:
                    return f"SERIAL:{serial}"

    except Exception:
        pass
    return ""


class ZpoolManager:
    def __init__(self) -> None:
        self.zfs = libzfs.ZFS()

    def list_pool_detail(self, pool_name: str = None):
        try:
            if pool_name:
                pools = [p for p in self.zfs.pools if str(p.properties["name"].value) == pool_name]
            else:
                pools = self.zfs.pools
            items = [{
                "name": str(p.properties["name"].value),
                "allocated": str(p.properties["allocated"].value),
                "altroot": str(p.properties["altroot"].value),
                "ashift": str(p.properties["ashift"].value),
                "autoexpand": str(p.properties["autoexpand"].value),
                "autoreplace": str(p.properties["autoreplace"].value),
                "bootfs": str(p.properties["bootfs"].value),
                "capacity": str(p.properties["capacity"].value),
                "comment": str(p.properties["comment"].value),
                "dedupditto": str(p.properties["dedupditto"].value),
                "dedupratio": str(p.properties["dedupratio"].value),
                "delegation": str(p.properties["delegation"].value),
                "expandsize": str(p.properties["expandsize"].value),
                "failmode": str(p.properties["failmode"].value),
                "fragmentation": str(p.properties["fragmentation"].value),
                "freeing": str(p.properties["freeing"].value),
                "free": str(p.properties["free"].value),
                "guid": str(p.properties["guid"].value),
                "health": str(p.properties["health"].value),
                "leaked": str(p.properties["leaked"].value),
                "listsnapshots": str(p.properties["listsnapshots"].value),
                "readonly": str(p.properties["readonly"].value),
                "size": str(p.properties["size"].value)
            } for p in pools]
            return ok(items)
        except Exception as exc:
            return fail(str(exc))

    def create_pool(self, pool_name: str, devices: list[str], vdev_type: str = "disk"):
        """
        ایجاد یک ZFS pool با استفاده از دستور zpool.

        Args:
            pool_name (str): نام pool (مثلاً "mypool")
            devices (list[str]): لیست دیوایس‌ها (مثلاً ['/dev/sdb', '/dev/sdc'])
            vdev_type (str): نوع vdev (disk, mirror, raidz, raidz2, ...)
        """
        try:
            if pool_name and devices and vdev_type:
                if vdev_type == "disk":
                    cmd = ["/usr/bin/sudo", "/usr/bin/zpool", "create", pool_name] + devices
                else:
                    cmd = ["/usr/bin/sudo", "/usr/bin/zpool", "create", pool_name, vdev_type] + devices
                subprocess.run(cmd, check=True)
                return ok({"message": "Pool با موفقیت ساخته شد."})
            else:
                return fail("محتویات آرگومان‌های ورودی خالی است", "create_pool", {"pool_name": pool_name, "devices": devices, "vdev_type": vdev_type})
        except subprocess.CalledProcessError as exc:
            return fail(f"خطا در اجرای دستور zpool: {exc}")
        except Exception as exc:
            return fail(f"خطای غیرمنتظره: {exc}")

    def pool_delete(self, pool_name: str):
        obj_file = File_Temp()
        if not obj_file.string_exists_in_file(pool_name, "/etc/samba/smb.conf"):
            try:
                cmd = ["/usr/bin/sudo","/usr/bin/zpool", "destroy", pool_name]
                subprocess.run(cmd, check=True)
                return ok({"message": "Pool با موفقیت حذف شد."})
            except subprocess.CalledProcessError as cpe:
                return fail(f"خطا در حذف pool: {cpe}")
            except Exception as exc:
                return fail(f"خطای غیرمنتظره: {exc}")
        else:
            return fail(f"pool {pool_name} is bussy in shareConfiguration:")


    def list_pool_devices(self, pool_name: str) -> Dict[str, Any]:
        """
        بازگرداندن لیست دیسک‌های فیزیکی یک ZFS pool خاص همراه با WWN.
        """
        try:
            # پیدا کردن pool با نام داده‌شده
            target_pool = None
            for p in self.zfs.pools:
                if str(p.properties["name"].value) == pool_name:
                    target_pool = p
                    break

            if not target_pool:
                return fail(f"Pool با نام '{pool_name}' یافت نشد.", "pool_not_found")

            devices = []

            def traverse_vdevs(vdev, parent_type="root"):
                """پیمایش بازگشتی ساختار vdevها"""
                # فقط دیسک‌های فیزیکی یا فایل‌ها را در نظر بگیر
                if vdev.type in ("disk", "file"):
                    wwn = _get_wwn_from_device_path(vdev.path)
                    devices.append({
                        "name": vdev.path.replace("1", ""),
                        "status": getattr(vdev, 'status', 'UNKNOWN'),
                        "type": vdev.type,
                        "parent_vdev": parent_type,
                        "wwn": f"/dev/disk/by-id/{wwn}",
                    })
                # پیمایش زیرشاخه‌ها (mirror, raidz, etc.)
                elif hasattr(vdev, 'children') and vdev.children:
                    for child in vdev.children:
                        traverse_vdevs(child, parent_type=vdev.type)

            traverse_vdevs(target_pool.root_vdev)

            return ok({
                "pool_name": pool_name,
                "devices": devices
            })

        except Exception as exc:
            return fail(f"خطا در دریافت لیست دیسک‌ها: {str(exc)}", "device_list_error")
