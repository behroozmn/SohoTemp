# soho_core_api/pylibs/service.py
from __future__ import annotations
import re
from typing import Dict, List, Optional, Set, Union, Any
from pylibs import CLICommandError, run_cli_command


class ServiceManager:
    """
    مدیریت جامع سرویس‌های سیستم‌عامل بر پایه systemd.

    این کلاس تمام عملیات رایج روی یونیت‌های systemd (مانند start, stop, status, enable, mask و ...)
    را پوشش می‌دهد و امکان فیلتر کردن، مشاهده وابستگی‌ها و بازیابی PID و وضعیت سرویس را فراهم می‌کند.

    ویژگی‌های کلیدی:
    - پشتیبانی از توابع `start`, `stop`, `restart`, `reload`, `enable`, `disable`, `mask`, `unmask`
    - بازیابی وضعیت فعلی سرویس (active, inactive, failed, ...)
    - دریافت شماره پردازه (Main PID) سرویس در صورت فعال بودن
    - لیست‌کردن تمام یونیت‌ها با امکان فیلتر بر اساس وضعیت (running, enabled, failed و ...)
    - مشاهده وابستگی‌های سرویس (`Wants`, `WantedBy`, `Requires`, `After`, `Before`, ...)
    - امکان تنظیم لیست‌های `included_units` و `excluded_units` برای سرورهای خاص (non-global)
    """

    # ✅ تنظیمات سراسری (global exclusions/inclusions)
    _global_included_units: Optional[Set[str]] = None
    _global_excluded_units: Set[str] = set()

    @classmethod
    def set_global_filter(cls, included: Optional[List[str]] = None, excluded: Optional[List[str]] = None) -> None:
        """
        تنظیم فیلترهای سراسری برای تمام نمونه‌های ServiceManager.

        Args:
            included: لیست یونیت‌هایی که مجاز به مدیریت هستند (بقیه ignore می‌شوند).
                      اگر None باشد، هیچ محدودیتی اعمال نمی‌شود.
            excluded: لیست یونیت‌هایی که **هرگز** نباید مدیریت شوند.
        """
        cls._global_included_units = set(included) if included else None
        cls._global_excluded_units = set(excluded) if excluded else set()

    def __init__(self, included_units: Optional[List[str]] = None, excluded_units: Optional[List[str]] = None):
        """
        سازنده اختیاری برای فیلترهای محلی (برای یک نمونه خاص).

        Args:
            included_units: لیست یونیت‌های قابل مدیریت برای این نمونه.
            excluded_units: لیست یونیت‌های غیرقابل مدیریت برای این نمونه.
        """
        self._local_included = set(included_units) if included_units else None
        self._local_excluded = set(excluded_units) if excluded_units else set()

    @staticmethod
    def _normalize_unit_name(name: str) -> str:
        """تبدیل نام یونیت به فرمت کامل systemd (افزودن .service اگر پسوند نداشت)."""
        if "." not in name:
            return name + ".service"
        return name

    def _is_unit_allowed(self, unit_name: str) -> bool:
        """
        بررسی اینکه آیا یک یونیت مجاز به مدیریت است یا خیر (با در نظر گرفتن فیلترهای سراسری و محلی).
        نام ورودی به‌صورت خودکار نرمالایز می‌شود.

        Args:
            unit_name (str): نام یونیت (مانند `nginx` یا `nginx.service`)

        Returns:
            bool: True اگر مدیریت مجاز باشد، در غیر این صورت False
        """
        normalized = self._normalize_unit_name(unit_name)
        if normalized in self._global_excluded_units or normalized in self._local_excluded:
            return False
        if self._global_included_units is not None and normalized not in self._global_included_units:
            return False
        if self._local_included is not None and normalized not in self._local_included:
            return False
        return True

    def _run_systemctl(self, args: List[str]) -> str:
        """
        اجرای دستور systemctl با مدیریت خطا.

        - اگر systemctl خطا دهد (returncode != 0)، run_cli_command خودش CLICommandError raise می‌کند.
        - در غیر این صورت، stdout را برمی‌گرداند.
        """
        stdout, stderr = run_cli_command(["/usr/bin/systemctl"] + args, use_sudo=True)
        return stdout

    def _get_unit_property(self, unit_name: str, property_name: str) -> Optional[str]:
        """
        دریافت یک خاصیت خاص از یونیت systemd با استفاده از `systemctl show`.

        Args:
            unit_name (str): نام یونیت
            property_name (str): نام خاصیت (مثال: "ActiveState", "MainPID", "Id")

        Returns:
            Optional[str]: مقدار خاصیت یا None اگر یونیت وجود نداشته باشد
        """
        normalized = self._normalize_unit_name(unit_name)
        try:
            output = self._run_systemctl(["show", "--property", property_name, normalized])
            if "=" in output:
                return output.split("=", 1)[1].strip()
            return None
        except CLICommandError:
            return None

    def get_status(self, unit_name: str) -> Dict[str, Union[str, int, bool, None]]:
        """
        دریافت وضعیت کامل یک یونیت systemd.

        Args:
            unit_name (str): نام یونیت (مثال: "nginx")

        Returns:
            Dict شامل:
                - active_state: وضعیت فعال‌سازی (active, inactive, failed, ...)
                - load_state: وضعیت بارگذاری فایل یونیت
                - sub_state: وضعیت زیرمجموعه (running, exited, dead, ...)
                - main_pid: شماره پردازه اصلی (0 اگر فعال نباشد)
                - enabled: آیا یونیت در بوت فعال است؟
        """
        normalized = self._normalize_unit_name(unit_name)
        active = self._get_unit_property(normalized, "ActiveState") or "unknown"
        load = self._get_unit_property(normalized, "LoadState") or "unknown"
        sub = self._get_unit_property(normalized, "SubState") or "unknown"
        pid_raw = self._get_unit_property(normalized, "MainPID") or "0"
        try:
            pid = int(pid_raw)
        except ValueError:
            pid = 0
        enabled_raw = self._get_unit_property(normalized, "UnitFileState")
        enabled = enabled_raw in ("enabled", "enabled-runtime") if enabled_raw else False

        return {
            "active_state": active,
            "load_state": load,
            "sub_state": sub,
            "main_pid": pid,
            "enabled": enabled,
        }

    def get_dependencies(self, unit_name: str) -> Dict[str, List[str]]:
        """
        بازیابی وابستگی‌های یک یونیت systemd.

        Args:
            unit_name (str): نام یونیت

        Returns:
            Dict شامل:
                - requires: یونیت‌هایی که این یونیت به آن‌ها نیاز دارد
                - wants: یونیت‌هایی که این یونیت می‌خواهد فعال شوند
                - after: یونیت‌هایی که این یونیت باید **بعد از** آن‌ها شروع شود
                - before: یونیت‌هایی که این یونیت باید **قبل از** آن‌ها شروع شود
                - wanted_by: یونیت‌هایی که این یونیت را در لیست Wants خود دارند
        """
        normalized = self._normalize_unit_name(unit_name)

        def _get_deps(cmd_flag: str) -> List[str]:
            try:
                out = self._run_systemctl([cmd_flag, normalized])
                return [line.strip() for line in out.strip().split("\n") if line.strip()]
            except CLICommandError:
                return []

        return {
            "requires": _get_deps("--requires"),
            "wants": _get_deps("--wants"),
            "after": _get_deps("--after"),
            "before": _get_deps("--before"),
            "wanted_by": _get_deps("--wanted-by"),
        }

    def list_units(self, state_filter: Optional[str] = None) -> List[Dict[str, str]]:
        """
        لیست **یونیت‌های مجاز** با امکان فیلتر بر اساس وضعیت.
        """
        try:
            output = self._run_systemctl(["list-units", "--all", "--no-pager"])
        except CLICommandError:
            return []

        units = []
        lines = output.strip().split("\n")[1:]
        for line in lines:
            if not line.strip():
                continue
            parts = re.split(r"\s{2,}", line.strip())
            if len(parts) < 4:
                continue
            unit = parts[0]
            # ✅ فقط یونیت‌های مجاز را اضافه کن (نام خام از systemctl می‌آید و کامل است)
            if not self._is_unit_allowed(unit):
                continue
            load = parts[1]
            active = parts[2]
            sub = parts[3]
            desc = parts[4] if len(parts) > 4 else ""

            if state_filter and active != state_filter and sub != state_filter:
                continue

            units.append({
                "unit": unit,
                "load": load,
                "active": active,
                "sub": sub,
                "description": desc,
            })
        return units

    # ========== عملیات کنترلی سرویس ==========
    def start(self, unit_name: str) -> None:
        normalized = self._normalize_unit_name(unit_name)
        if not self._is_unit_allowed(normalized):
            raise PermissionError(f"یونیت '{unit_name}' مجاز به مدیریت نیست.")
        self._run_systemctl(["start", normalized])

    def stop(self, unit_name: str) -> None:
        normalized = self._normalize_unit_name(unit_name)
        if not self._is_unit_allowed(normalized):
            raise PermissionError(f"یونیت '{unit_name}' مجاز به مدیریت نیست.")
        self._run_systemctl(["stop", normalized])

    def restart(self, unit_name: str) -> None:
        normalized = self._normalize_unit_name(unit_name)
        if not self._is_unit_allowed(normalized):
            raise PermissionError(f"یونیت '{unit_name}' مجاز به مدیریت نیست.")
        self._run_systemctl(["restart", normalized])

    def reload(self, unit_name: str) -> None:
        normalized = self._normalize_unit_name(unit_name)
        if not self._is_unit_allowed(normalized):
            raise PermissionError(f"یونیت '{unit_name}' مجاز به مدیریت نیست.")
        self._run_systemctl(["reload", normalized])

    def enable(self, unit_name: str) -> None:
        normalized = self._normalize_unit_name(unit_name)
        if not self._is_unit_allowed(normalized):
            raise PermissionError(f"یونیت '{unit_name}' مجاز به مدیریت نیست.")
        self._run_systemctl(["enable", normalized])

    def disable(self, unit_name: str) -> None:
        normalized = self._normalize_unit_name(unit_name)
        if not self._is_unit_allowed(normalized):
            raise PermissionError(f"یونیت '{unit_name}' مجاز به مدیریت نیست.")
        self._run_systemctl(["disable", normalized])

    def mask(self, unit_name: str) -> None:
        normalized = self._normalize_unit_name(unit_name)
        if not self._is_unit_allowed(normalized):
            raise PermissionError(f"یونیت '{unit_name}' مجاز به مدیریت نیست.")
        self._run_systemctl(["mask", normalized])

    def unmask(self, unit_name: str) -> None:
        normalized = self._normalize_unit_name(unit_name)
        if not self._is_unit_allowed(normalized):
            raise PermissionError(f"یونیت '{unit_name}' مجاز به مدیریت نیست.")
        self._run_systemctl(["unmask", normalized])

    def is_active(self, unit_name: str) -> bool:
        """بررسی اینکه آیا یونیت در حال اجراست یا خیر."""
        status = self.get_status(unit_name)
        return status["active_state"] == "active"


# ========== تنظیم لیست مجاز سرویس‌ها ==========
# ⚠️ نام‌ها باید همیشه با پسوند .service باشند
ALLOWED_SERVICES = {
    "nginx.service",
    "smbd.service",
    "soho_core_api.service",
    "ssh.service",  # در Ubuntu/Debian — در RHEL/CentOS باید sshd.service باشد
    # "networking.service",  # ❌ حذف شده چون در اکثر سیستم‌ها وجود ندارد
}

ServiceManager.set_global_filter(included=list(ALLOWED_SERVICES))