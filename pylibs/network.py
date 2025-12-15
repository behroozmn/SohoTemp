# soho_core_api/pylibs/network.py
from __future__ import annotations
import os
import re
import psutil
import socket
import subprocess
from typing import Dict, List, Any, Optional
from pylibs import CLICommandError, run_cli_command
from pylibs.mixins import NetworkValidationMixin


class NetworkManager:
    """
    مدیریت جامع اطلاعات و تنظیمات کارت‌های شبکه (NIC) در سیستم.

    این کلاس از کتابخانه‌های psutil و دستورات سیستمی (مانند `ethtool`، `ifup`/`ifdown`) برای جمع‌آوری اطلاعات سخت‌افزاری،
    آمار ترافیک، آدرس‌های IP و همچنین پیکربندی فایل‌های تنظیمات شبکه استفاده می‌کند.
    """

    def __init__(self):
        """
        سازنده کلاس. لیست تمام کارت‌های شبکه (NIC) موجود در سیستم را از طریق psutil بارگذاری می‌کند.
        """
        self._available_nics = psutil.net_if_addrs().keys()

    def _get_nic_stats(self, nic_name: str) -> Dict[str, Any]:
        """
        دریافت آمار لحظه‌ای (پهنای باند و خطاهای I/O) برای یک کارت شبکه مشخص.

        Args:
            nic_name (str): نام کارت شبکه (مثلاً `eth0` یا `enp3s0`).

        Returns:
            Dict[str, Any]: دیکشنری شامل فیلدهای زیر:
                - `bytes_sent` (int): تعداد بایت‌های ارسالی.
                - `bytes_recv` (int): تعداد بایت‌های دریافتی.
                - `packets_sent` (int): تعداد بسته‌های ارسالی.
                - `packets_recv` (int): تعداد بسته‌های دریافتی.
                - `errin` (int): تعداد خطاهای ورودی (دریافت).
                - `errout` (int): تعداد خطاهای خروجی (ارسال).
                - `dropin` (int): تعداد بسته‌های رهاشده در ورودی.
                - `dropout` (int): تعداد بسته‌های رهاشده در خروجی.

        Raises:
            ValueError: اگر نام کارت شبکه در سیستم یافت نشود.
            RuntimeError: اگر آماری برای کارت شبکه در دسترس نباشد.
        """
        if nic_name not in self._available_nics:
            raise ValueError(f"کارت شبکه '{nic_name}' یافت نشد.")
        stats = psutil.net_io_counters(pernic=True).get(nic_name)
        if not stats:
            raise RuntimeError(f"آماری برای کارت '{nic_name}' در دسترس نیست.")
        return {"bytes_sent": stats.bytes_sent,
                "bytes_recv": stats.bytes_recv,
                "packets_sent": stats.packets_sent,
                "packets_recv": stats.packets_recv,
                "errin": stats.errin,
                "errout": stats.errout,
                "dropin": stats.dropin,
                "dropout": stats.dropout, }

    def get_bandwidth(self, nic_name: str) -> Dict[str, int]:
        """
        بازیابی پهنای باند لحظه‌ای (دریافت و ارسال) بر اساس داده‌های آماری کارت شبکه.

        Args:
            nic_name (str): نام کارت شبکه.

        Returns:
            Dict[str, int]: دیکشنری شامل:
                - `upload_bytes`: تعداد بایت‌های ارسالی (آپلود).
                - `download_bytes`: تعداد بایت‌های دریافتی (دانلود).
        """
        stats = self._get_nic_stats(nic_name)
        return {"upload_bytes": stats["bytes_sent"],
                "download_bytes": stats["bytes_recv"], }

    def get_traffic_summary(self, nic_name: str) -> Dict[str, Any]:
        """
        دریافت خلاصه‌ای از ترافیک کارت شبکه در سه دسته‌بندی: حجم (بایت)، تعداد بسته، و سرعت لینک.

        Args:
            nic_name (str): نام کارت شبکه.

        Returns:
            Dict[str, Any]: دیکشنری ساختاریافته شامل:
                - `volume` (dict): حجم داده‌های ارسالی و دریافتی به بایت.
                    - `bytes_sent` (int)
                    - `bytes_recv` (int)
                - `packets` (dict): تعداد بسته‌های ارسالی و دریافتی.
                    - `sent` (int)
                    - `recv` (int)
                - `speed` (Optional[int]): سرعت لینک به مگابیت بر ثانیه (ممکن است `None` باشد).
        """
        stats = self._get_nic_stats(nic_name)
        return {
            "volume": {"bytes_sent": stats["bytes_sent"],
                       "bytes_recv": stats["bytes_recv"], },
            "packets": {"sent": stats["packets_sent"],
                        "recv": stats["packets_recv"], },
            "speed": self._detect_speed(nic_name), }

    def _detect_speed(self, nic_name: str) -> Optional[int]:
        """
        تشخیص سرعت لینک فیزیکی کارت شبکه (Link Speed) به کمک دستور `ethtool`.

        Args:
            nic_name (str): نام کارت شبکه.

        Returns:
            Optional[int]: سرعت به مگابیت بر ثانیه (مثلاً 1000, 100, 10) یا `None` در صورت شکست.

        Notes:
            - این تابع نیاز به نصب بسته `ethtool` و دسترسی `sudo` دارد.
            - در صورت خطا یا عدم پشتیبانی کارت (مثل کارت‌های مجازی)، مقدار `None` بازگردانده می‌شود.
        """
        try:
            stdout, _ = run_cli_command(["/usr/sbin/ethtool", nic_name], use_sudo=True)
            match = re.search(r"Speed:\s*(\d+)(?:Mb/s)?", stdout)
            return int(match.group(1)) if match else None
        except CLICommandError:
            return None

    def get_hardware_info(self, nic_name: str) -> Dict[str, Any]:
        """
        بازیابی اطلاعات سخت‌افزاری یک کارت شبکه.

        Args:
            nic_name (str): نام کارت شبکه.

        Returns:
            Dict[str, Any]: شامل:
                - `name` (str): نام کارت شبکه.
                - `mac_address` (Optional[str]): آدرس MAC (در صورت وجود).
                - `mtu` (Optional[int]): اندازهٔ بیشینهٔ واحد انتقال (MTU).
                - `is_up` (bool): وضعیت فیزیکی/منطقی کارت (فعال یا غیرفعال).
                - `speed_mbps` (Optional[int]): سرعت لینک به مگابیت بر ثانیه.
        """
        addrs = psutil.net_if_addrs().get(nic_name, [])
        mac = None
        for addr in addrs:
            if addr.family == psutil.AF_LINK:
                mac = addr.address
                break

        return {"name": nic_name,
                "mac_address": mac,
                "mtu": psutil.net_if_stats().get(nic_name, {}).mtu if nic_name in psutil.net_if_stats() else None,
                "is_up": psutil.net_if_stats().get(nic_name, {}).isup if nic_name in psutil.net_if_stats() else False,
                "speed_mbps": self._detect_speed(nic_name), }

    def get_general_info(self, nic_name: str) -> Dict[str, Any]:
        """
        دریافت اطلاعات عمومی و شبکه‌ای یک کارت (غیر از حجم، تعداد بسته و سرعت).

        Args:
            nic_name (str): نام کارت شبکه.

        Returns:
            Dict[str, Any]: شامل:
                - `mac_address` (Optional[str]): آدرس MAC.
                - `mtu` (Optional[int]): MTU.
                - `is_up` (bool): وضعیت فعال بودن کارت.
                - `ip_addresses` (List[Dict]): لیست آدرس‌های IP (IPv4 و IPv6) با جزئیات.
                    - برای IPv4: `ip`, `netmask`, `broadcast`
                    - برای IPv6: `ipv6`, `netmask`
        """
        addrs = psutil.net_if_addrs().get(nic_name, [])
        ip_info = []
        for addr in addrs:
            if addr.family == socket.AF_INET:
                ip_info.append({
                    "ip": addr.address,
                    "netmask": addr.netmask,
                    "broadcast": addr.broadcast,
                })
            elif addr.family == socket.AF_INET6:
                ip_info.append({"ipv6": addr.address,
                                "netmask": addr.netmask, })

        hw = self.get_hardware_info(nic_name)
        return {"mac_address": hw["mac_address"],
                "mtu": hw["mtu"],
                "is_up": hw["is_up"],
                "ip_addresses": ip_info, }

    def list_nics(self) -> Dict[str, int]:
        """
        بازیابی لیست تمام کارت‌های شبکه موجود و تعداد آن‌ها.

        Returns:
            Dict[str, Any]: شامل:
                - `count` (int): تعداد کل کارت‌های شبکه.
                - `names` (List[str]): لیست نام کارت‌ها (مثل `['lo', 'eth0', 'enp3s0']`).
        """
        nics = list(self._available_nics)
        return {"count": len(nics),
                "names": nics, }

    def gather_all_info(self) -> Dict[str, Any]:
        """
        جمع‌آوری اطلاعات کامل تمام کارت‌های شبکه در یک دیکشنری.

        Returns:
            Dict[str, Any]: کلیدها نام کارت‌ها هستند و مقادیر شامل:
                - `bandwidth`
                - `traffic_summary`
                - `hardware`
                - `general`
            در صورت بروز خطا برای یک کارت، مقدار آن به‌صورت `{"error": "failed_to_retrieve"}` تنظیم می‌شود.
        """
        result = {}
        for nic in self._available_nics:
            try:
                result[nic] = {"bandwidth": self.get_bandwidth(nic),
                               "traffic_summary": self.get_traffic_summary(nic),
                               "hardware": self.get_hardware_info(nic),
                               "general": self.get_general_info(nic), }
            except Exception:
                result[nic] = {"error": "failed_to_retrieve"}
        return result

    def configure_interface_file(self, nic_name: str, config: Dict[str, Any]) -> None:
        """
        نوشتن فایل پیکربندی شبکه در `/etc/network/interfaces.d/{nic_name}` (برای سیستم‌های مبتنی بر Debian).

        Args:
            nic_name (str): نام کارت شبکه (مثلاً `eth0`).
            config (Dict[str, Any]): دیکشنری تنظیمات با فیلدهای:
                - `mode` (str): حالت آدرس‌دهی (`dhcp` یا `static`).
                - `ip` (str, optional): آدرس IP (در حالت static).
                - `netmask` (str, optional): ماسک شبکه.
                - `gateway` (str, optional): دروازه پیش‌فرض.
                - `dns` (Union[str, List[str]], optional): سرورهای DNS.
                - `mtu` (int, optional): اندازه MTU.

        Raises:
            CLICommandError: در صورت عدم دسترسی به فایل یا خطای سیستم فایل.
        """
        mode = config.get("mode", "dhcp")
        path = f"/etc/network/interfaces.d/{nic_name}"
        lines = [f"auto {nic_name}",
                 f"iface {nic_name} inet {mode}", ]
        if mode == "static":
            if ip := config.get("ip"):
                lines.append(f"    address {ip}")
            if netmask := config.get("netmask"):
                lines.append(f"    netmask {netmask}")
            if gateway := config.get("gateway"):
                lines.append(f"    gateway {gateway}")
            if dns_list := config.get("dns"):
                dns_str = " ".join(dns_list) if isinstance(dns_list, list) else dns_list
                lines.append(f"    dns-nameservers {dns_str}")
        if mtu := config.get("mtu"):
            lines.append(f"    mtu {mtu}")

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except (OSError, PermissionError) as e:
            raise CLICommandError(command=["write", path], returncode=1, stderr=str(e), stdout="", )

    def ifdown(self, nic_name: str) -> None:
        """
        غیرفعال‌سازی یک کارت شبکه با استفاده از دستور سیستمی `ifdown`.

        Args:
            nic_name (str): نام کارت شبکه.
        """
        run_cli_command(["/sbin/ifdown", nic_name], use_sudo=True)

    def ifup(self, nic_name: str) -> None:
        """
        فعال‌سازی یک کارت شبکه با استفاده از دستور سیستمی `ifup`.

        Args:
            nic_name (str): نام کارت شبکه.
        """
        run_cli_command(["/sbin/ifup", nic_name], use_sudo=True)

    def restart_interface(self, nic_name: str) -> None:
        """
        راه‌اندازی مجدد یک کارت شبکه (ifdown → ifup).

        Args:
            nic_name (str): نام کارت شبکه.

        Notes:
            - اگر کارت از قبل غیرفعال باشد، `ifdown` خطایی ایجاد نمی‌کند.
        """
        try:
            self.ifdown(nic_name)
        except CLICommandError:
            pass
        self.ifup(nic_name)

    def is_valid_interface_name(self, nic_name: str) -> bool:
        """
        بررسی اینکه آیا نام داده‌شده مربوط به یک کارت شبکهٔ موجود در سیستم است.

        Args:
            nic_name (str): نام کارت شبکه.

        Returns:
            bool: `True` اگر نام معتبر و موجود باشد، در غیر این صورت `False`.
        """
        return nic_name in self._available_nics