from django.http import JsonResponse  # برای ساخت پاسخ JSON
import psutil  # psutil برای خواندن آمار سیستم
from typing import Dict, List, Any, Optional  # تایپ‌هینت برای خوانایی بهتر
import subprocess  # اجرای دستورات سیستمی در صورت نیاز

import psutil  # psutil برای خواندن آمار سیستم
import time
from typing import Dict, Any, Optional, List  # تایپ‌هینت برای خوانایی بهتر
from django.http import JsonResponse  # برای ساخت پاسخ JSON


class Network:
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

            # ۲. آمار دومین اینترفیس‌ها بعد از interval
            self._net_io_final = psutil.net_io_counters(pernic=True)

            # محاسبه سرعت
            self._bandwidth_data = self._calculate_bandwidth(interval)

            # ۳. IP و MAC هر interface
            self._net_addrs = psutil.net_if_addrs()
            self._addr_data = {
                intf: [addr._asdict() for addr in addrs]
                for intf, addrs in self._net_addrs.items()
            }

            # ۴. وضعیت هر interface (up/down, duplex, speed)
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

            # ۶. gateway پیش‌فرض
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
        """گرفتن gateway پیش‌فرض در لینوکس از /proc/net/route"""
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
        """بازگرداندن اطلاعات یک interface خاص"""
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
        """فقط interfaceهای مشخص شده را برمی‌گرداند"""
        result = {}
        all_interfaces = set(self._io_data_initial.keys()) | set(self._addr_data.keys()) | set(self._stats_data.keys())

        for intf in interface_names:
            if intf in all_interfaces:
                result[intf] = self.get_interface(intf)
        return result

    def to_dict(self) -> Dict[str, Any]:
        """بازگرداندن تمام اطلاعات شبکه به صورت dict"""
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

        return JsonResponse(data, safe=False)  # برگرداندن خروجی به صورت JSON
