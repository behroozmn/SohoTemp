#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
zpool.py
========
High-level ZFS Pool management library using official libzfs Python bindings.
- Contains all zpool-level properties as class attributes with default values.
- No dataset creation/deletion/editing logic is inside this class (those belong in dataset manager).
- Provides methods to inspect pools, list pools, manage properties, show devices, and fetch dataset summaries.
- Designed for DRF-friendly JSON output.
"""

import libzfs
from typing import Any, Dict, List, Optional


def ok(data: Any) -> Dict[str, Any]:
    """Return a success envelope (DRF-ready)."""
    return {"ok": True, "error": None, "data": data, "meta": {}}


def fail(message: str, code: str = "zpool_error", extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a failure envelope (DRF-ready)."""
    return {"ok": False, "error": {"code": code, "message": message, "extra": extra or {}}, "data": None, "meta": {}}


class ZPoolManager:
    """
    High-level manager for ZFS Pools (zpools).
    Attributes:
        ashift (int): default block size shift (commonly 12 → 4K) # possible: 9, 12, 13
        autoexpand (str): autoexpand pool # values: "on", "off"
        autoreplace (str): auto-replace failed devices # values: "on", "off"
        autotrim (str): trim SSDs automatically # values: "on", "off"
        cachefile (str): path to pool cache file or "none"
        comment (str): free-text comment
        readonly (str): pool readonly property # values: "on", "off"
        failmode (str): failure behavior # values: "wait", "continue", "panic"
        listsnapshots (str): include snapshots in listings # values: "on", "off"
        multihost (str): multihost protection for clusters # values: "on", "off"
    """

    # --- Default pool-level attributes with safe defaults ---
    ashift: int = 12  # possible: 9, 12, 13
    autoexpand: str = "off"  # values: on/off
    autoreplace: str = "off"  # values: on/off
    autotrim: str = "off"  # values: on/off
    cachefile: str = "none"  # path or "none"
    comment: str = ""  # free text
    readonly: str = "off"  # values: on/off
    failmode: str = "wait"  # values: wait/continue/panic
    listsnapshots: str = "off"  # values: on/off
    multihost: str = "off"  # values: on/off

    def __init__(self) -> None:
        """Initialize libzfs handle."""
        self.zfs = libzfs.ZFS()

    # -------------------- Pool Management Methods --------------------

    def list_pools(self) -> Dict[str, Any]:
        """
        List all pools available in the system.
        Returns:
            dict: success envelope with list of pool names
        """
        try:
            return ok([p.name for p in self.zfs.pools])
        except Exception as exc:
            return fail(str(exc))

    def pool_info(self, pool_name: str) -> Dict[str, Any]:
        """
        Get full information of a pool.
        Args:
            pool_name (str): name of the pool
        Returns:
            dict: envelope with pool details and properties
        """
        try:
            pool = next(p for p in self.zfs.pools if p.name == pool_name)
            props = {}
            for prop in (
                "ashift", "autoexpand", "autoreplace", "autotrim", "cachefile",
                "comment", "readonly", "failmode", "listsnapshots", "multihost"
            ):
                try:
                    props[prop] = str(pool.get_prop(prop))
                except Exception:
                    props[prop] = None
            return ok({
                "name": pool.name,
                "guid": str(pool.guid),
                "state": str(pool.state),
                "props": props
            })
        except StopIteration:
            return fail(f"Pool not found: {pool_name}")
        except Exception as exc:
            return fail(str(exc))

    def list_datasets_info(self, pool_name: str) -> Dict[str, Any]:
        """
        List summary of datasets inside a pool.
        Shows name, type, used, available, referenced.
        Args:
            pool_name (str): pool to inspect
        Returns:
            dict: envelope with dataset summary list
        """
        try:
            pool = next(p for p in self.zfs.pools if p.name == pool_name)
            datasets = []
            for ds in pool.root_dataset.children_recursive:
                datasets.append({
                    "name": ds.name,
                    "type": ds.type.name.lower(),
                    "used": str(ds.properties["used"].value),
                    "available": str(ds.properties["available"].value),
                    "referenced": str(ds.properties["referenced"].value),
                })
            return ok(datasets)
        except Exception as exc:
            return fail(str(exc))

    def delete_pool(self, pool_name: str) -> Dict[str, Any]:
        """
        Destroy a pool.
        Args:
            pool_name (str): pool to destroy
        Returns:
            dict: envelope with deletion result
        """
        try:
            pool = next(p for p in self.zfs.pools if p.name == pool_name)
            pool.destroy()
            return ok({"deleted": True, "pool": pool_name})
        except Exception as exc:
            return fail(str(exc))

    def edit_pool_prop(self, pool_name: str, prop: str, value: str) -> Dict[str, Any]:
        """
        Edit a pool property.
        Args:
            pool_name (str): pool to edit
            prop (str): property name
            value (str): new value
        Returns:
            dict: envelope with update confirmation
        """
        try:
            pool = next(p for p in self.zfs.pools if p.name == pool_name)
            pool.set_prop(prop, value)
            return ok({"edited": True, "pool": pool_name, "prop": prop, "value": value})
        except Exception as exc:
            return fail(str(exc))

    def list_pool_devices(self, pool_name: str) -> Dict[str, Any]:
        """
        Show detailed list of devices used in a pool.
        Args:
            pool_name (str): pool name
        Returns:
            dict: envelope with device details
        """
        try:
            pool = next(p for p in self.zfs.pools if p.name == pool_name)
            devs = []
            for vdev in pool.vdevs:
                devs.append({
                    "type": vdev.type,
                    "path": vdev.path,
                    "guid": str(vdev.guid),
                    "state": str(vdev.state),
                })
            return ok(devs)
        except Exception as exc:
            return fail(str(exc))

    def list_pool_device_names(self, pool_name: str) -> Dict[str, Any]:
        """
        Return only device names of a pool.
        Args:
            pool_name (str): pool name
        Returns:
            dict: envelope with list of device paths
        """
        try:
            pool = next(p for p in self.zfs.pools if p.name == pool_name)
            names = [vdev.path for vdev in pool.vdevs if vdev.path]
            return ok(names)
        except Exception as exc:
            return fail(str(exc))

    def pool_features(self, pool_name: str) -> Dict[str, Any]:
        """
        List feature@* properties for a pool.
        Args:
            pool_name (str): pool name
        Returns:
            dict: envelope with feature states
        """
        try:
            pool = next(p for p in self.zfs.pools if p.name == pool_name)
            features = {}
            for k, v in pool.properties.items():
                if k.startswith("feature@"):
                    features[k] = str(v.value)
            return ok(features)
        except Exception as exc:
            return fail(str(exc))

    def pool_capacity(self, pool_name: str) -> Dict[str, Any]:
        """
        Return capacity summary of a pool.
        Args:
            pool_name (str): pool name
        Returns:
            dict: envelope with size, allocated, free, capacity
        """
        try:
            pool = next(p for p in self.zfs.pools if p.name == pool_name)
            return ok({
                "size": str(pool.properties["size"].value),
                "allocated": str(pool.properties["allocated"].value),
                "free": str(pool.properties["free"].value),
                "capacity": str(pool.properties["capacity"].value),
            })
        except Exception as exc:
            return fail(str(exc))
