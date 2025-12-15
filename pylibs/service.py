# soho_core_api/pylibs/service.py
from __future__ import annotations
import re
from typing import Dict, List, Optional, Set, Union
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

    def _is_unit_allowed(self, unit_name: str) -> bool:
        """
        بررسی اینکه آیا یک یونیت مجاز به مدیریت است یا خیر (با در نظر گرفتن فیلترهای سراسری و محلی).

        Args:
            unit_name (str): نام یونیت (مانند `nginx.service`)

        Returns:
            bool: True اگر مدیریت مجاز باشد، در غیر این صورت False
        """
        # 1. اگر در excluded سراسری یا محلی باشد → غیرمجاز
        if unit_name in self._global_excluded_units or unit_name in self._local_excluded:
            return False
        # 2. اگر included سراسری تنظیم شده باشد → فقط اگر در آن باشد مجاز است
        if self._global_included_units is not None:
            if unit_name not in self._global_included_units:
                return False
        # 3. اگر included محلی تنظیم شده باشد → فقط اگر در آن باشد مجاز است
        if self._local_included is not None:
            if unit_name not in self._local_included:
                return False
        return True

    def _run_systemctl(self, args: List[str]) -> str:
        """
        اجرای دستور systemctl با مدیریت خطا.

        Args:
            args: آرگومان‌های systemctl (مثال: ["status", "nginx.service"])

        Returns:
            str: stdout دستور

        Raises:
            CLICommandError: در صورت خطا در اجرای systemctl
        """
        return run_cli_command(["/usr/bin/systemctl"] + args, use_sudo=True)[0]

    def _get_unit_property(self, unit_name: str, property_name: str) -> Optional[str]:
        """
        دریافت یک خاصیت خاص از یونیت systemd با استفاده از `systemctl show`.

        Args:
            unit_name (str): نام یونیت
            property_name (str): نام خاصیت (مثال: "ActiveState", "MainPID", "Id")

        Returns:
            Optional[str]: مقدار خاصیت یا None اگر یونیت وجود نداشته باشد
        """
        try:
            output = self._run_systemctl(["show", "--property", property_name, unit_name])
            # نتیجه شبیه: "ActiveState=active"
            if "=" in output:
                return output.split("=", 1)[1].strip()
            return None
        except CLICommandError:
            return None

    def get_status(self, unit_name: str) -> Dict[str, Union[str, int, bool, None]]:
        """
        دریافت وضعیت کامل یک یونیت systemd.

        Args:
            unit_name (str): نام یونیت (مثال: "nginx.service")

        Returns:
            Dict شامل:
                - active_state: وضعیت فعال‌سازی (active, inactive, failed, ...)
                - load_state: وضعیت بارگذاری فایل یونیت
                - sub_state: وضعیت زیرمجموعه (running, exited, dead, ...)
                - main_pid: شماره پردازه اصلی (0 اگر فعال نباشد)
                - enabled: آیا یونیت در بوت فعال است؟
        """
        active = self._get_unit_property(unit_name, "ActiveState") or "unknown"
        load = self._get_unit_property(unit_name, "LoadState") or "unknown"
        sub = self._get_unit_property(unit_name, "SubState") or "unknown"
        pid_raw = self._get_unit_property(unit_name, "MainPID") or "0"
        try:
            pid = int(pid_raw)
        except ValueError:
            pid = 0
        enabled_raw = self._get_unit_property(unit_name, "UnitFileState")
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
        def _get_deps(cmd_flag: str) -> List[str]:
            try:
                out = self._run_systemctl([cmd_flag, unit_name])
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
            # ✅ فقط یونیت‌های مجاز را اضافه کن
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
        if not self._is_unit_allowed(unit_name):
            raise PermissionError(f"یونیت '{unit_name}' مجاز به مدیریت نیست.")
        self._run_systemctl(["start", unit_name])

    def stop(self, unit_name: str) -> None:
        if not self._is_unit_allowed(unit_name):
            raise PermissionError(f"یونیت '{unit_name}' مجاز به مدیریت نیست.")
        self._run_systemctl(["stop", unit_name])

    def restart(self, unit_name: str) -> None:
        if not self._is_unit_allowed(unit_name):
            raise PermissionError(f"یونیت '{unit_name}' مجاز به مدیریت نیست.")
        self._run_systemctl(["restart", unit_name])

    def reload(self, unit_name: str) -> None:
        if not self._is_unit_allowed(unit_name):
            raise PermissionError(f"یونیت '{unit_name}' مجاز به مدیریت نیست.")
        self._run_systemctl(["reload", unit_name])

    def enable(self, unit_name: str) -> None:
        if not self._is_unit_allowed(unit_name):
            raise PermissionError(f"یونیت '{unit_name}' مجاز به مدیریت نیست.")
        self._run_systemctl(["enable", unit_name])

    def disable(self, unit_name: str) -> None:
        if not self._is_unit_allowed(unit_name):
            raise PermissionError(f"یونیت '{unit_name}' مجاز به مدیریت نیست.")
        self._run_systemctl(["disable", unit_name])

    def mask(self, unit_name: str) -> None:
        if not self._is_unit_allowed(unit_name):
            raise PermissionError(f"یونیت '{unit_name}' مجاز به مدیریت نیست.")
        self._run_systemctl(["mask", unit_name])

    def unmask(self, unit_name: str) -> None:
        if not self._is_unit_allowed(unit_name):
            raise PermissionError(f"یونیت '{unit_name}' مجاز به مدیریت نیست.")
        self._run_systemctl(["unmask", unit_name])

    def is_active(self, unit_name: str) -> bool:
        """بررسی اینکه آیا یونیت در حال اجراست یا خیر."""
        status = self.get_status(unit_name)
        return status["active_state"] == "active"


# ========== تنظیم لیست مجاز سرویس‌ها ==========
ALLOWED_SERVICES = {
    "networking.service",
    "nginx.service",
    "smbd.service",
    "soho_core_api.service",
    "ssh.service",
}

ServiceManager.set_global_filter(included=list(ALLOWED_SERVICES))
