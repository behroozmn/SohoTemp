from django.http import JsonResponse
import psutil
from typing import Dict, List, Any, Optional
import subprocess


class Memory:
    def __init__(self):
        try:
            self._mem = psutil.virtual_memory()
        except Exception as e:
            raise RuntimeError("ERROR in getting data from system") from e

    def get(self, *fields: str) -> Dict[str, Optional[Any]]:
        """فقط فیلدهای تعیین شده را برمی‌گرداند."""
        data = self._mem._asdict()
        result = {}

        for field in fields:
            result[field] = data.get(field, None)

        return result

    def to_dict(self) -> Dict[str, Any]:
        """تمام فیلدها را به صورت dict برمی‌گرداند."""
        return self._mem._asdict()

    def total(self) -> int:
        return self._mem.total  # total physical psutil.virtual_memory()ory available.

    def available(self) -> int:
        # the memory that can be given instantly to processes without the system going into swap.
        # This is calculated by summing different memory values depending on the platform and it is supposed to be used to monitor actual memory usage in a cross-platform fashion.
        return self._mem.available

    def used(self) -> int:
        return self._mem.used  # memory used, calculated differently depending on the platform and designed for informational purposes only: macOS: active + wired BSD: active + wired + cached Linux: total - free

    def free(self) -> int:
        # memory not being used at all(zeroed) that is readily available
        # NOTE: this doesn't reflect the actual memory available (use 'available' instead)
        return self._mem.free

    def percent(self) -> float:
        """درصد استفاده از RAM"""
        # calculated as (total - available) / total * 100
        return self._mem.percent

    def active(self) -> Optional[int]:
        """فقط در لینوکس/ماک وجود دارد"""
        # active(UNIX): memory [currently in use] or [very recently used], and so it is in RAM.
        return getattr(self._mem, 'active', None)

    def inactive(self) -> Optional[int]:
        """فقط در لینوکس/ماک وجود دارد"""
        # inactive(UNIX): memory that is marked as not used.
        return getattr(self._mem, 'inactive', None)

    def buffers(self) -> Optional[int]:
        """فقط در لینوکس وجود دارد"""
        # buffers(BSD,Linux): cache for things like file system metadata.
        return getattr(self._mem, 'buffers', None)

    def cached(self) -> Optional[int]:
        """فقط در لینوکس/ماک وجود دارد"""
        # cached(BSD,macOS): cache for various things.
        return getattr(self._mem, 'cached', None)

    def shared(self) -> Optional[int]:
        """فقط در لینوکس وجود دارد"""
        # shared(BSD): memory that may be simultaneously accessed by multiple processes.
        return getattr(self._mem, 'shared', None)


class CPU:
    def __init__(self):
        try:
            self._cpu_percent = psutil.cpu_percent()
            self._cpu_times = psutil.cpu_times()._asdict()
            self._cpu_freq = self._get_cpu_frequency()
            self._cpu_cores = self._get_cpu_cores()
        except Exception as e:
            raise RuntimeError(f"Error in getting CPU data: {e}") from e

    def _get_cpu_frequency(self) -> Dict[str, Optional[float]]:
        try:
            return psutil.cpu_freq()._asdict()
        except Exception as e:
            return {"error": str(e)}

    def _get_cpu_cores(self) -> Dict[str, Optional[int]]:
        return {
            "physical": psutil.cpu_count(logical=False),
            "logical": psutil.cpu_count(logical=True)
        }

    def get(self, *fields: str) -> Dict[str, Any]:
        """بازگرداندن فقط فیلدهای تعیین شده"""
        full_data = self.to_dict()
        result = {}

        for field in fields:
            if field in full_data:
                result[field] = full_data[field]
            else:
                result[field] = None

        return result

    def to_dict(self) -> Dict[str, Any]:
        """بازگرداندن تمام اطلاعات CPU به صورت dict"""
        return {
            "cpu_percent": self._cpu_percent,
            "cpu_times_second": self._cpu_times,
            "cpu_frequency": self._cpu_freq,
            "cpu_cores": self._cpu_cores
        }

    def to_json_response(self, selected_fields: Optional[List[str]] = None) -> JsonResponse:
        """برگرداندن اطلاعات به صورت JsonResponse (با امکان انتخاب فیلدها)"""
        if selected_fields:
            data = self.get(*selected_fields)
        else:
            data = self.to_dict()

        return JsonResponse(data, safe=False)


import psutil
import time
from typing import Dict, Any, Optional, List
from django.http import JsonResponse


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

        return JsonResponse(data, safe=False)


