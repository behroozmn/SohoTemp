#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
zfsDataset.py

High-level ZFS Dataset management library using libzfs binding.
- Provides ZFSDatasetManager class to manage filesystems, zvols (volumes), snapshots, bookmarks, and clones.
- Class-level attributes define default properties with inline comments for valid values.
- All operations use libzfs API (no shell CLI fallback).
- Methods return DRF-friendly JSON envelopes.

فارسی:
این کتابخانه برای مدیریت دیتاست‌های ZFS طراحی شده است.
ویژگی‌ها:
  - مدیریت volume, filesystem, snapshot, bookmark, clone
  - استفاده از libzfs به‌طور مستقیم
  - خروجی به صورت JSON سازگار با DRF
"""

from typing import Any, Dict, List, Optional
import datetime

try:
    import libzfs  # official python binding for ZFS
except Exception as exc:
    libzfs = None  # will raise meaningful error at runtime

# -------------------- JSON Envelopes --------------------

def ok(data: Any, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return success envelope."""
    return {"ok": True, "error": None, "data": data, "meta": meta or {}}

def fail(message: str, code: str = "zfs_dataset_error", extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return failure envelope."""
    return {"ok": False, "error": {"code": code, "message": message, "extra": extra or {}}, "data": None, "meta": {}}


# -------------------- Manager Class --------------------

class ZFSDatasetManager:
    """
    مدیر دیتاست‌های ZFS.

    این کلاس شامل همه پارامترهای مربوط به دیتاست (filesystem, volume, snapshot, bookmark, clone)
    به صورت متغیرهای سطح کلاس (attributes) می‌باشد.
    تمام عملیات (ایجاد، حذف، ویرایش، استخراج اطلاعات) با استفاده از libzfs انجام می‌شود.

    پارامترهای سازنده:
      - dry_run (bool): اگر True باشد، تغییرات واقعی اعمال نمی‌شوند.
      - run_timeout (int): زمان انتظار؛ در این پیاده‌سازی بیشتر جهت هماهنگی لحاظ شده.
    """

    # -------------------- Dataset Properties --------------------
    compression: Optional[str] = "lz4"          # "off","lz4","zstd","gzip","zle"
    dedup: Optional[str] = "off"                # "on","off","verify"
    atime: Optional[str] = "off"                # "on","off"
    recordsize: Optional[str] = "128K"          # "16K","128K","256K"
    volsize: Optional[str] = None               # e.g. "50G","10T"
    volblocksize: Optional[str] = "8K"          # "8K","16K","512"
    mountpoint: Optional[str] = "none"          # "/mnt/data","none"
    readonly: Optional[str] = "off"             # "on","off"
    quota: Optional[str] = "none"               # "100G","none"
    reservation: Optional[str] = "none"         # "10G","none"
    refquota: Optional[str] = None              # e.g. "50G"
    refreservation: Optional[str] = None        # e.g. "50G"
    primarycache: Optional[str] = "all"         # "all","none","metadata"
    secondarycache: Optional[str] = "all"       # "all","none","metadata"
    sync: Optional[str] = "standard"            # "standard","always","disabled"
    sharenfs: Optional[str] = "off"             # "on","off"
    shareiscsi: Optional[str] = "off"           # "on","off"
    copies: Optional[int] = 1                   # 1,2,3
    logbias: Optional[str] = "latency"          # "latency","throughput"
    snapdir: Optional[str] = "hidden"           # "visible","hidden"
    user_properties: Optional[Dict[str,str]] = None  # custom user props
    compression_level: Optional[int] = None     # for gzip: "1"-"9"

    def __init__(self, dry_run: bool = False, run_timeout: int = 120) -> None:
        """Initialize dataset manager."""
        self.dry_run = dry_run
        self.run_timeout = run_timeout
        if libzfs is None:
            self.zfs = None
        else:
            self.zfs = libzfs.ZFS()
        self._last_refresh: Optional[datetime.datetime] = None

    # -------------------- Internal Helpers --------------------

    def _ensure_binding(self) -> Optional[Dict[str, Any]]:
        """Ensure libzfs binding is available."""
        if self.zfs is None:
            return fail("libzfs binding not available", code="binding_missing")
        return None

    def _normalize(self, v: Any) -> Any:
        """Convert libzfs property object to primitive value."""
        return getattr(v, "value", v)

    # -------------------- Discovery --------------------

    def list_datasets(self) -> Dict[str, Any]:
        """Return list of all dataset names and types."""
        missing = self._ensure_binding()
        if missing: return missing
        try:
            items = [{
                "name": ds.name,
                "type": getattr(ds,
                "type", None)
            } for ds in self.zfs.datasets]
            return ok(items)
        except Exception as exc:
            return fail(str(exc))

    def get_dataset(self, name: str) -> Dict[str, Any]:
        """Return full details of a dataset."""
        missing = self._ensure_binding()
        if missing: return missing
        try:
            ds = self.zfs.get_dataset(name)
            info = {
                "name": ds.name,
                "type": getattr(ds, "type", None),
                "properties": {k: self._normalize(v) for k,v in getattr(ds,"properties",{}).items()},
                "snapshots": [{"name": s.name, "creation": getattr(s,"creation",None)} for s in getattr(ds,"snapshots",[])],
                "bookmarks": [{"name": b.name} for b in getattr(ds,"bookmarks",[])],
                "clones": [{"name": c.name} for c in getattr(ds,"clones",[])]
            }
            return ok(info)
        except Exception as exc:
            return fail(f"Dataset not found or error: {exc}", code="not_found")

    # -------------------- Create / Destroy / Edit --------------------

    def create_dataset(self, name: str, dataset_type: str="filesystem", properties: Optional[Dict[str,str]]=None) -> Dict[str, Any]:
        """Create dataset (filesystem or zvol)."""
        missing = self._ensure_binding()
        if missing: return missing
        if self.dry_run: return ok({"created": False,"dry_run": True,"name": name})
        try:
            if dataset_type not in ("filesystem","volume","zvol"):
                return fail("Invalid dataset_type", code="invalid_request")
            self.zfs.create(name, properties=properties or {})
            return ok({"created": True,"name": name,"type": dataset_type})
        except Exception as exc:
            return fail(str(exc))

    def destroy_dataset(self, name: str, recursive: bool=False, force: bool=False) -> Dict[str, Any]:
        """Destroy a dataset."""
        missing = self._ensure_binding()
        if missing: return missing
        if self.dry_run: return ok({"destroyed": False,"dry_run": True,"name": name})
        try:
            ds = self.zfs.get_dataset(name)
            ds.destroy(recursive=recursive, force=force)
            return ok({"destroyed": True,"name": name})
        except Exception as exc:
            return fail(str(exc))

    def edit_dataset(self, name: str, properties: Dict[str,str]) -> Dict[str, Any]:
        """Edit dataset properties."""
        missing = self._ensure_binding()
        if missing: return missing
        if self.dry_run: return ok({"edited": False,"dry_run": True,"name": name})
        try:
            ds = self.zfs.get_dataset(name)
            for k,v in properties.items():
                ds.set_property(k,v)
            return ok({"edited": True,"name": name,"changed": properties})
        except Exception as exc:
            return fail(str(exc))

    # -------------------- Snapshot / Bookmark / Clone --------------------

    def create_snapshot(self, dataset_at_snap: str, recursive: bool=False) -> Dict[str, Any]:
        """Create snapshot (dataset@snap)."""
        missing = self._ensure_binding()
        if missing: return missing
        if self.dry_run: return ok({"created": False,"dry_run": True,"snapshot": dataset_at_snap})
        if "@" not in dataset_at_snap:
            return fail("Invalid format; must be dataset@snap", code="invalid_request")
        try:
            ds_name, snap_name = dataset_at_snap.split("@",1)
            ds = self.zfs.get_dataset(ds_name)
            ds.create_snapshot(snap_name, recursive=recursive)
            return ok({"created": True,"snapshot": dataset_at_snap})
        except Exception as exc:
            return fail(str(exc))

    def list_snapshots(self, dataset_name: Optional[str]=None) -> Dict[str, Any]:
        """List snapshots (all or for specific dataset)."""
        missing = self._ensure_binding()
        if missing: return missing
        try:
            snaps = []
            if dataset_name:
                ds = self.zfs.get_dataset(dataset_name)
                snaps = [{"name": s.name,"creation": getattr(s,"creation",None)} for s in ds.snapshots]
            else:
                for ds in self.zfs.datasets:
                    for s in ds.snapshots:
                        snaps.append({"name": s.name,"dataset": ds.name})
            return ok(snaps)
        except Exception as exc:
            return fail(str(exc))

    def create_bookmark(self, snapshot: str, bookmark_name: str) -> Dict[str, Any]:
        """Create a bookmark from snapshot."""
        missing = self._ensure_binding()
        if missing: return missing
        if self.dry_run: return ok({"created": False,"dry_run": True,"bookmark": bookmark_name})
        try:
            self.zfs.bookmark(snapshot, bookmark_name)
            return ok({"created": True,"bookmark": bookmark_name})
        except Exception as exc:
            return fail(str(exc))

    def clone_snapshot(self, snapshot: str, target: str, properties: Optional[Dict[str,str]]=None) -> Dict[str, Any]:
        """Clone a snapshot into writable dataset."""
        missing = self._ensure_binding()
        if missing: return missing
        if self.dry_run: return ok({"cloned": False,"dry_run": True,"snapshot": snapshot})
        try:
            self.zfs.clone(snapshot, target, properties=properties or {})
            return ok({"cloned": True,"from": snapshot,"to": target})
        except Exception as exc:
            return fail(str(exc))

    def promote_clone(self, clone_name: str) -> Dict[str, Any]:
        """Promote a clone to be independent."""
        missing = self._ensure_binding()
        if missing: return missing
        try:
            ds = self.zfs.get_dataset(clone_name)
            ds.promote()
            return ok({"promoted": True,"clone": clone_name})
        except Exception as exc:
            return fail(str(exc))

    def rollback(self, dataset: str, to_snapshot: Optional[str]=None, destroy_more_recent: bool=False) -> Dict[str, Any]:
        """Rollback dataset to snapshot."""
        missing = self._ensure_binding()
        if missing: return missing
        try:
            ds = self.zfs.get_dataset(dataset)
            if to_snapshot:
                snap_full = to_snapshot if "@" in to_snapshot else f"{dataset}@{to_snapshot}"
                ds.rollback(snap_full, destroy_more_recent=destroy_more_recent)
                return ok({"rolled_back": True,"to": snap_full})
            else:
                ds.rollback(destroy_more_recent=destroy_more_recent)
                return ok({"rolled_back": True,"to": "latest"})
        except Exception as exc:
            return fail(str(exc))

    # -------------------- Utilities --------------------

    def dataset_exists(self, name: str) -> Dict[str, Any]:
        """Check if dataset exists."""
        missing = self._ensure_binding()
        if missing: return missing
        try:
            self.zfs.get_dataset(name)
            return ok({"exists": True})
        except Exception:
            return ok({"exists": False})

    def datasets_under_pool(self, pool_name: str) -> Dict[str, Any]:
        """Return summary of datasets under a pool."""
        missing = self._ensure_binding()
        if missing: return missing
        try:
            out = []
            for ds in self.zfs.datasets:
                if ds.name == pool_name or ds.name.startswith(pool_name+"/"):
                    props = {k: self._normalize(v) for k,v in getattr(ds,"properties",{}).items()}
                    out.append({
                        "name": ds.name,
                        "type": getattr(ds,"type",None),
                        "used": props.get("used"),
                        "available": props.get("available"),
                        "referenced": props.get("referenced")
                    })
            return ok(out)
        except Exception as exc:
            return fail(str(exc))
