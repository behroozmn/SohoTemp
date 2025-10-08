import os
import subprocess  # اجرای دستورات سیستمی در صورت نیاز
import psutil  # برای خواندن آمار سیستم
from typing import Dict, Any, Optional, List  # تایپ‌هینت برای خوانایی بهتر
import glob
import re
from pylibs.File import FileManager


def ok(data: Any, details: Any = None) -> Dict[str, Any]:
    return {
        "ok": True,
        "error": None,
        "data": data,
        "details": details or {}
    }


def fail(message: str, code: str = "disk_error", extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "ok": False,
        "error": {"code": code, "message": message, "extra": extra or {}},
        "data": None,
        "details": {}
    }

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
            output = subprocess.check_output(["lsblk", "-O", "-J"], stderr=subprocess.DEVNULL, text=True)
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

    def get_disks_wwn_mapping(self):
        """
        Returns a dict: {device_name: wwn_name} -----> {'sda': 'wwn-0x5002538d40123456', ...}
        """
        mapping = {}
        by_id_path = "/dev/disk/by-id/wwn-*"

        try:
            for link in glob.glob(by_id_path):
                target = os.readlink(link)  # Resolve symlink to get target (e.g., ../../sda)
                dev_name = os.path.basename(target)  # Extract device name (e.g., sda from ../../sda or nvme0n1 from ../../nvme0n1)
                if re.match(r'^(sd[a-z]+|nvme[0-9]+n[0-9]+|vd[a-z]+|hd[a-z]+)$', dev_name):  # Only consider block devices that look like disks (not partitions)
                    # wwn_name = os.path.basename(link)
                    d = "/dev/" + dev_name
                    # mapping[dev_name] = wwn_name
                    mapping[d] = link
        except Exception as exc:
            return fail(str(exc))
        return ok(mapping)  # {'sdb': 'wwn-0x50014ee2139fda31', 'sda': 'wwn-0x5000000000001aa9'}

        return ok(items)

    def get_all_disks(self):
        """
        Returns a sorted list of disk device names (e.g., ['sda', 'sdb', 'nvme0n1'])
        by scanning /sys/block and excluding partitions and virtual devices.
        """
        disks = []
        block_path = "/sys/block"

        if not os.path.exists(block_path):
            raise RuntimeError("/sys/block not found – are you on Linux?")

        for entry in os.listdir(block_path):
            # Skip loop, ram, sr (CD-ROM), etc.
            if entry.startswith(('loop', 'ram', 'sr', 'fd', 'md', 'dm-', 'zram')):
                continue
            # Only include real disk-like devices
            if re.match(r'^(sd[a-z]+|nvme[0-9]+n[0-9]+|vd[a-z]+|hd[a-z]+)$', entry):
                disks.append(entry)
        return sorted(disks)  # ['nvme0n1', 'sda', 'sdb']

    def list_unpartitioned_disks(self) -> Dict[str, Any]:
        """
        List block devices that have NO partitions.
        Works for both SCSI (sda, sdb) and NVMe (nvme0n1) devices.
        """
        try:
            block_path = "/sys/block"
            if not os.path.exists(block_path):
                return fail("System does not appear to be Linux (no /sys/block).")

            unpartitioned = []

            for device in os.listdir(block_path):
                # فیلتر کردن دستگاه‌های غیردیسک
                if device.startswith(('loop', 'ram', 'sr', 'fd', 'md', 'dm-', 'zram', 'mmcblk')):
                    continue

                # فقط دستگاه‌های معتبر
                if not re.match(r'^(sd[a-z]+|nvme[0-9]+n[0-9]+|vd[a-z]+|hd[a-z]+|mmcblk[0-9]+)$', device):
                    continue

                # بررسی وجود پارتیشن: آیا زیرشاخه‌ای با نام پارتیشن وجود دارد؟
                device_dir = os.path.join(block_path, device)
                has_partition = False

                try:
                    for entry in os.listdir(device_dir):
                        # پارتیشن‌ها معمولاً با عدد شروع یا شامل 'p' هستند
                        if entry.startswith(device) and (
                                entry[len(device):].isdigit() or  # sda1, sdb2
                                (entry.startswith(device + "p") and entry[len(device) + 1:].isdigit())  # nvme0n1p1
                        ):
                            has_partition = True
                            break
                except OSError:
                    # اگر دسترسی نبود، فرض می‌کنیم پارتیشن ندارد (کم‌احتمال)
                    pass

                if not has_partition:
                    unpartitioned.append(device)

            unpartitioned.sort()
            return ok(unpartitioned, details={"count": len(unpartitioned)})

        except PermissionError:
            return fail("Permission denied accessing /sys/block")
        except Exception as e:
            return fail(f"Unexpected error: {str(e)}", extra={"exception": str(e)})

    def wipe_disk(self, device_path: str) -> Dict[str, Any]:

        device_path = device_path.strip()
        device_name = os.path.basename(device_path)

        if not isinstance(device_path, str) or not device_path.strip():
            return fail("Device name must be a non-empty string.")

        # اعتبارسنجی نام دستگاه (جلوگیری از command injection و دستگاه‌های نامعتبر)
        if not re.match(r'^(sd[a-z]+|nvme[0-9]+n[0-9]+|vd[a-z]+|hd[a-z]+|mmcblk[0-9]+)$', device_name):
            return fail(f"Invalid device name: {device_name}. Only block devices like sda, nvme0n1 are allowed.")

        # بررسی وجود دستگاه
        try:
            if not os.path.exists(device_path):
                return fail(f"Device not found: {device_path}")
        except Exception as e:
            return fail(f"Error checking device path: {str(e)}")

        try:
            # اجرای دستور wipefs
            result = subprocess.run(
                ["/usr/bin/sudo","/usr/sbin/wipefs", "-a", device_path],
                capture_output=True,
                text=True,
                check=False,
                timeout=60
            )

            if result.returncode == 0:
                return ok(
                    {"device": device_name},
                    details="All filesystem signatures successfully wiped."
                )
            else:
                stderr = result.stderr.strip() or result.stdout.strip()
                return fail(
                    f"wipefs failed on {device_name}: {stderr}",
                    code="wipefs_failed",
                    extra={"stderr": result.stderr, "stdout": result.stdout}
                )

        except subprocess.TimeoutExpired:
            return fail(f"wipefs timed out on {device_name}", code="timeout")
        except FileNotFoundError:
            return fail("wipefs command not found. Install util-linux package.", code="command_not_found")
        except Exception as e:
            return fail(f"Exception during wipefs: {str(e)}", extra={"exception": str(e)})

    def wipe_disk_clean(self, device_path: str) -> Dict[str, Any]:
        """
        پاک‌سازی کامل یک دیسک/پارتیشن از هر اثر ZFS یا فایل‌سیستم.

        مراحل:
        1. اجرای `zfs clearlabel` روی device_path (مثلاً /dev/sda1)
        2. استخراج نام دیسک اصلی (مثلاً از /dev/sda1 → /dev/sda)
        3. اجرای `wipefs -af` روی دیسک اصلی

        Args:
            device_path (str): مسیر دستگاه (مثلاً "/dev/sda1" یا "/dev/sda")

        Returns:
            Dict: نتیجه عملیات
        """
        try:
            if not device_path or not device_path.startswith("/dev/"):
                return fail("مسیر دستگاه نامعتبر است.", "invalid_device_path")

            # مرحله 1: حذف لیبل ZFS (اگر وجود داشته باشد)
            try:
                subprocess.run(
                    ["/usr/bin/sudo","/usr/bin/zfs", "clearlabel", f"{device_path}1"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except subprocess.CalledProcessError as e:
                # اگر لیبل ZFS نبود، خطا را نادیده بگیر (طبیعی است)
                pass

            subprocess.run(
                ["/usr/bin/sudo","/usr/sbin/wipefs", "-a", device_path],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            return ok({
                "message": "دیسک با موفقیت پاک‌سازی شد.",
                "device_path": device_path,
            })

        except subprocess.CalledProcessError as e:
            return fail(f"خطا در اجرای دستور سیستمی: {e}", "wipe_error")
        except Exception as e:
            return fail(f"خطای غیرمنتظره: {str(e)}", "wipe_error")


# def main():
#     disk_wwn_map = get_disks_wwn_mapping()
#     all_disks = get_all_disks()
#
#     print(f"{'Device':<12} {'WWN'}")
#     print("-" * 60)
#
#     for disk in all_disks:
#         wwn = disk_wwn_map.get(disk, "N/A")
#         print(f"{disk:<12} {wwn}")

class DiskManager:
    os_disk: str = None
    disks: list = []

    def __init__(self):
        # مشکل: استفاده از : به جای = برای انتساب
        # همچنین باید از self استفاده کنید
        self.os_disk = self.get_os_disk()
        self.disks = self.get_disks_all()

    def get_disks_all(self, contain_os_disk=True, exclude: tuple = ('loop', 'ram', 'sr', 'fd', 'md', 'dm-', 'zram')):
        import os
        import re

        block_path = "/sys/block"
        if not os.path.exists(block_path):
            raise Exception("/sys/block not found – OS is not Linux?")

        disks = []
        for entry in os.listdir(block_path):
            # مشکل: exclude باید چک شود که با هر کدام از موارد شروع می‌شود یا نه
            if any(entry.startswith(excl) for excl in exclude):
                continue

            # Only include real disk-like devices
            if re.match(r'^(sd[a-z]+|nvme[0-9]+n[0-9]+|vd[a-z]+|hd[a-z]+)$', entry):
                if not contain_os_disk and entry == self.os_disk:
                    continue
                else:
                    disks.append(entry)

        disks = sorted(disks)
        return disks

    def get_os_disk(self) -> str | None:
        import os
        import psutil

        for part in psutil.disk_partitions(all=False):
            if part.mountpoint == '/':
                dev = os.path.basename(part.device)  # e.g. sda2
                # strip partition number (sda2 → sda)
                for disk in os.listdir("/sys/block"):
                    if dev.startswith(disk):
                        return disk
        return None

    def get_disk_info(self, disk: str) -> Dict[str, Optional[str]]:
        base = f"/sys/block/{disk}"
        filemanager = FileManager()
        info = {
            "disk": disk,
            "model": filemanager.get_file_content(f"{base}/device/model"),
            "vendor": filemanager.get_file_content(f"{base}/device/vendor"),
            "wwn": filemanager.get_file_content(f"{base}/device/wwid"),  # may exist depending on driver
            "device_path": os.path.realpath(base),
            "physical_block_size": filemanager.get_file_content(f"{base}/queue/physical_block_size"),
            "logical_block_size": filemanager.get_file_content(f"{base}/queue/logical_block_size"),
            "scheduler": filemanager.get_file_content(f"{base}/queue/scheduler"),
            "state": filemanager.get_file_content(f"{base}/device/state"),
        }
        return info
