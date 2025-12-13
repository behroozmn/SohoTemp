# soho_core_api/managers/cpu_manager.py
import os
import subprocess
from typing import Dict, List, Any, Optional
import psutil


class CPUManager:
    """
    کلاس جامع برای مدیریت و بازیابی اطلاعات CPU از منابع مختلف:
    - دستور lscpu (قابل اعتمادترین منبع برای اطلاعات سخت‌افزاری ثابت)
    - فایل /proc/cpuinfo (به‌عنوان منبع جایگزین یا تکمیلی)
    - کتابخانه psutil (برای اطلاعات پویا مانند درصد استفاده و فرکانس لحظه‌ای)

    این کلاس امکان بازیابی اطلاعات هم برای کل CPU و هم برای هر هسته به‌طور جداگانه را فراهم می‌کند.
    """

    def __init__(self) -> None:
        self._lscpu_data: Dict[str, str] = self._parse_lscpu()
        self._proc_cpuinfo_data: List[Dict[str, str]] = self._parse_proc_cpuinfo()
        self._logical_core_count: int = psutil.cpu_count(logical=True) or 1
        self._physical_core_count: int = psutil.cpu_count(logical=False) or 1

    def _run_command(self, cmd: List[str]) -> str:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                raise RuntimeError(f"دستور {' '.join(cmd)} با خطا مواجه شد: {result.stderr}")
            return result.stdout
        except Exception as e:
            raise RuntimeError(f"خطا در اجرای دستور سیستمی: {e}") from e

    def _parse_lscpu(self) -> Dict[str, str]:
        output = self._run_command(["lscpu"])
        data = {}
        for line in output.strip().splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                data[key.strip()] = value.strip()
        return data

    def _parse_proc_cpuinfo(self) -> List[Dict[str, str]]:
        if not os.path.exists("/proc/cpuinfo"):
            return []
        with open("/proc/cpuinfo", "r") as f:
            content = f.read()
        processors = []
        current = {}
        for line in content.strip().splitlines():
            if line.strip() == "":
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
        usage = psutil.cpu_percent(interval=0.1)
        freq_info = psutil.cpu_freq()
        freq = freq_info.current if freq_info else None
        return {
            "usage_percent_total": usage,
            "frequency_total": freq
        }

    def _get_per_core_usage(self) -> List[float]:
        return psutil.cpu_percent(percpu=True, interval=0.1)

    def _get_per_core_frequency(self) -> List[Optional[float]]:
        freqs = []
        for core in self._proc_cpuinfo_data:
            mhz = core.get("cpu MHz")
            if mhz:
                try:
                    freqs.append(float(mhz))
                except ValueError:
                    freqs.append(None)
            else:
                freqs.append(None)
        if not freqs or len(freqs) < self._logical_core_count:
            base_freq = psutil.cpu_freq()
            base = base_freq.current if base_freq else None
            freqs = [base] * self._logical_core_count
        return freqs

    def gather_info(self, core_id: Optional[int] = None, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        جمع‌آوری اطلاعات CPU بر اساس پارامترهای درخواستی.

        Args:
            core_id (Optional[int]): شناسه هسته مورد نظر. اگر None باشد، اطلاعات کلی بازگردانده می‌شود.
            fields (Optional[List[str]]): لیست فیلدهای مورد نیاز. اگر None باشد، تمام فیلدها بازگردانده می‌شوند.

        Returns:
            Dict[str, Any]: دیکشنری حاوی اطلاعات درخواستی.
        """
        result: Dict[str, Any] = {}

        hw_info = self._get_hardware_info()
        total_stats = self._get_total_usage_and_freq()
        per_core_usage = self._get_per_core_usage()
        per_core_freq = self._get_per_core_frequency()

        all_fields = {
            "vendor_id", "model_name", "architecture", "cpu_op_mode", "byte_order",
            "cpu_count_physical", "cpu_count_logical", "threads_per_core", "cores_per_socket",
            "sockets", "flags", "hypervisor", "virtualization",
            "usage_percent_total", "frequency_total",
            "per_core_usage", "per_core_frequency"
        }
        target_fields = set(fields) if fields else all_fields

        for key in hw_info:
            if key in target_fields:
                result[key] = hw_info[key]

        if "usage_percent_total" in target_fields:
            result["usage_percent_total"] = total_stats["usage_percent_total"]
        if "frequency_total" in target_fields:
            result["frequency_total"] = total_stats["frequency_total"]

        if "per_core_usage" in target_fields:
            if core_id is not None:
                result["per_core_usage"] = per_core_usage[core_id] if core_id < len(per_core_usage) else None
            else:
                result["per_core_usage"] = per_core_usage

        if "per_core_frequency" in target_fields:
            if core_id is not None:
                result["per_core_frequency"] = per_core_freq[core_id] if core_id < len(per_core_freq) else None
            else:
                result["per_core_frequency"] = per_core_freq

        return result
