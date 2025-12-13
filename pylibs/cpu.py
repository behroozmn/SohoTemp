# soho_core_api/managers/cpu_manager.py
"""
جمع‌آوری اطلاعات CPU با استفاده از منابع استاندارد سیستم.
بدون هیچ وابستگی به StandardResponse یا View.
"""
import os
from typing import Dict, List, Any, Optional
import psutil
from pylibs import run_cli_command, CLICommandError


class CPUManager:
    """
    کلاس جامع برای دریافت اطلاعات CPU از lscpu، /proc/cpuinfo و psutil.
    """

    def __init__(self) -> None:
        self._lscpu_data: Dict[str, str] = self._parse_lscpu()
        self._proc_cpuinfo_data: List[Dict[str, str]] = self._parse_proc_cpuinfo()
        self._logical_core_count: int = psutil.cpu_count(logical=True) or 1
        self._physical_core_count: int = psutil.cpu_count(logical=False) or 1

    def _parse_lscpu(self) -> Dict[str, str]:
        """تحلیل خروجی دستور lscpu."""
        try:
            stdout, _ = run_cli_command(["lscpu"])
            data = {}
            for line in stdout.strip().splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    data[key.strip()] = val.strip()
            return data
        except CLICommandError as e:
            raise RuntimeError(f"خطا در اجرای lscpu: {e}") from e

    def _parse_proc_cpuinfo(self) -> List[Dict[str, str]]:
        """تحلیل فایل /proc/cpuinfo."""
        if not os.path.exists("/proc/cpuinfo"):
            return []
        with open("/proc/cpuinfo", "r") as f:
            lines = f.readlines()

        processors = []
        current = {}
        for line in lines:
            line = line.strip()
            if not line:
                if current:
                    processors.append(current)
                    current = {}
            elif ":" in line:
                key, val = line.split(":", 1)
                current[key.strip()] = val.strip()
        if current:
            processors.append(current)
        return processors

    def _get_hardware_info(self) -> Dict[str, Any]:
        lscpu = self._lscpu_data
        return {
            "vendor_id": lscpu.get("Vendor ID", lscpu.get("VendorID", "ناشناس")),
            "model_name": lscpu.get("Model name", lscpu.get("Model Name", "نامشخص")),
            "architecture": lscpu.get("Architecture", "نامشخص"),
            "cpu_op_mode": lscpu.get("CPU op-mode(s)", "نامشخص"),
            "byte_order": lscpu.get("Byte Order", "نامشخص"),
            "cpu_count_physical": self._physical_core_count,
            "cpu_count_logical": self._logical_core_count,
            "threads_per_core": int(lscpu.get("Thread(s) per core", "1")),
            "cores_per_socket": int(lscpu.get("Core(s) per socket", "1")),
            "sockets": int(lscpu.get("Socket(s)", "1")),
            "flags": lscpu.get("Flags", "").split(),
            "hypervisor": "Hypervisor" in lscpu,
            "virtualization": lscpu.get("Virtualization", "غیرفعال"),
        }

    def _get_total_usage_and_freq(self) -> Dict[str, Any]:
        usage = psutil.cpu_percent(interval=0.2)
        freq_info = psutil.cpu_freq()
        freq = freq_info.current if freq_info else None
        return {
            "usage_percent_total": usage,
            "frequency_total": freq
        }

    def _get_per_core_usage(self) -> List[float]:
        return psutil.cpu_percent(percpu=True, interval=0.2)

    def _get_per_core_frequency(self) -> List[Optional[float]]:
        freqs = []
        for core in self._proc_cpuinfo_data:
            mhz_str = core.get("cpu MHz")
            if mhz_str:
                try:
                    freqs.append(float(mhz_str))
                except (ValueError, TypeError):
                    freqs.append(None)
            else:
                freqs.append(None)
        if not freqs or len(freqs) < self._logical_core_count:
            base_freq = psutil.cpu_freq()
            base = base_freq.current if base_freq else None
            freqs = [base] * self._logical_core_count
        return freqs

    def gather_info(self, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        hw = self._get_hardware_info()
        total_stats = self._get_total_usage_and_freq()
        per_core_usage = self._get_per_core_usage()
        per_core_freq = self._get_per_core_frequency()

        full_data = {
            **hw,
            "usage_percent_total": total_stats["usage_percent_total"],
            "frequency_total": total_stats["frequency_total"],
            "per_core_usage": per_core_usage,
            "per_core_frequency": per_core_freq,
        }

        if not fields:
            return full_data

        return {k: v for k, v in full_data.items() if k in fields}