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
    این کلاس از کتابخانه‌های psutil و دستورات سیستمی (ip, ethtool) برای جمع‌آوری اطلاعات استفاده می‌کند.
    """

    def __init__(self):
        self._available_nics = psutil.net_if_addrs().keys()

    def _get_nic_stats(self, nic_name: str) -> Dict[str, Any]:
        """دریافت آمار لحظه‌ای (پهنای باند) برای یک کارت شبکه."""
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
        """دریافت پهنای باند لحظه‌ای (دانلود و آپلود) به بایت. """
        stats = self._get_nic_stats(nic_name)
        return {"upload_bytes": stats["bytes_sent"],
                "download_bytes": stats["bytes_recv"], }

    def get_traffic_summary(self, nic_name: str) -> Dict[str, Any]:
        """اطلاعات در سه دسته: سرعت، تعداد بسته، مقدار حجم."""
        stats = self._get_nic_stats(nic_name)
        return {
            "volume": {"bytes_sent": stats["bytes_sent"],
                       "bytes_recv": stats["bytes_recv"], },
            "packets": {"sent": stats["packets_sent"],
                        "recv": stats["packets_recv"], },
            "speed": self._detect_speed(nic_name), }

    def _detect_speed(self, nic_name: str) -> Optional[int]:
        """تشخیص سرعت کارت شبکه (مگابیت بر ثانیه) با استفاده از ethtool."""
        try:
            stdout, _ = run_cli_command(["/usr/sbin/ethtool", nic_name], use_sudo=True)
            match = re.search(r"Speed:\s*(\d+)(?:Mb/s)?", stdout)
            return int(match.group(1)) if match else None
        except CLICommandError:
            return None

    def get_hardware_info(self, nic_name: str) -> Dict[str, Any]:
        """اطلاعات سخت‌افزاری کارت شبکه."""
        # آدرس MAC
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
        """اطلاعات عمومی شامل IP و غیره (غیر از volume/packets/speed)."""
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
        """لیست تمام NICها و تعداد آن‌ها."""
        nics = list(self._available_nics)
        return {"count": len(nics),
                "names": nics, }

    def gather_all_info(self) -> Dict[str, Any]:
        """استخراج اطلاعات کامل برای همه کارت‌های شبکه."""
        result = {}
        for nic in self._available_nics:
            try:
                result[nic] = {"bandwidth": self.get_bandwidth(nic),
                               "traffic_summary": self.get_traffic_summary(nic),
                               "hardware": self.get_hardware_info(nic),
                               "general": self.get_general_info(nic), }
            except Exception:
                # در صورت خطا در یک NIC، آن را نادیده بگیر و ادامه بده
                result[nic] = {"error": "failed_to_retrieve"}
        return result

    def configure_interface_file(self, nic_name: str, config: Dict[str, Any]) -> None:
        """
        نوشتن تنظیمات به فایل /etc/network/interfaces.d/{nic_name}
        پارامترهای config: mode (dhcp/static), ip, netmask, gateway, dns, mtu, ...
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
        """غیرفعال‌سازی کارت شبکه."""
        run_cli_command(["/sbin/ifdown", nic_name], use_sudo=True)

    def ifup(self, nic_name: str) -> None:
        """فعال‌سازی کارت شبکه."""
        run_cli_command(["/sbin/ifup", nic_name], use_sudo=True)

    def restart_interface(self, nic_name: str) -> None:
        """غیرفعال و دوباره فعال‌سازی کارت شبکه."""
        try:
            self.ifdown(nic_name)
        except CLICommandError:
            pass  # اگر down نبود، ایرادی ندارد
        self.ifup(nic_name)

    def is_valid_interface_name(self, nic_name: str) -> bool:
        """بررسی اینکه آیا نام کارت شبکه معتبر و موجود است."""
        return nic_name in self._available_nics
