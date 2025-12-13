# soho_core_api/managers/memory_manager.py
"""
جمع‌آوری اطلاعات حافظه با استفاده از lsmem و /proc/meminfo.
"""
import os
import json
from typing import Dict, Any, List, Optional
import psutil
from pylibs import run_cli_command, CLICommandError


class MemoryManager:
    """
    کلاس جامع برای دریافت اطلاعات RAM از lsmem و /proc/meminfo.
    """

    def __init__(self) -> None:
        self._lsmem_data: List[Dict[str, Any]] = self._parse_lsmem()
        self._meminfo_dict: Dict[str, int] = self._parse_proc_meminfo()

    def _parse_lsmem(self) -> List[Dict[str, Any]]:
        """تحلیل خروجی JSON lsmem."""
        try:
            stdout, _ = run_cli_command(["lsmem", "--bytes", "--json"])
            data = json.loads(stdout)
            return data.get("memory", [])
        except (CLICommandError, json.JSONDecodeError, KeyError):
            return []

    def _parse_proc_meminfo(self) -> Dict[str, int]:
        """تحلیل فایل /proc/meminfo (مقادیر به بایت)."""
        meminfo = {}
        if not os.path.exists("/proc/meminfo"):
            return meminfo
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if ":" in line:
                    key, val = line.split(":", 1)
                    try:
                        # مقدار به کیلوبایت است — به بایت تبدیل می‌شود
                        value_kb = int(val.strip().split()[0])
                        meminfo[key.strip()] = value_kb * 1024
                    except (ValueError, IndexError):
                        continue
        return meminfo

    def _get_hardware_info(self) -> Dict[str, Any]:
        """استخراج اطلاعات بلاک‌های حافظه از lsmem."""
        blocks = []
        total_online = 0
        total_offline = 0

        for block in self._lsmem_data:
            size_str = block.get("size", "0")
            try:
                size_bytes = int(size_str)
            except (ValueError, TypeError):
                size_bytes = 0

            info = {
                "range": block.get("range", "unknown"),
                "size_bytes": size_bytes,
                "state": block.get("state", "unknown"),
                "removable": block.get("removable", "unknown"),
                "device": block.get("device"),
            }
            blocks.append(info)

            if block.get("state") == "online":
                total_online += size_bytes
            elif block.get("state") == "offline":
                total_offline += size_bytes

        return {
            "memory_blocks": blocks,
            "total_online_memory_bytes": total_online,
            "total_offline_memory_bytes": total_offline,
        }

    def _get_usage_info(self) -> Dict[str, Any]:
        """محاسبه استفاده از حافظه بر اساس /proc/meminfo."""
        mem = self._meminfo_dict
        total = mem.get("MemTotal", 0)
        free = mem.get("MemFree", 0)
        buffers = mem.get("Buffers", 0)
        cached = mem.get("Cached", 0)
        available = free + buffers + cached
        used = total - available
        usage_percent = round((used / total) * 100, 2) if total > 0 else 0.0

        try:
            psutil_percent = psutil.virtual_memory().percent
        except Exception:
            psutil_percent = None

        return {
            "total_bytes": total,
            "available_bytes": available,
            "used_bytes": used,
            "free_bytes": free,
            "usage_percent": usage_percent,
            "psutil_usage_percent": psutil_percent,
        }

    def gather_info(self, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        hw = self._get_hardware_info()
        usage = self._get_usage_info()
        full_data = {**hw, **usage}

        if not fields:
            return full_data

        return {k: v for k, v in full_data.items() if k in fields}