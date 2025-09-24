# zpool.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ماژول zpool: کلاس ZPoolManager برای مدیریت زِدپول‌ها (zpool).
این کلاس وظایف مربوط به introspection (خواندن اطلاعات) پول‌ها را
با استفاده از libzfs انجام می‌دهد و متدهایی برای حذف/ویرایش/فهرست کردن دارد.

Important notes (inline comments are English). Docstrings (Persian) explain inputs/outputs.
"""

from typing import Dict, List, Optional, Any, Tuple
import libzfs  # official binding required
import subprocess
import shlex
import datetime

# JSON envelope helpers (same pattern as before)
def ok(data: Any, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return success envelope (DRF-friendly)."""
    return {"ok": True, "error": None, "data": data, "meta": meta or {}}

def fail(message: str, code: str = "zpool_error", extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return failure envelope (DRF-friendly)."""
    return {"ok": False, "error": {"code": code, "message": message, "extra": extra or {}}, "data": None, "meta": {}}


class ZPoolManager:
    """
    کلاس ZPoolManager برای مدیریت و خواندن اطلاعات zpool ها.

    ورودی سازنده:
      - dry_run (bool): اگر True باشد، تغییرات اجرایی (create/destroy/edit) اجرا نمی‌شوند و صرفاً پیش‌نمایش بازگردانده می‌شود.
      - run_timeout (int): timeout برای اجرای fallback CLI در صورت نیاز (ثانیه).

    امکانات:
      - تعریف گسترده‌ای از پارامترهای pool به‌عنوان attribute کلاس با مقدار پیش‌فرض.
      - متدی برای بازگرداندن لیست نام pool ها.
      - متدی برای بازگرداندن کلیه‌ی پارامترها/آمار یک pool (با استفاده از libzfs).
      - متدی برای بازگرداندن جمع‌بندی dataset های داخل pool شامل: name, type, total, used, allocated, free, remaining.
      - متد حذف پول، ادیت پول (set properties)، لیست دیسک‌ها و فقط نام دیسک‌ها.
      - بیشتر خواندن‌ها با libzfs انجام می‌شود؛ عملیات تغییر در صورت عدم پشتیبانی binding مستقیماً با CLI اجرا خواهد شد.
    """

    # Class-level default properties (these are typical zpool-level properties)
    autoexpand: Optional[str] = None        # Possible: "on", "off"
    autoreplace: Optional[str] = None       # Possible: "on", "off"
    autotrim: Optional[str] = None          # Possible: "on", "off"
    listsnapshots: Optional[str] = None     # Possible: "on", "off"
    cachefile: Optional[str] = None         # Possible: "/etc/zfs/zpool.cache", "none"
    altroot: Optional[str] = None           # Possible: "/mnt", None
    ashift: Optional[int] = None            # Possible: 9, 12, 13,... (ashift = 2^n)
    comment: Optional[str] = None           # free text
    failmode: Optional[str] = None          # Possible: "wait","continue","panic"
    feature_flags: Optional[Dict[str,str]] = None  # feature@... -> state
    # Additional attributes can be added here as needed

    def __init__(self, dry_run: bool = False, run_timeout: int = 120) -> None:
        """
        سازندهٔ ZPoolManager.
        ورودی:
          - dry_run: اگر True باشد تغییر حالت‌ها اجرا نخواهند شد.
          - run_timeout: timeout برای اجرای fallback CLI.
        خروجی:
          - None
        """
        self.zfs = libzfs.ZFS()  # main libzfs instance  # English inline comment
        self.dry_run = dry_run  # whether to actually execute mutating ops
        self.run_timeout = run_timeout  # subprocess timeout for CLI fallback
        # instance snapshot of pools for quick repeated reads (optional)
        self._last_refreshed: Optional[datetime.datetime] = None  # last refresh time
        self._pool_cache: Dict[str, Any] = {}  # cache of pool introspection results

    # -------------------- internal helpers --------------------

    def _refresh_cache_if_needed(self, ttl_seconds: int = 5) -> None:
        """Refresh internal pool cache if stale (uses libzfs)."""
        now = datetime.datetime.utcnow()
        if self._last_refreshed and (now - self._last_refreshed).total_seconds() < ttl_seconds:
            return
        self._pool_cache = {}
        for pool in self.zfs.pools:  # iterate libzfs pools
            self._pool_cache[pool.name] = pool
        self._last_refreshed = now

    def _safe_prop(self, val: Any) -> Any:
        """Normalize libzfs property object to plain value."""
        return getattr(val, "value", val)

    def _run_cli(self, args: List[str]) -> Tuple[str,str]:
        """Fallback CLI runner (safe, no shell)."""
        cmd_str = " ".join(shlex.quote(a) for a in args)
        if self.dry_run:
            return f"[DRY-RUN] {cmd_str}", ""
        proc = subprocess.run(args, capture_output=True, timeout=self.run_timeout, check=False)
        return proc.stdout.decode(errors="ignore"), proc.stderr.decode(errors="ignore")

    # -------------------- listing / discovery --------------------

    def list_pool_names(self) -> Dict[str, Any]:
        """
        لیست اسامی تمام zpool ها را بازمی‌گرداند.

        خروجی:
          - dict: {"ok": True, "data": ["pool1","pool2",...], ...}
        """
        try:
            self._refresh_cache_if_needed()
            names = list(self._pool_cache.keys())  # get pool names
            return ok(names)
        except Exception as exc:
            return fail(str(exc))

    def get_pool(self, pool_name: str) -> Dict[str, Any]:
        """
        تمام اطلاعات و پارامترهای یک pool را بازمی‌گرداند (props, size totals, health, vdev devices, features).
        ورودی:
          - pool_name (str): نام پول
        خروجی:
          - dict: comprehensive pool info in 'data' on success
        """
        try:
            self._refresh_cache_if_needed()
            pool = self._pool_cache.get(pool_name)
            if pool is None:
                # try to load again
                for p in self.zfs.pools:
                    if p.name == pool_name:
                        pool = p
                        break
            if pool is None:
                return fail(f"Pool not found: {pool_name}", code="not_found")
            # basic attributes
            pool_info: Dict[str, Any] = {}
            pool_info["name"] = pool.name
            pool_info["guid"] = str(getattr(pool, "guid", None))
            pool_info["state"] = str(getattr(pool, "state", None))
            pool_info["health"] = str(getattr(pool, "health", None))
            # properties via libzfs if available
            props: Dict[str, Any] = {}
            try:
                for k, v in getattr(pool, "properties", {}).items():
                    props[k] = str(self._safe_prop(v))
            except Exception:
                pass
            pool_info["props"] = props
            # size summary (attempt to use libzfs pool space attributes)
            try:
                # some libzfs bindings expose space stats on pool (allocated, size, free)
                total = getattr(pool, "size", None) or props.get("size") or props.get("available")
                pool_info["raw_props"] = {
                    "size": props.get("size"),
                    "allocated": props.get("allocated"),
                    "free": props.get("free")
                }
            except Exception:
                pool_info["raw_props"] = {}
            # vdevs and devices
            devices = []
            try:
                # libzfs pool.topology maybe available
                topo = getattr(pool, "topology", None)
                if topo:
                    for tname, tlist in topo.items():
                        for v in tlist:
                            devices.append({"type": tname, "device": getattr(v, "name", None), "state": getattr(v, "state", None)})
            except Exception:
                pass
            # fallback: try pool.vdevs or pool.devices
            try:
                if not devices:
                    for v in getattr(pool, "vdevs", []) or getattr(pool, "devices", []):
                        devices.append({"device": getattr(v, "name", None), "path": getattr(v, "path", None), "state": getattr(v, "state", None)})
            except Exception:
                pass
            pool_info["devices"] = devices
            # features
            feats = {}
            try:
                for k, v in getattr(pool, "features", {}).items():
                    feats[k] = str(self._safe_prop(v))
            except Exception:
                pass
            pool_info["features"] = feats
            return ok(pool_info)
        except Exception as exc:
            return fail(str(exc))

    # -------------------- pool -> dataset summary --------------------

    def datasets_summary_for_pool(self, pool_name: str) -> Dict[str, Any]:
        """
        For a given pool, return summary list of datasets inside it.
        Each entry: {name, type, referenced, used, available, used_percent}
        ورودی:
          - pool_name (str)
        خروجی:
          - dict: {"data": [ ... ] }
        """
        try:
            # use libzfs to iterate datasets and filter by pool prefix
            items = []
            for ds in self.zfs.datasets:  # libzfs datasets iterator
                # ds.name like "pool/dataset..."
                if not ds.name.startswith(pool_name + "/") and ds.name != pool_name:
                    continue
                typ = getattr(ds, "type", None)
                # many bindings expose properties on dataset
                props = {}
                try:
                    for k, v in getattr(ds, "properties", {}).items():
                        props[k] = str(self._safe_prop(v))
                except Exception:
                    pass
                # build numeric-ish fields where possible
                referenced = props.get("referenced") or props.get("used") or None
                used = props.get("used") or None
                available = props.get("available") or None
                try:
                    # try to calculate percent if numeric - keep as string-safe
                    used_percent = props.get("used") and props.get("referenced") and None
                except Exception:
                    used_percent = None
                items.append({
                    "name": ds.name,
                    "type": typ,
                    "props": props,
                    "referenced": referenced,
                    "used": used,
                    "available": available,
                    "used_percent": used_percent
                })
            return ok(items)
        except Exception as exc:
            return fail(str(exc))

    # -------------------- mutating operations --------------------

    def destroy_pool(self, pool_name: str, force: bool = False) -> Dict[str, Any]:
        """
        Destroy a zpool. This method will attempt to use libzfs's API if available;
        if the binding does not provide destroy, it falls back to invoking 'zpool destroy'.
        ورودی:
          - pool_name (str)
          - force (bool)
        خروجی:
          - dict envelope
        """
        try:
            # try libzfs API first (if available)
            try:
                pool = next((p for p in self.zfs.pools if p.name == pool_name), None)
                if pool is not None and hasattr(self.zfs, "destroy_pool"):
                    # some bindings may have destroy_pool (not guaranteed)
                    self.zfs.destroy_pool(pool_name, force=force)  # type: ignore
                    return ok({"destroyed": True, "pool": pool_name})
            except Exception:
                pass
            # fallback to CLI
            args = ["zpool", "destroy"]
            if force:
                args.append("-f")
            args.append(pool_name)
            out, err = self._run_cli(args)
            if err:
                return fail("CLI destroy error", extra={"stderr": err})
            return ok({"destroyed": True, "pool": pool_name, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def edit_pool_props(self, pool_name: str, properties: Dict[str,str]) -> Dict[str, Any]:
        """
        Edit pool-level properties. Prefer libzfs when possible; otherwise fallback to CLI.
        ورودی:
          - pool_name (str)
          - properties (dict): key->value mapping
        خروجی:
          - dict envelope with changed properties.
        """
        try:
            pool = next((p for p in self.zfs.pools if p.name == pool_name), None)
            changed = {}
            if pool is not None and hasattr(pool, "set_prop"):
                # attempt to set via libzfs pool API
                for k, v in properties.items():
                    try:
                        pool.set_prop(k, v)  # type: ignore
                        changed[k] = v
                    except Exception:
                        # ignore and try CLI later for that prop
                        pass
            # for any remaining properties, use 'zpool set' via CLI
            remaining = {k:v for k,v in properties.items() if k not in changed}
            if remaining:
                for k, v in remaining.items():
                    args = ["zpool", "set", f"{k}={v}", pool_name]
                    out, err = self._run_cli(args)
                    if err:
                        return fail(f"Failed to set {k} via CLI", extra={"stderr": err})
                    changed[k] = v
            return ok({"pool": pool_name, "changed": changed})
        except Exception as exc:
            return fail(str(exc))

    def list_pool_devices(self, pool_name: str) -> Dict[str, Any]:
        """
        Return detailed device records used by the pool (type, name, path, state).
        ورودی:
          - pool_name (str)
        خروجی:
          - dict: list of devices
        """
        try:
            pool = next((p for p in self.zfs.pools if p.name == pool_name), None)
            if pool is None:
                return fail("Pool not found", code="not_found")
            devices = []
            try:
                topo = getattr(pool, "topology", None)
                if topo:
                    for t, l in topo.items():
                        for v in l:
                            devices.append({"vdev_type": t, "name": getattr(v, "name", None), "path": getattr(v, "path", None), "state": getattr(v, "state", None)})
                else:
                    # try devices attribute
                    for v in getattr(pool, "vdevs", []) or getattr(pool, "devices", []):
                        devices.append({"name": getattr(v, "name", None), "path": getattr(v, "path", None), "state": getattr(v, "state", None)})
            except Exception:
                pass
            return ok(devices)
        except Exception as exc:
            return fail(str(exc))

    def list_pool_device_names(self, pool_name: str) -> Dict[str, Any]:
        """
        Return only the device names (strings) used by the pool.
        ورودی:
          - pool_name (str)
        خروجی:
          - dict: list of device names
        """
        resp = self.list_pool_devices(pool_name)
        if not resp["ok"]:
            return resp
        names = []
        for d in resp["data"]:
            n = d.get("name") or d.get("path") or d.get("device")
            if n:
                names.append(n)
        return ok(names)

    # -------------------- additional helpers --------------------

    def refresh(self) -> Dict[str, Any]:
        """
        Force refresh of cached pool objects (libzfs datasets/pools).
        Useful after mutating operations to re-sync.
        """
        try:
            self._last_refreshed = None
            self._refresh_cache_if_needed(ttl_seconds=0)
            return ok({"refreshed": True})
        except Exception as exc:
            return fail(str(exc))


__all__ = ["ZPoolManager", "ok", "fail"]
