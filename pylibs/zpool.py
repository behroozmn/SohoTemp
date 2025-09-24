#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import libzfs
from typing import Any, Dict, List, Optional


def ok(data: Any) -> Dict[str, Any]:
    """Return a success envelope (DRF-ready)."""
    return {"ok": True, "error": None, "data": data, "Details": {}}


def fail(message: str, code: str = "zpool_error", extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a failure envelope (DRF-ready)."""
    return {"ok": False, "error": {"code": code, "message": message, "extra": extra or {}}, "data": None, "Details": {}}


class zPoolManager:
    def __init__(self) -> None:
        self.zfs = libzfs.ZFS()

    def list_pools_name(self):
        try:
            return ok([p.name for p in self.zfs.pools])
        except Exception as exc:
            return fail(str(exc))

    def get_pools(self):
        try:
            return self.zfs.pools
        except Exception as exc:
            return fail(str(exc))

    def get_pool(self, pool_name):
        try:
            pool = next(p for p in self.zfs.pools if p.name == pool_name)
            return pool
        except Exception as exc:
            return fail(str(exc))

    def list_pool_size_detail(self, pool_name: str):
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

    def list_pool_details(self, pool_name: str):
        try:
            pool = next(p for p in self.zfs.pools if p.name == pool_name)
            return ok({
                "allocated": str(pool.properties["allocated"].value),
                "altroot": str(pool.properties["altroot"].value),
                "ashift": str(pool.properties["ashift"].value),
                "autoexpand": str(pool.properties["autoexpand"].value),
                "autoreplace": str(pool.properties["autoreplace"].value),
                "bootfs": str(pool.properties["bootfs"].value),
                "cachemode": str(pool.properties["cachemode"].value),
                "capacity": str(pool.properties["capacity"].value),
                "comment": str(pool.properties["comment"].value),
                "dedupditto": str(pool.properties["dedupditto"].value),
                "dedupratio": str(pool.properties["dedupratio"].value),
                "delegation": str(pool.properties["delegation"].value),
                "expandsize": str(pool.properties["expandsize"].value),
                "failmode": str(pool.properties["failmode"].value),
                "fragmentation": str(pool.properties["fragmentation"].value),
                "freeing": str(pool.properties["freeing"].value),
                "free": str(pool.properties["free"].value),
                "guid": str(pool.properties["guid"].value),
                "health": str(pool.properties["health"].value),
                "leaked": str(pool.properties["leaked"].value),
                "listsnapshots": str(pool.properties["listsnapshots"].value),
                "name": str(pool.properties["name"].value),
                "readonly": str(pool.properties["readonly"].value),
                "size": str(pool.properties["size"].value),
            })
        except Exception as exc:
            return fail(str(exc))
