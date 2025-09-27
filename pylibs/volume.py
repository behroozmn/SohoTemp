#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import libzfs
from typing import Any, Dict, Optional
import subprocess


def ok(data: Any) -> Dict[str, Any]:
    """Return a success envelope (DRF-ready)."""
    return {"ok": True, "error": None, "data": data, "details": {}}


def fail(message: str, code: str = "zpool_error", extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message, "extra": extra or {}}, "data": None, "details": {}}


class VolumeManager:
    def __init__(self) -> None:
        self.zfs = libzfs.ZFS()

    def list_volume_detail(self, volume_name :str = None):
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