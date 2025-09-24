# zfsDataset.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
zfsDataset module: ZFSDatasetManager for dataset-level operations (filesystem, zvol, snapshot, bookmark, clone).
This module prefers libzfs for reading/setting properties and uses CLI only for fallback mutating operations if required.

Inline comments are English. Docstrings are Persian and describe parameters/returns.
"""

from typing import Dict, List, Optional, Any
import libzfs
import subprocess
import shlex
import datetime

def ok(data: Any, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Success envelope."""
    return {"ok": True, "error": None, "data": data, "meta": meta or {}}

def fail(message: str, code: str = "zfs_dataset_error", extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Failure envelope."""
    return {"ok": False, "error": {"code": code, "message": message, "extra": extra or {}}, "data": None, "meta": {}}


class ZFSDatasetManager:
    """
    کلاس ZFSDatasetManager برای عملیات مربوط به dataset ها (filesystems, zvols, snapshots, bookmarks, clones).

    ویژگی‌ها (class attributes): تعریف مجموعه‌ای از پراپرتی‌های رایج dataset به‌صورت متغیر کلاس با مقدار پیش‌فرض.
    مثال‌ها در کامنت انگلیسی هر attribute ذکر شده‌اند.
    """

    # Common dataset-level properties with defaults (class-level)
    compression: Optional[str] = None        # Possible: "off","lz4","zstd","gzip"
    dedup: Optional[str] = None              # Possible: "on","off","verify"
    atime: Optional[str] = None              # Possible: "on","off"
    recordsize: Optional[str] = None         # Possible: "128K","256K","16K"
    volsize: Optional[str] = None            # For zvols e.g. "50G"
    volblocksize: Optional[str] = None       # For zvols e.g. "8K","16K"
    mountpoint: Optional[str] = None         # e.g. "/mnt/data" or "none"
    readonly: Optional[str] = None           # "on","off"
    quota: Optional[str] = None              # e.g. "100G", "none"
    reservation: Optional[str] = None        # e.g. "10G", "none"
    primarycache: Optional[str] = None       # "all","none","metadata"
    secondarycache: Optional[str] = None     # "all","none","metadata"
    sync: Optional[str] = None               # "standard","always","disabled"
    sharenfs: Optional[str] = None           # "on","off"
    shareiscsi: Optional[str] = None         # "on","off"
    copies: Optional[int] = None             # 1,2,3
    logbias: Optional[str] = None            # "latency","throughput"
    snapdir: Optional[str] = None            # "visible","hidden"
    # More attributes can be added as needed

    def __init__(self, dry_run: bool = False, run_timeout: int = 120) -> None:
        """
        سازنده ZFSDatasetManager.
        ورودی:
          - dry_run (bool): اگر True باشد عملیات تغییر‌دهنده اجرا نمی‌شوند.
          - run_timeout (int): timeout برای fallback CLI.
        خروجی: None
        """
        self.zfs = libzfs.ZFS()  # libzfs instance
        self.dry_run = dry_run  # do not execute destructive ops if True
        self.run_timeout = run_timeout  # CLI fallback timeout
        self._last_refresh = None

    # -------------------- helpers --------------------

    def _safe(self, v: Any) -> Any:
        """Normalize libzfs property object to simple value."""
        return getattr(v, "value", v)

    def _run_cli(self, args: List[str]) -> Dict[str,str]:
        """Run CLI command if fallback needed."""
        cmd_str = " ".join(shlex.quote(a) for a in args)
        if self.dry_run:
            return {"stdout": f"[DRY-RUN] {cmd_str}", "stderr": ""}
        proc = subprocess.run(args, capture_output=True, timeout=self.run_timeout, check=False)
        return {"stdout": proc.stdout.decode(errors="ignore"), "stderr": proc.stderr.decode(errors="ignore")}

    # -------------------- dataset discovery --------------------

    def list_datasets(self) -> Dict[str, Any]:
        """
        Return list of all datasets with their types.
        خروجی:
          - dict with list of {"name": "...", "type": "..."}
        """
        try:
            items = []
            for ds in self.zfs.datasets:
                items.append({"name": ds.name, "type": getattr(ds, "type", None)})
            return ok(items)
        except Exception as exc:
            return fail(str(exc))

    def get_dataset(self, name: str) -> Dict[str, Any]:
        """
        Return full dataset info for given name (type, properties, space usage, snapshots/bookmarks).
        ورودی:
          - name (str): dataset name
        خروجی:
          - dict: detailed dataset info
        """
        try:
            ds = self.zfs.get_dataset(name)  # may raise
            info: Dict[str, Any] = {}
            info["name"] = ds.name
            info["type"] = getattr(ds, "type", None)
            # properties
            props = {}
            try:
                for k, v in getattr(ds, "properties", {}).items():
                    props[k] = str(self._safe(v))
            except Exception:
                pass
            info["properties"] = props
            # space/usage
            try:
                # libzfs may expose referenced/used/available properties
                info["referenced"] = props.get("referenced") or props.get("used") or None
                info["used"] = props.get("used")
                info["available"] = props.get("available")
            except Exception:
                pass
            # snapshots & bookmarks (use libzfs dataset.snapshots if available)
            snaps = []
            try:
                for s in ds.snapshots:  # type: ignore
                    snaps.append({"name": s.name, "creation": getattr(s, "creation", None)})
            except Exception:
                # fallback: no snapshots attribute
                snaps = []
            info["snapshots"] = snaps
            # bookmarks: some bindings might have dataset.bookmarks
            bms = []
            try:
                for b in getattr(ds, "bookmarks", []) or []:
                    bms.append({"name": getattr(b, "name", None)})
            except Exception:
                pass
            info["bookmarks"] = bms
            return ok(info)
        except libzfs.ZFSException as exc:
            return fail(f"Dataset not found: {name}", code="not_found")
        except Exception as exc:
            return fail(str(exc))

    # -------------------- create / destroy / edit --------------------

    def create_dataset(self, name: str, dataset_type: str = "filesystem", properties: Optional[Dict[str,str]] = None) -> Dict[str, Any]:
        """
        Create a dataset (filesystem or zvol). Prefer libzfs when able; fallback to CLI if required.
        ورودی:
          - name (str): dataset full name
          - dataset_type (str): "filesystem" or "volume"
          - properties (dict|None): properties map (must contain volsize for zvol)
        خروجی:
          - dict envelope
        """
        try:
            # attempt libzfs create if available
            try:
                if dataset_type == "filesystem":
                    self.zfs.create(name, properties=properties or {})  # some bindings accept create(name, properties={})
                    return ok({"created": True, "dataset": name})
                else:
                    # For volume, libzfs binding may have create_zvol or similar
                    # We try generic create and fall back later
                    self.zfs.create(name, properties=properties or {})  # may raise
                    return ok({"created": True, "dataset": name})
            except Exception:
                # fallback to CLI zfs create
                if dataset_type == "volume" and (not properties or "volsize" not in properties):
                    return fail("volsize is required for volume creation", code="invalid_request")
                args = ["zfs", "create", "-p"]
                if properties:
                    for k, v in properties.items():
                        args += ["-o", f"{k}={v}"]
                args.append(name)
                res = self._run_cli(args)
                if res["stderr"]:
                    return fail("CLI create failed", extra={"stderr": res["stderr"]})
                return ok({"created": True, "dataset": name, "stdout": res["stdout"]})
        except Exception as exc:
            return fail(str(exc))

    def destroy_dataset(self, name: str, recursive: bool = False, force: bool = False) -> Dict[str, Any]:
        """
        Destroy a dataset. Uses libzfs.destroy_dataset if available; otherwise CLI fallback.
        ورودی:
          - name (str)
          - recursive (bool)
          - force (bool)
        خروجی:
          - dict envelope
        """
        try:
            # attempt libzfs
            try:
                ds = self.zfs.get_dataset(name)
                if hasattr(ds, "destroy"):
                    ds.destroy(recursive=recursive, force=force)  # type: ignore
                    return ok({"destroyed": True, "dataset": name})
            except Exception:
                pass
            # fallback CLI
            args = ["zfs", "destroy"]
            if recursive:
                args.append("-r")
            if force:
                args.append("-f")
            args.append(name)
            res = self._run_cli(args)
            if res["stderr"]:
                return fail("CLI destroy failed", extra={"stderr": res["stderr"]})
            return ok({"destroyed": True, "dataset": name, "stdout": res["stdout"]})
        except Exception as exc:
            return fail(str(exc))

    def edit_dataset_props(self, name: str, properties: Dict[str,str]) -> Dict[str, Any]:
        """
        Edit dataset properties. Prefer libzfs set_property on dataset object; fallback to CLI zfs set.
        ورودی:
          - name (str)
          - properties (dict)
        خروجی:
          - dict with changed properties
        """
        try:
            try:
                ds = self.zfs.get_dataset(name)
                changed = {}
                for k, v in properties.items():
                    try:
                        ds.set_property(k, v)  # type: ignore
                        changed[k] = v
                    except Exception:
                        # try CLI for that key
                        res = self._run_cli(["zfs", "set", f"{k}={v}", name])
                        if res["stderr"]:
                            return fail(f"Failed to set {k}", extra={"stderr": res["stderr"]})
                        changed[k] = v
                return ok({"dataset": name, "changed": changed})
            except libzfs.ZFSException:
                # fallback: CLI for all
                changed = {}
                for k, v in properties.items():
                    res = self._run_cli(["zfs", "set", f"{k}={v}", name])
                    if res["stderr"]:
                        return fail(f"Failed to set {k}", extra={"stderr": res["stderr"]})
                    changed[k] = v
                return ok({"dataset": name, "changed": changed, "method": "cli_fallback"})
        except Exception as exc:
            return fail(str(exc))

    # -------------------- snapshot / bookmark / clone helpers --------------------

    def create_snapshot(self, dataset_at_snap: str, recursive: bool = False) -> Dict[str, Any]:
        """
        Create a snapshot (dataset@snapname). Uses libzfs if available else CLI fallback.
        ورودی:
          - dataset_at_snap (str): e.g. "tank/data@now"
          - recursive (bool)
        خروجی:
          - dict envelope
        """
        try:
            try:
                ds_name, snap_name = dataset_at_snap.split("@", 1)
            except ValueError:
                return fail("snapshot name must be dataset@snap", code="invalid_request")
            try:
                ds = self.zfs.get_dataset(ds_name)
                # some bindings offer create_snapshot on dataset
                if hasattr(ds, "create_snapshot"):
                    ds.create_snapshot(snap_name, recursive=recursive)  # type: ignore
                    return ok({"snapshot": dataset_at_snap, "created": True})
            except Exception:
                pass
            # CLI fallback
            args = ["zfs", "snapshot"]
            if recursive:
                args.append("-r")
            args.append(dataset_at_snap)
            res = self._run_cli(args)
            if res["stderr"]:
                return fail("CLI snapshot failed", extra={"stderr": res["stderr"]})
            return ok({"snapshot": dataset_at_snap, "created": True, "stdout": res["stdout"]})
        except Exception as exc:
            return fail(str(exc))

    def create_bookmark(self, snapshot: str, bookmark: str) -> Dict[str, Any]:
        """
        Create a bookmark from an existing snapshot.
        ورودی:
          - snapshot (str): "tank/data@A"
          - bookmark (str): "tank/data#bm"
        خروجی:
          - dict envelope
        """
        try:
            # try CLI (bookmarks are often CLI-only in some bindings)
            res = self._run_cli(["zfs", "bookmark", snapshot, bookmark])
            if res["stderr"]:
                return fail("CLI bookmark failed", extra={"stderr": res["stderr"]})
            return ok({"bookmark": bookmark, "from": snapshot})
        except Exception as exc:
            return fail(str(exc))

    def clone_snapshot(self, snapshot: str, target: str, properties: Optional[Dict[str,str]] = None) -> Dict[str, Any]:
        """
        Clone a snapshot into a writable dataset.
        ورودی:
          - snapshot (str)
          - target (str)
          - properties (optional dict)
        خروجی:
          - dict envelope
        """
        try:
            # try CLI clone because lib bindings vary
            args = ["zfs", "clone"]
            if properties:
                for k,v in properties.items():
                    args += ["-o", f"{k}={v}"]
            args += [snapshot, target]
            res = self._run_cli(args)
            if res["stderr"]:
                return fail("CLI clone failed", extra={"stderr": res["stderr"]})
            return ok({"cloned": True, "from": snapshot, "to": target})
        except Exception as exc:
            return fail(str(exc))

    # -------------------- convenience / utility --------------------

    def dataset_names_with_type(self) -> Dict[str, Any]:
        """
        Return list of datasets with their type (name,type).
        خروجی:
          - dict with list
        """
        try:
            items = []
            for ds in self.zfs.datasets:
                items.append({"name": ds.name, "type": getattr(ds, "type", None)})
            return ok(items)
        except Exception as exc:
            return fail(str(exc))

    def get_snapshots_of_dataset(self, dataset_name: str) -> Dict[str, Any]:
        """
        Return a list of snapshots for a dataset.
        ورودی:
          - dataset_name (str)
        خروجی:
          - dict with snapshots list
        """
        try:
            ds = self.zfs.get_dataset(dataset_name)
            snaps = []
            try:
                for s in ds.snapshots:
                    snaps.append({"name": s.name, "creation": getattr(s, "creation", None)})
            except Exception:
                pass
            return ok(snaps)
        except libzfs.ZFSException:
            return fail("Dataset not found", code="not_found")
        except Exception as exc:
            return fail(str(exc))


__all__ = ["ZFSDatasetManager", "ok", "fail"]