class Disk:
    def __init__(self):
        try:
            self._partitions = psutil.disk_partitions()  # فقط mount points و فایل‌سیستم‌ها را برمی‌گرداند
            self._io_counters = psutil.disk_io_counters(perdisk=True)  # آمار read/write دیسک برای هر device
            self._usage_data = {}
            self._details = {}

            for part in self._partitions:
                try:
                    usage = psutil.disk_usage(part.mountpoint)._asdict()  # استفاده از حافظه برای هر partition
                    self._usage_data[part.device] = usage
                except PermissionError:
                    continue

            # جزئیات دیسک: device info, uuid, fs type و غیره
            self._details = self._get_disk_details()
        except Exception as e:
            raise RuntimeError(f"خطا در گرفتن اطلاعات دیسک: {e}") from e

    def _get_disk_details(self) -> Dict[str, Dict[str, Any]]:
        """گرفتن جزئیات بیشتر دیسک با استفاده از lsblk"""
        result = {}

        try:
            # گرفتن لیست دیسک‌ها با lsblk
            output = subprocess.check_output(
                ["lsblk", "-O", "-J"],
                stderr=subprocess.DEVNULL,
                text=True
            )
            data = eval(output)  # تبدیl to dict

            for disk in data.get("blockdevices", []):
                name = disk.get("name")
                result[name] = {
                    "maj_min": disk.get("maj:min"),
                    "rm": disk.get("rm"),
                    "size": disk.get("size"),
                    "ro": disk.get("ro"),
                    "type": disk.get("type"),
                    "mountpoint": disk.get("mountpoint"),
                    "model": disk.get("model"),
                    "serial": disk.get("serial"),
                    "vendor": disk.get("vendor"),
                    "path": f"/dev/{name}",
                    "fstype": disk.get("fstype"),
                    "fsavail": disk.get("fsavail"),
                    "fssize": disk.get("fssize"),
                    "fsused": disk.get("fsused"),
                    "mountpoints": disk.get("mountpoints", []),
                    "uuid": disk.get("uuid"),
                    "state": disk.get("stat"),
                    "scheduler": disk.get("sched"),
                    "hotplug": disk.get("hotplug"),
                    "zoned": disk.get("zoned"),
                    "disc-aln": disk.get("disc-aln"),
                    "disc-granularity": disk.get("disc-gran"),
                    "disc-max": disk.get("disc-max"),
                    "io_rio": disk.get("rIO", 0),
                    "io_wio": disk.get("wIO", 0),
                    "io_time": disk.get("io_time", 0),
                    "discards": disk.get("discards", 0),
                    "read_bytes": disk.get("rbytes", 0),
                    "write_bytes": disk.get("wbytes", 0),
                    "read_count": disk.get("rnum", 0),
                    "write_count": disk.get("wnum", 0),
                    "read_time": disk.get("rtime", 0),
                    "write_time": disk.get("wtime", 0),
                    "queue_depth": disk.get("queue-depth", 0),
                    "latency": disk.get("latency", 0),
                }
        except FileNotFoundError:
            # lsblk وجود ندارد (در سیستم‌های قدیمی یا غیرلینوکس)
            pass
        except Exception as e:
            result["error"] = str(e)

        return result

    def get_disk_io(self, disk_name: str) -> Dict[str, Any]:
        """داده I/O یک دیسک خاص"""
        io = self._io_counters.get(disk_name, None)
        if io:
            return io._asdict()
        return {}

    def get_disk_usage(self, device_path: str) -> Dict[str, Any]:
        """استفاده از حافظه برای یک device خاص"""
        return self._usage_data.get(device_path, {})

    def get_disk_info(self, device: str) -> Dict[str, Any]:
        """اطلاعات یک دیسک خاص شامل mount point, uuid و غیره"""
        return self._details.get(device, {})

    def get_all_devices(self) -> List[Dict[str, Any]]:
        """لیست تمام دیسک‌ها با اطلاعات اولیه"""
        devices = []

        for part in self._partitions:
            device_info = {
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "opts": part.opts,
                "usage": self.get_disk_usage(part.device),
                "io": self.get_disk_io(part.device.split("/")[-1]),
                "details": self.get_disk_info(part.device.split("/")[-1])
            }
            devices.append(device_info)

        return devices

    def to_dict(self) -> Dict[str, Any]:
        """بازگرداندن تمام اطلاعات به صورت dict"""
        return {
            "disks": self.get_all_devices(),
            "summary": {
                "total_disks": len(self._partitions),
                "disk_io_summary": {
                    dev: counters._asdict()
                    for dev, counters in self._io_counters.items()
                },
            }
        }
