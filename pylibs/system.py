# soho_core_api/pylibs/power.py
from __future__ import annotations
from typing import Dict, Any
from pylibs import CLICommandError, run_cli_command


class PowerManager:
    """
    مدیریت عملیات خاموش‌کردن و ریبوت سیستم از طریق systemd.

    این کلاس فقط دو عملیات مجاز را پشتیبانی می‌کند:
    - خاموش‌کردن سیستم (poweroff)
    - راه‌اندازی مجدد سیستم (reboot)

    تمام دستورات با استفاده از systemctl و sudo اجرا می‌شوند.
    """

    def _execute_power_command(self, action: str) -> None:
        """
        اجرای دستور systemctl برای عملیات خاموش‌کردن یا ریبوت.

        Args:
            action (str): یکی از مقادیر "poweroff" یا "reboot"

        Raises:
            ValueError: اگر action معتبر نباشد
            CLICommandError: در صورت خطا در اجرای دستور
        """
        if action not in ("poweroff", "reboot"):
            raise ValueError(f"عملیات '{action}' پشتیبانی نمی‌شود. مقادیر مجاز: poweroff, reboot")
        run_cli_command(["/usr/bin/systemctl", action], use_sudo=True)

    def poweroff(self) -> None:
        """
        خاموش‌کردن سیستم با استفاده از `systemctl poweroff`.

        Raises:
            CLICommandError: در صورت خطا در اجرای دستور
        """
        self._execute_power_command("poweroff")

    def reboot(self) -> None:
        """
        راه‌اندازی مجدد سیستم با استفاده از `systemctl reboot`.

        Raises:
            CLICommandError: در صورت خطا در اجرای دستور
        """
        self._execute_power_command("reboot")