#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FA: این ماژول یک کلاس سطح‌بالا برای مدیریت ZFS با libzfs و fallback ایمن به CLI ارائه می‌دهد.
# EN: This module provides a high-level ZFS manager using libzfs with safe CLI fallbacks.

import libzfs  # required by user request: use libzfs binding
import subprocess
import shlex
from typing import Dict, List, Optional, Iterable, Tuple, Any


# --------------------------- JSON envelopes ---------------------------

def ok(data: Any, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a DRF-friendly success envelope."""
    # FA: پاسخ موفق استاندارد برای بازگشت به DRF.
    # EN: Standard success envelope to return in DRF responses.
    return {"ok": True, "error": None, "data": data, "meta": meta or {}}


def fail(message: str, code: str = "zfs_error", extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a DRF-friendly failure envelope."""
    # FA: پاسخ خطا با پیام و کُد منطقی.
    # EN: Failure envelope with human-readable message and logical code.
    return {"ok": False, "error": {"code": code, "message": message, "extra": extra or {}}, "data": None, "meta": {}}


class ZFSError(Exception):
    """Domain exception for ZFS manager."""
    # FA: استثنای دامنه‌ای مخصوص ZFS برای تفکیک خطاها.
    # EN: Domain-specific exception for clear error separation.
    pass


class ZFSManager:
    """
    High-level ZFS manager using libzfs and safe CLI fallbacks.

    dry_run=True برای تستِ بدون تغییر

    - All public methods return JSON-serializable dicts (friendly to DRF Response()).
    - Uses libzfs for discovery/property ops; uses `zfs`/`zpool` CLI for gaps (send/recv, create pool, etc.).
    """

    def __init__(self, dry_run: bool = False, run_timeout: int = 180) -> None:
        """Initialize manager with libzfs, dry-run mode and CLI timeout."""
        # FA: اتصال libzfs برقرار می‌شود؛ dry_run برای تست بدون اعمال تغییر؛ run_timeout برای محدود کردن اجرای CLI.
        # EN: Initialize libzfs; dry_run to simulate actions; run_timeout limits CLI execution time.

        self.zfs = libzfs.ZFS()
        self.dry_run = dry_run
        self.run_timeout = run_timeout

    # --------------------------- internal helpers ---------------------------

    def _run(self, args: List[str], stdin: Optional[bytes] = None) -> Tuple[str, str]:
        """Run a CLI command safely (no shell=True), return (stdout, stderr)."""
        # FA: اجرای امن CLI با آرگومان‌های لیستی جهت جلوگیری از تزریق؛ پشتیبانی از ورودی باینری.
        # EN: Safe CLI execution with list args to avoid injection; supports binary stdin.
        cmd_str = " ".join(shlex.quote(a) for a in args)
        if self.dry_run:
            return f"[DRY-RUN] {cmd_str}", ""
        try:
            proc = subprocess.run(args, input=stdin, capture_output=True, timeout=self.run_timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ZFSError(f"Command failed: {cmd_str} ({exc})") from exc
        if proc.returncode != 0:
            raise ZFSError(
                f"Command failed: {cmd_str}\nstdout: {proc.stdout.decode(errors='ignore')}\nstderr: {proc.stderr.decode(errors='ignore')}"
            )
        return proc.stdout.decode(errors="ignore"), proc.stderr.decode(errors="ignore")

    def _get_dataset(self, name: str) -> libzfs.ZFSDataset:
        """Return dataset object or raise ZFSError."""
        # FA: تلاش برای گرفتن دیتاست از libzfs؛ در صورت نبود، خطا می‌دهیم.
        # EN: Try fetching dataset via libzfs; raise if not found.
        try:
            return self.zfs.get_dataset(name)
        except libzfs.ZFSException as exc:
            raise ZFSError(f"Dataset not found: {name}") from exc

    def _get_pool(self, name: str) -> libzfs.ZFSPool:
        """Return pool object or raise ZFSError."""
        # FA: در بین poolها جستجو می‌کنیم و نام مطابق را بازمی‌گردانیم.
        # EN: Iterate pools and return the matching one by name.
        for pool in self.zfs.pools:
            if pool.name == name:
                return pool
        raise ZFSError(f"Pool not found: {name}")

    def _safe_prop_value(self, v: Any) -> Any:
        """Normalize libzfs property object to plain value if needed."""
        # FA: برخی bindingها شیء Property برمی‌گردانند؛ value را استخراج می‌کنیم.
        # EN: Some bindings return Property objects; extract .value when present.
        return getattr(v, "value", v)

    # --------------------------- discovery & listing ---------------------------

    def list_pools(self) -> Dict[str, Any]:
        """List zpool names."""
        # FA: نام تمام zpoolها را از libzfs می‌گیریم.
        # EN: Get all zpool names via libzfs.
        try:
            return ok([p.name for p in self.zfs.pools])
        except Exception as exc:
            return fail(str(exc))

    def pool_status(self, pool: str) -> Dict[str, Any]:
        """Basic pool status: name/state/health/guid and a few props."""
        # FA: وضعیت ساده‌ی یک zpool به‌همراه چند property مهم.
        # EN: Simple zpool status with a few important properties.
        try:
            p = self._get_pool(pool)
            extras = {}
            for prop in ("ashift", "autoexpand", "autoreplace", "autotrim", "listsnapshots"):
                try:
                    if hasattr(p, "get_prop"):
                        extras[prop] = str(self._safe_prop_value(p.get_prop(prop)))
                except Exception:
                    pass
            return ok({
                "name": p.name,
                "state": str(getattr(p, "state", "")),
                "health": str(getattr(p, "health", "")),
                "guid": str(getattr(p, "guid", "")),
                "props": extras
            })
        except Exception as exc:
            return fail(str(exc))

    def pool_status_verbose(self, pool: str) -> Dict[str, Any]:
        """Return raw output of `zpool status -v <pool>`."""
        # FA: خروجی کامل برای عیب‌یابی دقیق؛ برای پارس بعدی ذخیره کنید.
        # EN: Full verbose status; store/parse downstream as needed.
        try:
            out, _ = self._run(["zpool", "status", "-v", pool])
            return ok({"raw": out})
        except Exception as exc:
            return fail(str(exc))

    def pool_iostat(self, pool: Optional[str] = None, samples: int = 1, interval: int = 1) -> Dict[str, Any]:
        """Return raw output of `zpool iostat -v` (optionally for one pool)."""
        # FA: نمونه‌ای از آمار I/O برای تحلیل لحظه‌ای.
        # EN: One-shot I/O stats snapshot for quick visibility.
        try:
            args = ["zpool", "iostat", "-v"]
            if pool:
                args.append(pool)
            args += [str(samples), str(interval)]
            out, _ = self._run(args)
            return ok({"raw": out})
        except Exception as exc:
            return fail(str(exc))

    def list_datasets(self, pool: Optional[str] = None,
                      types: Iterable[str] = ("filesystem", "volume", "snapshot")) -> Dict[str, Any]:
        """List datasets with type."""
        # FA: لیست دیتاست‌ها (fs/zvol/snapshot) به‌صورت ساده.
        # EN: List datasets filtered by type (fs/zvol/snapshot).
        try:
            args = ["zfs", "list", "-H", "-o", "name,type", "-t", ",".join(types), "-r"]
            if pool:
                args.append(pool)
            out, _ = self._run(args)
            items: List[Dict[str, str]] = []
            for line in out.splitlines():
                if not line.strip():
                    continue
                name_i, type_i = line.split("\t")
                if pool is None or name_i.split("/")[0] == pool:
                    items.append({"name": name_i, "type": type_i})
            return ok(items)
        except Exception as exc:
            return fail(str(exc))

    def get_props(self, target: str) -> Dict[str, Any]:
        """Return all visible properties of a dataset as a dict."""
        # FA: دریافت همهٔ propertyها؛ ابتدا libzfs سپس CLI.
        # EN: Fetch all properties; try libzfs then fallback to CLI.
        try:
            try:
                ds = self._get_dataset(target)
                result: Dict[str, Any] = {}
                if hasattr(ds, "properties"):
                    for k, v in ds.properties.items():
                        result[k] = str(self._safe_prop_value(v))
                    return ok(result)
            except ZFSError:
                pass
            out, _ = self._run(["zfs", "get", "-H", "-o", "property,value", "all", target])
            props: Dict[str, Any] = {}
            for line in out.splitlines():
                if not line.strip():
                    continue
                k, v = line.split("\t")
                props[k] = v
            return ok(props)
        except Exception as exc:
            return fail(str(exc))

    # --------------------------- pool operations ---------------------------

    def create_pool(self, name: str, vdevs: List[List[str]],
                    properties: Optional[Dict[str, str]] = None,
                    force: bool = False, altroot: Optional[str] = None,
                    ashift: Optional[int] = None) -> Dict[str, Any]:
        """Create a zpool using CLI (safe arg building)."""
        # FA: ساخت zpool با گروه‌های vdev؛ از -o ها و گزینه‌ها پشتیبانی می‌شود.
        # EN: Create zpool with vdev groups; supports -o properties and options.
        try:
            args = ["zpool", "create"]
            if force:
                args.append("-f")
            if altroot:
                args += ["-R", altroot]
            if ashift is not None:
                args += ["-o", f"ashift={ashift}"]
            if properties:
                for k, v in properties.items():
                    args += ["-o", f"{k}={v}"]
            args.append(name)
            for grp in vdevs:
                args += grp
            out, _ = self._run(args)
            return ok({"created": True, "pool": name, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def destroy_pool(self, name: str, force: bool = False) -> Dict[str, Any]:
        """Destroy a zpool."""
        # FA: حذف کامل zpool؛ با احتیاط استفاده شود.
        # EN: Destroy zpool; dangerous—use carefully.
        try:
            args = ["zpool", "destroy"]
            if force:
                args.append("-f")
            args.append(name)
            out, _ = self._run(args)
            return ok({"destroyed": True, "pool": name, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def import_pool(self, name: Optional[str] = None,
                    dir_hint: Optional[str] = None, readonly: bool = False) -> Dict[str, Any]:
        """Import a zpool (optionally read-only)."""
        # FA: ایمپورت یک zpool از مسیر خاص یا حالت فقط‌خواندنی.
        # EN: Import a zpool from a search dir or as read-only.
        try:
            args = ["zpool", "import"]
            if dir_hint:
                args += ["-d", dir_hint]
            if readonly:
                args += ["-o", "readonly=on"]
            if name:
                args.append(name)
            out, _ = self._run(args)
            return ok({"imported": True, "pool": name, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def export_pool(self, name: str, force: bool = False) -> Dict[str, Any]:
        """Export a zpool."""
        # FA: خروج یک zpool برای انتقال به سیستم دیگر.
        # EN: Export a zpool to move/use on another system.
        try:
            args = ["zpool", "export"]
            if force:
                args.append("-f")
            args.append(name)
            out, _ = self._run(args)
            return ok({"exported": True, "pool": name, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def scrub_pool(self, name: str, stop: bool = False) -> Dict[str, Any]:
        """Start or stop a scrub."""
        # FA: شروع یا توقف scrub برای بررسی و ترمیم خطاهای silent.
        # EN: Start/stop scrub to detect/correct silent errors.
        try:
            args = ["zpool", "scrub"]
            if stop:
                args.append("-s")
            args.append(name)
            out, _ = self._run(args)
            return ok({"scrub": "stopped" if stop else "started", "pool": name, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def clear_pool(self, name: str, device: Optional[str] = None) -> Dict[str, Any]:
        """Clear error counters on a pool/device."""
        # FA: پاک‌سازی شمارنده‌های خطا در کل pool یا یک دیسک خاص.
        # EN: Clear error counters for pool or a specific device.
        try:
            args = ["zpool", "clear", name]
            if device:
                args.append(device)
            out, _ = self._run(args)
            return ok({"cleared": True, "pool": name, "device": device, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def features(self, pool: str) -> Dict[str, Any]:
        """List feature@* flags for a pool."""
        # FA: ویژگی‌های فعال/غیرفعال شدهٔ pool را از zpool get استخراج می‌کنیم.
        # EN: Extract feature flags from `zpool get`.
        try:
            out, _ = self._run(["zpool", "get", "-H", "-o", "name,property,value,source", "all", pool])
            rows: List[Dict[str, str]] = []
            for ln in out.splitlines():
                if not ln.strip():
                    continue
                name, prop, value, source = ln.split("\t")
                if prop.startswith("feature@"):
                    rows.append({"property": prop, "value": value, "source": source})
            return ok(rows)
        except Exception as exc:
            return fail(str(exc))

    # --------------------------- dataset operations ---------------------------

    def create_dataset(self, name: str, properties: Optional[Dict[str, str]] = None,
                       dataset_type: str = "filesystem") -> Dict[str, Any]:
        """Create a filesystem or a zvol (volume)."""
        # FA: ساخت filesystem یا zvol؛ برای zvol باید volsize تعیین شود.
        # EN: Create filesystem or zvol; zvol requires 'volsize'.
        try:
            args = ["zfs", "create", "-p"]
            if dataset_type == "volume":
                if not properties or "volsize" not in properties:
                    return fail("Creating a volume requires 'volsize' property.", code="invalid_request")
            if properties:
                for k, v in properties.items():
                    args += ["-o", f"{k}={v}"]
            args.append(name)
            out, _ = self._run(args)
            return ok({"created": True, "dataset": name, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def destroy_dataset(self, name: str, recursive: bool = False, force: bool = False) -> Dict[str, Any]:
        """Destroy a dataset (optionally recursive/force)."""
        # FA: حذف dataset با انتخاب حذف بازگشتی یا اجباری.
        # EN: Destroy dataset with optional recursive/force flags.
        try:
            args = ["zfs", "destroy"]
            if recursive:
                args.append("-r")
            if force:
                args.append("-f")
            args.append(name)
            out, _ = self._run(args)
            return ok({"destroyed": True, "dataset": name, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def set_props(self, target: str, properties: Dict[str, str]) -> Dict[str, Any]:
        """Set properties on a dataset (attempt libzfs, fallback CLI)."""
        # FA: تلاش برای ست‌کردن property با libزfs؛ درصورت نیاز با CLI.
        # EN: Set properties via libzfs when possible; fallback to CLI.
        try:
            ds = self._get_dataset(target)
            changed: Dict[str, str] = {}
            for k, v in properties.items():
                try:
                    if hasattr(ds, "set_property"):
                        ds.set_property(k, v)
                        changed[k] = str(v)
                    else:
                        out, _ = self._run(["zfs", "set", f"{k}={v}", target])
                        changed[k] = str(v)
                except Exception as inner:
                    return fail(f"Failed to set {k}: {inner}")
            return ok({"target": target, "changed": changed})
        except Exception:
            try:
                changed: Dict[str, str] = {}
                for k, v in properties.items():
                    out, _ = self._run(["zfs", "set", f"{k}={v}", target])
                    changed[k] = str(v)
                return ok({"target": target, "changed": changed, "method": "cli_fallback"})
            except Exception as exc2:
                return fail(str(exc2))

    def snapshot(self, name: str, recursive: bool = False, props: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create a snapshot <dataset>@<snap>."""
        # FA: ایجاد snapshot برای نسخه‌برداری سریع.
        # EN: Create snapshot for point-in-time copy.
        try:
            args = ["zfs", "snapshot"]
            if recursive:
                args.append("-r")
            if props:
                for k, v in props.items():
                    args += ["-o", f"{k}={v}"]
            args.append(name)
            out, _ = self._run(args)
            return ok({"snapshot": name, "created": True, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def list_snapshots(self, dataset: Optional[str] = None) -> Dict[str, Any]:
        """List snapshots (name, creation, used, refer)."""
        # FA: فهرست snapshotها با چند فیلد کاربردی.
        # EN: Return snapshots with a few useful columns.
        try:
            target = dataset or ""
            out, _ = self._run(["zfs", "list", "-H", "-o", "name,creation,used,refer", "-t", "snapshot", "-r", target])
            snaps: List[Dict[str, str]] = []
            for ln in out.splitlines():
                if not ln.strip():
                    continue
                name, creation, used, refer = ln.split("\t")
                snaps.append({"name": name, "creation": creation, "used": used, "refer": refer})
            return ok(snaps)
        except Exception as exc:
            return fail(str(exc))

    def bookmark(self, snapshot: str, bookmark: str) -> Dict[str, Any]:
        """Create a bookmark from a snapshot."""
        # FA: بوکمارک سبک‌تر از snapshot است و برای replication مناسب است.
        # EN: Bookmark is a lightweight snapshot pointer, handy for replication.
        try:
            out, _ = self._run(["zfs", "bookmark", snapshot, bookmark])
            return ok({"bookmark": bookmark, "from_snapshot": snapshot, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def list_bookmarks(self, dataset: Optional[str] = None) -> Dict[str, Any]:
        """List bookmarks under dataset (or all)."""
        # FA: لیست نام بوکمارک‌ها برای مدیریت و پاک‌سازی.
        # EN: List bookmark names for management/cleanup.
        try:
            args = ["zfs", "list", "-H", "-o", "name", "-t", "bookmark"]
            if dataset:
                args += ["-r", dataset]
            out, _ = self._run(args)
            items = [ln.strip() for ln in out.splitlines() if ln.strip()]
            return ok(items)
        except Exception as exc:
            return fail(str(exc))

    def clone(self, snapshot: str, target: str, properties: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Clone a snapshot into a new dataset."""
        # FA: ایجاد کلون سریع از snapshot برای تست یا شاخهٔ داده.
        # EN: Fast clone from snapshot for testing/branching.
        try:
            args = ["zfs", "clone"]
            if properties:
                for k, v in properties.items():
                    args += ["-o", f"{k}={v}"]
            args += [snapshot, target]
            out, _ = self._run(args)
            return ok({"cloned": True, "from": snapshot, "to": target, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def promote(self, dataset: str) -> Dict[str, Any]:
        """Promote a clone to a normal dataset."""
        # FA: قطع وابستگی کلون از والد با promote.
        # EN: Break clone dependency via promote.
        try:
            out, _ = self._run(["zfs", "promote", dataset])
            return ok({"promoted": dataset, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def rename(self, src: str, dst: str, recursive: bool = False) -> Dict[str, Any]:
        """Rename a dataset (optionally recursive)."""
        # FA: تغییر نام دیتاست با امکان بازگشتی.
        # EN: Rename dataset with optional recursion.
        try:
            args = ["zfs", "rename"]
            if recursive:
                args.append("-r")
            args += [src, dst]
            out, _ = self._run(args)
            return ok({"renamed": True, "src": src, "dst": dst, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def rollback(self, dataset: str, to_snapshot: Optional[str] = None,
                 destroy_more_recent: bool = False) -> Dict[str, Any]:
        """Rollback dataset to a snapshot."""
        # FA: بازگشت به snapshot مشخص یا آخرین snapshot.
        # EN: Rollback to a specific or latest snapshot.
        try:
            args = ["zfs", "rollback"]
            if destroy_more_recent:
                args.append("-r")
            if to_snapshot:
                args.append(f"{dataset}@{to_snapshot}" if "@" not in to_snapshot else to_snapshot)
            else:
                args.append(dataset)
            out, _ = self._run(args)
            return ok({"rolled_back": dataset, "to": to_snapshot or "latest", "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def mount(self, dataset: str) -> Dict[str, Any]:
        """Mount a filesystem dataset."""
        # FA: سوارکردن دیتاست در mountpoint تعریف‌شده.
        # EN: Mount dataset at its defined mountpoint.
        try:
            out, _ = self._run(["zfs", "mount", dataset])
            return ok({"mounted": dataset, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def unmount(self, dataset: str, force: bool = False) -> Dict[str, Any]:
        """Unmount a dataset."""
        # FA: پیاده‌کردن دیتاست؛ در صورت نیاز با force.
        # EN: Unmount dataset; can force if needed.
        try:
            args = ["zfs", "unmount"]
            if force:
                args.append("-f")
            args.append(dataset)
            out, _ = self._run(args)
            return ok({"unmounted": dataset, "force": force, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    # --------------------------- quotas & space ---------------------------

    def set_quota(self, dataset: str, size: str) -> Dict[str, Any]:
        """Set dataset quota (e.g., '100G' or 'none')."""
        # FA: تعیین quota برای محدودیت فضای قابل‌دید کاربر.
        # EN: Set user-visible quota limit.
        return self.set_props(dataset, {"quota": size})

    def set_refquota(self, dataset: str, size: str) -> Dict[str, Any]:
        """Set referenced quota."""
        # FA: محدودیت فضا بر اساس فضای referenced.
        # EN: Quota based on referenced space.
        return self.set_props(dataset, {"refquota": size})

    def set_reservation(self, dataset: str, size: str) -> Dict[str, Any]:
        """Set reservation."""
        # FA: رزروکردن فضا به‌صورت تضمین‌شده.
        # EN: Guarantee space via reservation.
        return self.set_props(dataset, {"reservation": size})

    def set_refreservation(self, dataset: str, size: str) -> Dict[str, Any]:
        """Set referenced reservation."""
        # FA: رزرو بر اساس referenced space.
        # EN: Referenced-space reservation.
        return self.set_props(dataset, {"refreservation": size})

    def list_user_quotas(self, dataset: str) -> Dict[str, Any]:
        """List user/group space and quotas."""
        # FA: نمایش quota کاربر و گروه برای مدیریت سهمیه‌ها.
        # EN: Show user/group space usage and quotas.
        try:
            out_u, _ = self._run(["zfs", "userspace", "-H", "-o", "name,used,quota", dataset])
            out_g, _ = self._run(["zfs", "groupspace", -H", " - o", "name, used, quota", dataset])
        except Exception as exc:
            return fail(str(exc))
        try:
            def parse(txt: str) -> List[Dict[str, str]]:
                rows: List[Dict[str, str]] = []
                for ln in txt.splitlines():
                    if not ln.strip():
                        continue
                    n, u, q = ln.split("\t")
                    rows.append({"name": n, "used": u, "quota": q})
                return rows

            return ok({"users": parse(out_u), "groups": parse(out_g)})
        except Exception as exc:
            return fail(str(exc))

    # --------------------------- tuning ---------------------------

    def enable_compression(self, dataset: str, algo: str = "lz4") -> Dict[str, Any]:
        """Enable compression (lz4/zstd/gzip/off)."""
        # FA: فعال‌سازی فشرده‌سازی با الگوریتم دلخواه.
        # EN: Turn on compression with desired algorithm.
        return self.set_props(dataset, {"compression": algo})

    def enable_dedup(self, dataset: str, mode: str = "on") -> Dict[str, Any]:
        """Enable deduplication (on/verify/off)."""
        # FA: فعال‌سازی dedup برای کاهش مصرف فضا.
        # EN: Enable deduplication to reduce space usage.
        return self.set_props(dataset, {"dedup": mode})

    def set_record_or_volblock(self, dataset: str, size: str = "128K") -> Dict[str, Any]:
        """Set recordsize or volblocksize depending on dataset type."""
        # FA: اگر zvol باشد volblocksize وگرنه recordsize را ست می‌کنیم.
        # EN: Use volblocksize for zvol else recordsize for filesystem.
        props = self.get_props(dataset)
        if not props["ok"]:
            return props
        p = props["data"]
        if p.get("type") == "volume" or "volblocksize" in p:
            return self.set_props(dataset, {"volblocksize": size})
        return self.set_props(dataset, {"recordsize": size})

    def set_mountpoint(self, dataset: str, path: str) -> Dict[str, Any]:
        """Set mountpoint for a filesystem dataset."""
        # FA: تعیین مسیر mountpoint دیتاست.
        # EN: Set dataset's mountpoint path.
        return self.set_props(dataset, {"mountpoint": path})

    def set_atime(self, dataset: str, mode: str = "off") -> Dict[str, Any]:
        """Toggle atime (on/off)."""
        # FA: خاموش/روشن کردن atime برای کاهش I/O.
        # EN: Toggle atime to reduce extra writes.
        return self.set_props(dataset, {"atime": mode})

    # --------------------------- send / receive ---------------------------

    def send(self, snapshot: str, incremental_from: Optional[str] = None, raw: bool = False,
             compressed: bool = True, resume_token: Optional[str] = None,
             output_file: Optional[str] = None) -> Dict[str, Any]:
        """Generate a send stream (prefer writing to file for large streams)."""
        # FA: تولید استریم برای replication؛ پیشنهاد می‌شود به فایل نوشته شود.
        # EN: Produce replication stream; prefer writing to a file.
        try:
            args = ["zfs", "send"]
            if raw:
                args.append("--raw")
            if compressed:
                args.append("-c")
            if resume_token:
                args += ["-t", resume_token]
            elif incremental_from:
                args += ["-I", incremental_from]
            args.append(snapshot)

            if self.dry_run:
                return ok({"stdout": " ".join(args), "dry_run": True})

            if output_file:
                with open(output_file, "wb") as f:
                    proc = subprocess.Popen(args, stdout=f, stderr=subprocess.PIPE)
                    _, err = proc.communicate(timeout=self.run_timeout)
                    if proc.returncode != 0:
                        raise ZFSError(err.decode(errors="ignore"))
                return ok({"snapshot": snapshot, "output_file": output_file})
            else:
                proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, err = proc.communicate(timeout=self.run_timeout)
                if proc.returncode != 0:
                    raise ZFSError(err.decode(errors="ignore"))
                return ok({"snapshot": snapshot, "stream_size": len(out)})
        except Exception as exc:
            return fail(str(exc))

    def receive(self, target: str, input_file: Optional[str] = None, stdin_bytes: Optional[bytes] = None,
                force: bool = False, nomount: bool = False, verbose: bool = False) -> Dict[str, Any]:
        """Receive a send stream into target dataset."""
        # FA: دریافت استریم روی مقصد؛ از فایل یا stdin.
        # EN: Receive stream into target; from file or stdin.
        try:
            if input_file and stdin_bytes:
                return fail("Provide either input_file or stdin_bytes, not both.", code="invalid_request")
            args = ["zfs", "receive"]
            if force:
                args.append("-F")
            if nomount:
                args.append("-u")
            if verbose:
                args.append("-v")
            args.append(target)

            if input_file:
                with open(input_file, "rb") as f:
                    data = f.read()
                out, _ = self._run(args, stdin=data)
                return ok({"received": True, "target": target, "from": input_file, "stdout": out})
            else:
                out, _ = self._run(args, stdin=stdin_bytes)
                return ok({"received": True, "target": target, "stdin_bytes": stdin_bytes is not None, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    # --------------------------- diagnostics ---------------------------

    def diff(self, older: str, newer: str) -> Dict[str, Any]:
        """Return `zfs diff` output between two points."""
        # FA: مقایسه تغییرات بین دو snapshot/dataset.
        # EN: Compare changes between two snapshots/datasets.
        try:
            out, _ = self._run(["zfs", "diff", older, newer])
            return ok({"raw": out, "lines": [ln for ln in out.splitlines()]})
        except Exception as exc:
            return fail(str(exc))

    def history(self, dataset_or_pool: Optional[str] = None) -> Dict[str, Any]:
        """Return ZFS command history for a pool/dataset or global."""
        # FA: تاریخچه عملیات برای بررسی تغییرات.
        # EN: Operation history to audit changes.
        try:
            if dataset_or_pool:
                try:
                    out, _ = self._run(["zpool", "history", dataset_or_pool])
                    return ok({"scope": "pool", "name": dataset_or_pool, "raw": out})
                except ZFSError:
                    out, _ = self._run(["zfs", "history", dataset_or_pool])
                    return ok({"scope": "dataset", "name": dataset_or_pool, "raw": out})
            out, _ = self._run(["zfs", "history"])
            return ok({"scope": "global", "raw": out})
        except Exception as exc:
            return fail(str(exc))

    # --------------------------- comprehensive export ---------------------------

    def export_full_state(self) -> Dict[str, Any]:
        """
        Return a deep, JSON-serializable inventory:
          - pools (status, features, iostat, status -v)
          - datasets under each pool (props, snapshots, bookmarks)
          - global snapshots summary
        """
        # FA: جمع‌آوری نمای کامل وضعیت سیستم فایل ZFS برای داشبورد/مانیتورینگ.
        # EN: Build a comprehensive JSON view for dashboards/monitoring.
        try:
            full: Dict[str, Any] = {"pools": []}

            for p in self.zfs.pools:
                pool_entry: Dict[str, Any] = {
                    "name": p.name,
                    "guid": str(getattr(p, "guid", "")),
                    "state": str(getattr(p, "state", "")),
                    "health": str(getattr(p, "health", "")),
                    "props": {},
                    "features": [],
                    "status_verbose": None,
                    "iostat": None,
                    "datasets": [],
                }

                # pool props
                for prop in ("ashift", "autoexpand", "autoreplace", "autotrim", "comment", "cachefile"):
                    try:
                        if hasattr(p, "get_prop"):
                            pool_entry["props"][prop] = str(self._safe_prop_value(p.get_prop(prop)))
                    except Exception:
                        pass

                # features
                try:
                    feat = self.features(p.name)
                    if feat["ok"]:
                        pool_entry["features"] = feat["data"]
                except Exception:
                    pass

                # status -v
                try:
                    stv = self.pool_status_verbose(p.name)
                    if stv["ok"]:
                        pool_entry["status_verbose"] = stv["data"]["raw"]
                except Exception:
                    pass

                # iostat
                try:
                    io = self.pool_iostat(p.name, samples=1, interval=1)
                    if io["ok"]:
                        pool_entry["iostat"] = io["data"]["raw"]
                except Exception:
                    pass

                # datasets in pool
                try:
                    ds_list = self.list_datasets(pool=p.name, types=("filesystem", "volume"))
                    if ds_list["ok"]:
                        for item in ds_list["data"]:
                            ds_name = item["name"]
                            ds_entry: Dict[str, Any] = {
                                "name": ds_name,
                                "type": item["type"],
                                "props": {},
                                "snapshots": [],
                                "bookmarks": [],
                            }
                            gp = self.get_props(ds_name)
                            if gp["ok"]:
                                ds_entry["props"] = gp["data"]
                            snaps = self.list_snapshots(ds_name)
                            if snaps["ok"]:
                                ds_entry["snapshots"] = snaps["data"]
                            bms = self.list_bookmarks(ds_name)
                            if bms["ok"]:
                                ds_entry["bookmarks"] = bms["data"]
                            pool_entry["datasets"].append(ds_entry)
                except Exception:
                    pass

                full["pools"].append(pool_entry)

            # global snapshots
            try:
                all_snaps = self.list_snapshots()
                if all_snaps["ok"]:
                    full["all_snapshots"] = all_snaps["data"]
            except Exception:
                full["all_snapshots"] = []

            return ok(full, meta={"source": "libzfs+cli"})
        except Exception as exc:
            return fail(str(exc))


__all__ = ["ZFSManager", "ZFSError", "ok", "fail"]
