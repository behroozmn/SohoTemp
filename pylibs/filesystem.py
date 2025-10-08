#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import libzfs
from typing import Any, Dict, Optional, List
import subprocess



def ok(data: Any) -> Dict[str, Any]:
    """Return a success envelope (DRF-ready)."""
    return {"ok": True, "error": None, "data": data, "details": {}}


def fail(message: str, code: str = "volume_error", extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message, "extra": extra or {}}, "data": None, "details": {}}


class FilesystemManager:
    def __init__(self) -> None:
        self.zfs = libzfs.ZFS()

    def list_filesystem_detail(self):
        try:
            all_filesystem = [ds for ds in self.zfs.datasets if getattr(ds, 'type', None) == 1]
            items = [{
                "name": vol.name,
                "mountpoint": getattr(vol, "mountpoint", None),
                "type": "filesystem",
                "type_number": getattr(vol, "type", None),
            } for vol in all_filesystem if vol.name != f'/{getattr(vol, "mountpoint", None)}' ]
            return ok(items)
        except Exception as exc:
            return fail(f"Error listing filesystem: {str(exc)}")

    def create(self, filesystem_name: str, properties: Dict[str, str]=None):
        try:
            # zfs create p1/ds1 -o quota=100g -o reservation=50G
            cmd: List[str] = ["/usr/bin/sudo","/usr/bin/zfs", "create"]

            # اگر پراپرتی‌ها وجود داشتن، هر کدوم رو با -o اضافه کن
            if properties:
                for key, value in properties.items():
                    cmd += ["-o", f"{key}={value}"]

            cmd.append(filesystem_name)

            # اجرای دستور
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return ok({
                "status": "موفقیت‌آمیز ساخته شد",
                "name": filesystem_name,
                "properties": properties
            })
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.strip() if e.stderr else str(e)
            return fail(f"Error creating volume: {stderr}")
        except Exception as exc:
            return fail(f"Error creating volume: {str(exc)}")

    def delete(self, filesystem_name: str):
        try:
            cmd = ["/usr/bin/sudo","/usr/bin/zfs", "destroy", filesystem_name]  # اجرای دستور: zfs destroy filesystem_name
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return ok({
                "status": "موفقیت‌آمیز حذف شد",
                "name": filesystem_name
            })
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.strip() if e.stderr else str(e)
            # بررسی خطا برای حالتی که volume وجود ندارد
            if "dataset does not exist" in stderr or "no such dataset" in stderr.lower():
                return fail(f"Volume '{filesystem_name}' not found", code="not_found")
            return fail(f"Error deleting volume: {stderr}")
        except Exception as exc:
            return fail(f"Error deleting volume: {str(exc)}")
