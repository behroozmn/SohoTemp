import subprocess  # اجرای دستورات سیستمی در صورت نیاز
import psutil  # برای خواندن آمار سیستم
from typing import Dict, Any, Optional, List  # تایپ‌هینت برای خوانایی بهتر
from django.http import JsonResponse
import psutil
from typing import Dict, List, Any, Optional
import subprocess

import psutil
import time
from typing import Dict, Any, Optional, List
from django.http import JsonResponse

class Disk:
    def __init__(self):
        try:
            self._partitions = psutil.disk_partitions()  # فقط mount points و فایل‌سیستم‌ها را برمی‌گرداند
            self._io_counters = psutil.disk_io_counters(perdisk=True)  # آمار read/write دیسک برای هر device
            self._usage_data = {}
            self._details = {}

            for part in self._partitions:
                try:
                    usage = psutil.disk_usage(part.mountpoint)._asdict()  # استفاده از حافظه برای هر پارتیشن
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

            for disk in get("blockdevices", []):
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
        """استفاده از حافظه برای یک دیوایس خاص"""
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
        """بازگرداندن تمام اطلاعات به صورت دیکشنری"""
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
