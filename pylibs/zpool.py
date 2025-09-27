#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import libzfs
from typing import Any, Dict, Optional
import subprocess


def ok(data: Any) -> Dict[str, Any]:
    """Return a success envelope (DRF-ready)."""
    return {"ok": True, "error": None, "data": data, "details": {}}


def fail(message: str, code: str = "zpool_error", extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a failure envelope (DRF-ready)."""
    return {"ok": False, "error": {"code": code, "message": message, "extra": extra or {}}, "data": None, "details": {}}


class ZpoolManager:
    def __init__(self) -> None:
        self.zfs = libzfs.ZFS()

    def list_pool_detail(self, pool_name: str = None):
        try:
            # اگر pool_name داده شده باشد، فقط آن pool را فیلتر کن
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
                # "cachemode": str(p.properties["cachemode"].value),
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
                    cmd = ["zpool", "create", pool_name] + devices
                else:
                    cmd = ["zpool", "create", pool_name, vdev_type] + devices
                subprocess.run(cmd, check=True)
                return ok({"name": "موفقیت آمیز ساخته شد", })
            else:
                return fail("محتویات آرگومان های ورودی خالی است",
                            "create_pool",
                            {"pool_name": pool_name, "devices": devices, "vdev_type": vdev_type})
        except subprocess.CalledProcessError as exc:
            return fail(str(exc))
        except Exception as exc:
            return fail(str(exc))

    def pool_delete(self, pool_name: str):
        try:
            cmd = ["zpool", "destroy", pool_name]
            subprocess.run(cmd, check=True)
            return ok({"name": "موفقیت آمیز حذف شد", })
        except subprocess.CalledProcessError as cpe:
            return fail(str(cpe))
        except Exception as exc:
            return fail(str(exc))
