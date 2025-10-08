#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import libzfs
from typing import Any, Dict, Optional
import subprocess

from django.db.models.expressions import result


def ok(data: Any) -> Dict[str, Any]:
    """Return a success envelope (DRF-ready)."""
    return {"ok": True, "error": None, "data": data, "details": {}}


def fail(message: str, code: str = "volume_error", extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message, "extra": extra or {}}, "data": None, "details": {}}


class VolumeManager:
    def __init__(self) -> None:
        self.zfs = libzfs.ZFS()

    def list_volume_detail(self, volume_name: str = None):
        try:
            all_volumes = [ds for ds in self.zfs.datasets if getattr(ds, 'type', None) == 4]

            if volume_name is not None:
                filtered_volumes = [vol for vol in all_volumes if vol.name == volume_name]
            else:
                filtered_volumes = all_volumes

            items = [{
                "name": vol.name,
                "mountpoint": getattr(vol, "mountpoint", None),
                "type": "volume",
                "type_number": getattr(vol, "type", None),
            } for vol in filtered_volumes]
            return ok(items)
        except Exception as exc:
            return fail(f"Error listing volumes: {str(exc)}")

    def create(self, volume_name: str, properties: Dict[str, str]):
        try:
            if "volsize" not in properties:
                return fail("Missing required property: 'volsize' (e.g., '10G')")

            # ساخت دستور zfs create
            cmd = ["/usr/bin/sudo", "/usr/bin/zfs", "create", "-V", properties["volsize"]]
            for key, value in properties.items():
                if key != "volsize":
                    cmd += ["-o", f"{key}={value}"]
            cmd.append(volume_name)

            # اجرای دستور
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return ok({
                "status": "موفقیت‌آمیز ساخته شد",
                "name": volume_name,
                "properties": properties
            })
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.strip() if e.stderr else str(e)
            return fail(f"Error creating volume: {stderr}")
        except Exception as exc:
            return fail(f"Error creating volume: {str(exc)}")

    def delete(self, volume_name: str):
        import subprocess
        try:
            cmd = ["/usr/bin/sudo", "/usr/bin/zfs", "destroy", volume_name]  # اجرای دستور: zfs destroy volume_name
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return ok({
                "status": "موفقیت‌آمیز حذف شد",
                "name": volume_name
            })
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.strip() if e.stderr else str(e)
            # بررسی خطا برای حالتی که volume وجود ندارد
            if "dataset does not exist" in stderr or "no such dataset" in stderr.lower():
                return fail(f"Volume '{volume_name}' not found", code="not_found")
            return fail(f"Error deleting volume: {stderr}")
        except Exception as exc:
            return fail(f"Error deleting volume: {str(exc)}")
