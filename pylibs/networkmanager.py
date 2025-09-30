import psutil  # برای خواندن آمار سیستم
import time
from typing import Dict, Any, Optional, List  # تایپ‌هینت برای خوانایی بهتر
from django.http import JsonResponse  # برای ساخت پاسخ JSON
import subprocess

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import configparser
from typing import Any, Dict, Optional
import subprocess
import os
import shutil
from datetime import datetime
import os
import re


def ok(data: Any, detail: Any = None) -> Dict[str, Any]:
    return {"ok": True, "error": None, "data": data, "details": detail}


def fail(message: str, code: str = "samba_error", extra: str = None) -> Dict[str, Any]:
    """Return a failure envelope (DRF-ready)."""
    return {"ok": False, "error": {"code": code, "message": message, "extra": extra}}

INTERFACES_DIR = "/etc/network/interfaces.d"

class NetworkManager:
    def __init__(self, interval=1):
        try:
            # ۱. آمار عمومی اینترفیس‌ها: bytes, packets
            self._net_io_initial = psutil.net_io_counters(pernic=True)
            self._io_data_initial = {
                intf: counters._asdict()
                for intf, counters in self._net_io_initial.items()
            }

            # منتظر می‌مانیم برای اندازه‌گیری سرعت
            time.sleep(interval)

            # ۲. آمار دومین اینترفیس‌ها بعد از اینترنال
            self._net_io_final = psutil.net_io_counters(pernic=True)

            # محاسبه سرعت
            self._bandwidth_data = self._calculate_bandwidth(interval)

            # ۳. آی‌پی و مک هر اینترفیس
            self._net_addrs = psutil.net_if_addrs()
            self._addr_data = {
                intf: [addr._asdict() for addr in addrs]
                for intf, addrs in self._net_addrs.items()
            }

            # ۴. وضعیت هر اینترفیس (up/down, duplex, speed)
            self._net_stats = psutil.net_if_stats()
            self._stats_data = {
                intf: {
                    "isup": stats.isup,
                    "duplex": str(stats.duplex),
                    "speed": stats.speed,
                    "mtu": stats.mtu,
                    "flags": stats.flags
                }
                for intf, stats in self._net_stats.items()
            }

            # ۵. شمارش TCP/UDP connections
            self._tcp_connections = len(psutil.net_connections('tcp'))
            self._udp_connections = len(psutil.net_connections('udp'))

            # ۶. گیت‌وی پیش‌فرض
            self._default_gateway = self.get_default_gateway()

        except Exception as e:
            raise RuntimeError(f"خطا در گرفتن اطلاعات شبکه: {e}") from e

    def _calculate_bandwidth(self, interval) -> Dict[str, Dict]:
        """محاسبه upload و download speed بر حسب KB/s"""
        result = {}
        for interface in self._net_io_initial:
            if interface not in self._net_io_final:
                continue
            old = self._net_io_initial[interface]
            new = self._net_io_final[interface]

            upload_speed = (new.bytes_sent - old.bytes_sent) / interval / 1024
            download_speed = (new.bytes_recv - old.bytes_recv) / interval / 1024

            result[interface] = {
                'upload': round(upload_speed, 2),
                'download': round(download_speed, 2),
                'unit': 'KB/s'
            }
        return result

    @staticmethod
    def get_default_gateway() -> Optional[str]:
        """گرفتن گیت‌وی پیش‌فرض در لینوکس از /proc/net/route"""
        import socket

        try:
            with open("/proc/net/route") as f:
                for line in f:
                    fields = line.strip().split()
                    if fields[1] != '00000000' or not int(fields[3], 16) & 2:
                        continue
                    gateway_hex = fields[2]
                    ip_bytes = bytes.fromhex(gateway_hex)[::-1]  # reverse byte order
                    return socket.inet_ntoa(ip_bytes)
        except Exception as e:
            print(f"Error reading default gateway: {e}")
            return None

    def get_interface(self, interface_name: str) -> Dict[str, Any]:
        """بازگرداندن اطلاعات یک اینترفیس خاص"""
        io = self._io_data_initial.get(interface_name, {})
        bandwidth = self._bandwidth_data.get(interface_name, {"upload": 0, "download": 0, "unit": "KB/s"})
        addr = self._addr_data.get(interface_name, [])
        status = self._stats_data.get(interface_name, {})

        return {
            "io_counters": io,
            "bandwidth": bandwidth,
            "addresses": addr,
            "status": status
        }

    def get_interfaces(self, *interface_names: str) -> Dict[str, Dict]:
        """فقط اینترفیس‌های مشخص شده را برمی‌گرداند"""
        result = {}
        all_interfaces = set(self._io_data_initial.keys()) | set(self._addr_data.keys()) | set(self._stats_data.keys())

        for intf in interface_names:
            if intf in all_interfaces:
                result[intf] = self.get_interface(intf)
        return result

    def to_dict(self) -> Dict[str, Any]:
        """بازگرداندن تمام اطلاعات شبکه به صورت دیکشنری"""
        return {
            "interfaces": {
                intf: {
                    "io_counters": self._io_data_initial.get(intf, {}),
                    "bandwidth": self._bandwidth_data.get(intf, {"upload": 0, "download": 0, "unit": "KB/s"}),
                    "addresses": self._addr_data.get(intf, []),
                    "status": self._stats_data.get(intf, {})
                }
                for intf in set(self._io_data_initial.keys()) | set(self._addr_data.keys()) | set(self._stats_data.keys())
            },
            "summary": {
                "total_tcp_connections": self._tcp_connections,
                "total_udp_connections": self._udp_connections,
                "default_gateway": self._default_gateway,
            }
        }

    def to_json_response(self, selected_interfaces: Optional[List[str]] = None) -> JsonResponse:
        """برگرداندن اطلاعات به صورت JsonResponse"""
        if selected_interfaces:
            data = {
                "interfaces": {
                    intf: self.get_interface(intf)
                    for intf in selected_interfaces
                },
                "summary": {
                    "total_tcp_connections": self._tcp_connections,
                    "total_udp_connections": self._udp_connections,
                    "default_gateway": self._default_gateway
                }
            }
        else:
            data = self.to_dict()

        return JsonResponse(data, safe=False)  # برگرداندن خروجی به صورت جی‌سان

    @staticmethod
    def _parse_interface_file(filepath: str) -> List[Dict[str, Any]]:
        """فایل تنظیمات یک اینترفیس را پارس کرده و لیستی از تنظیمات آدرس‌ها را برمی‌گرداند."""
        if not os.path.isfile(filepath):
            return []

        with open(filepath, 'r') as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        interfaces = []
        current_iface = None

        for line in lines:
            # بررسی خطوط auto
            auto_match = re.match(r'^auto\s+(.+)$', line)
            if auto_match:
                continue  # فقط برای فعال‌سازی است، اطلاعات آدرس ندارد

            # شروع یک بلاک iface
            iface_match = re.match(r'^iface\s+([^\s]+)\s+inet\s+(.+)$', line)
            if iface_match:
                iface_name = iface_match.group(1)
                inet_type = iface_match.group(2)
                if inet_type == 'static':
                    current_iface = {
                        "name": iface_name,
                        "address": None,
                        "netmask": None,
                        "gateway": None,
                        "dns": [],
                        "broadcast": None
                    }
                    interfaces.append(current_iface)
                else:
                    current_iface = None
                continue

            # اگر داخل یک بلاک static باشیم
            if current_iface is not None:
                if line.startswith('address '):
                    current_iface["address"] = line.split(maxsplit=1)[1]
                elif line.startswith('netmask '):
                    current_iface["netmask"] = line.split(maxsplit=1)[1]
                elif line.startswith('gateway '):
                    current_iface["gateway"] = line.split(maxsplit=1)[1]
                elif line.startswith('broadcast '):
                    current_iface["broadcast"] = line.split(maxsplit=1)[1]
                elif line.startswith('dns-nameservers '):
                    dns_list = line.split(maxsplit=1)[1].split()
                    current_iface["dns"] = dns_list

        return interfaces

    @classmethod
    def get_all_interfaces_config(cls) -> Dict[str, Any]:
        """همه کارت‌های شبکه را از فایل‌های /etc/network/interfaces.d/ بخواند."""
        if not os.path.isdir(INTERFACES_DIR):
            return fail(f"مسیر {INTERFACES_DIR} وجود ندارد.")

        all_configs = {}

        for filename in os.listdir(INTERFACES_DIR):
            filepath = os.path.join(INTERFACES_DIR, filename)
            if os.path.isfile(filepath):
                interface_configs = cls._parse_interface_file(filepath)
                # استخراج نام اصلی کارت (مثلاً enp3s0 از enp3s0 یا enp3s0:0)
                base_interface = filename  # فایل‌ها معمولاً با نام اصلی کارت ذخیره شده‌اند
                all_configs[base_interface] = interface_configs

        return ok(all_configs)

    @classmethod
    def get_interface_config(cls, interface: str) -> Dict[str, Any]:
        """تنظیمات یک کارت شبکه خاص را برگرداند."""
        filepath = os.path.join(INTERFACES_DIR, interface)
        if not os.path.isfile(filepath):
            return fail(f"فایل تنظیمات برای کارت شبکه '{interface}' یافت نشد.")

        configs = cls._parse_interface_file(filepath)
        return ok(configs)

    @classmethod
    def update_interface_ip(cls, interface: str, new_ip: str, new_netmask: str) -> Dict[str, Any]:
        """
        آدرس IP و netmask یک کارت شبکه را در فایل مربوطه به‌روزرسانی می‌کند.
        فقط اولین بلاک static را تغییر می‌دهد (معمولاً بلاک اصلی).
        """
        filepath = os.path.join(INTERFACES_DIR, interface)
        if not os.path.isfile(filepath):
            return fail(f"فایل تنظیمات برای کارت شبکه '{interface}' یافت نشد.")

        # اعتبارسنجی IP و netmask
        try:
            import ipaddress
            ipaddress.ip_address(new_ip)
            ipaddress.ip_address(new_netmask)
        except ValueError as e:
            return fail(f"آدرس IP یا Netmask نامعتبر است: {e}")

        with open(filepath, 'r') as f:
            lines = f.readlines()

        updated_lines = []
        in_main_static_block = False
        address_replaced = False
        netmask_replaced = False

        for line in lines:
            stripped = line.strip()

            # شروع بلاک iface static
            if re.match(r'^iface\s+' + re.escape(interface) + r'\s+inet\s+static\s*$', stripped):
                in_main_static_block = True
                updated_lines.append(line)
                continue

            # پایان بلاک (با شروع بلاک جدید یا auto جدید)
            if in_main_static_block and (stripped.startswith('iface ') or stripped.startswith('auto ')):
                in_main_static_block = False

            if in_main_static_block:
                if stripped.startswith('address ') and not address_replaced:
                    updated_lines.append(f"address {new_ip}\n")
                    address_replaced = True
                    continue
                elif stripped.startswith('netmask ') and not netmask_replaced:
                    updated_lines.append(f"netmask {new_netmask}\n")
                    netmask_replaced = True
                    continue

            updated_lines.append(line)

        # اگر آدرس یا netmask جایگزین نشده، ممکن است بلاک static وجود نداشته باشد
        if not address_replaced or not netmask_replaced:
            return fail("بلاک تنظیمات static برای کارت اصلی یافت نشد.")

        # نوشتن فایل جدید
        try:
            with open(filepath, 'w') as f:
                f.writelines(updated_lines)

            # اعمال تغییرات (نیاز به دسترسی root)
            # subprocess.run(["sudo ","/usr/sbin/ifdown", interface], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # subprocess.run(["sudo","/usr/sbin/ifup", interface], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["/usr/bin/systemctl", "restart","networking.service"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            return ok({"interface": interface, "ip": new_ip, "netmask": new_netmask}, "آی‌پی با موفقیت به‌روز شد.")
        except subprocess.CalledProcessError as e:
            return fail("خطا در اعمال تنظیمات شبکه. ممکن است دسترسی کافی نباشد یا اینترفیس فعال نباشد.", code="network_apply_error")
        except PermissionError:
            return fail("عدم دسترسی برای نوشتن فایل یا اجرای دستورات شبکه.", code="permission_denied")
        except Exception as e:
            return fail(f"خطای غیرمنتظره: {str(e)}", code="unexpected_error")