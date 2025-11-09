import os
import re
import glob
from typing import Dict, Any, Optional, List, Tuple
from pylibs.file import FileManager


class DiskManager:
    """مدیریت جامع اطلاعات دیسک‌های سیستم لینوکس بدون اجرای هیچ دستور خارجی.

    این کلاس اطلاعات سخت‌افزاری (مدل، vendor، wwn)، آمار فضای ذخیره‌سازی (کل، مصرفی، آزاد) و دمای دیسک را تنها از طریق فایل‌های سیستمی کرنل (/sys, /proc) جمع‌آوری می‌کند.
    """

    SYS_BLOCK: str = "/sys/block"
    PROC_MOUNTS: str = "/proc/mounts"
    SYS_CLASS_HWMON: str = "/sys/class/hwmon"
    SYS_SCSI_DISK: str = "/sys/class/scsi_disk"

    def __init__(self) -> None:
        self.os_disk: Optional[str] = self.get_os_disk()
        self.disks: List[str] = self.get_all_disk_name()

    def get_all_disk_name(self, contain_os_disk: bool = True, exclude: tuple = ('loop', 'ram', 'sr', 'fd', 'md', 'dm-', 'zram')) -> List[str]:
        """بازیابی لیست تمام دیسک‌های فیزیکی سیستم با فیلتر کردن دستگاه‌های مجازی.

        Args:
            contain_os_disk (bool): آیا دیسک سیستم‌عامل هم شامل شود؟
            exclude (tuple): پیشوندهایی که باید نادیده گرفته شوند.
        Returns: List[str]: لیستی از نام دیسک‌ها (مثل ['sda', 'nvme0n1']).
        Raises: RuntimeError: اگر سیستم‌عامل لینوکس نباشد.
        """
        if not os.path.exists(self.SYS_BLOCK):
            raise RuntimeError("/sys/block not found – OS is not Linux?")

        found_disks: List[str] = []
        try:
            for entry in os.listdir(self.SYS_BLOCK):
                if any(entry.startswith(prefix) for prefix in exclude):
                    continue
                if re.match(r'^(sd[a-z]+|nvme[0-9]+n[0-9]+|vd[a-z]+|hd[a-z]+)$', entry):
                    if not contain_os_disk and entry == self.os_disk:
                        continue
                    found_disks.append(entry)
        except (OSError, IOError) as e:
            # ثبت خطا یا پرش به لیست خالی
            pass
        return sorted(found_disks)

    def get_os_disk(self) -> Optional[str]:
        """شناسایی دیسکی که سیستم‌عامل روی آن نصب شده (با mountpoint = /).

        Returns: Optional[str]: نام دیسک سیستم‌عامل (مثل 'sda') یا None در صورت شکست.
        """
        try:
            with open(self.PROC_MOUNTS, 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 3 and parts[1] == '/' and parts[0].startswith('/dev/'):
                        dev_name = os.path.basename(parts[0])  # e.g., 'sda2'
                        for disk in os.listdir(self.SYS_BLOCK):
                            if dev_name.startswith(disk):
                                return disk
        except (OSError, IOError, ValueError):
            pass
        return None

    def get_model(self, disk: str) -> str:
        """دریافت مدل دیسک از فایل سیستمی کرنل.

        Args: disk (str): نام دیسک (مثل 'sda').
        Returns: str: نام مدل دیسک یا رشته خالی در صورت عدم دسترسی.
        """
        try:
            return FileManager.read_strip(f"/sys/block/{disk}/device/model")
        except (OSError, IOError):
            return ""

    def get_vendor(self, disk: str) -> str:
        """دریافت نام تولیدکننده (vendor) دیسک.

        Args: disk (str): نام دیسک (مثل 'sda').
        Returns: str: نام vendor یا رشته خالی در صورت عدم دسترسی.
        """
        try:
            return FileManager.read_strip(f"/sys/block/{disk}/device/vendor")
        except (OSError, IOError):
            return ""

    def get_stat(self, disk: str) -> str:
        """دریافت وضعیت فعلی دیسک (مثل 'running').
        Args:
            disk (str): نام دیسک (مثل 'sda').
        Returns: str: وضعیت دیسک یا رشته خالی در صورت عدم دسترسی.
        """
        try:
            return FileManager.read_strip(f"/sys/block/{disk}/device/state")
        except (OSError, IOError):
            return ""

    def get_physical_block_size(self, disk: str) -> str:
        """دریافت اندازه فیزیکی بلاک دیسک به بایت.

        Args: disk (str): نام دیسک (مثل 'sda').
        Returns: str: اندازه بلاک فیزیکی (معمولاً '512' یا '4096') یا رشته خالی.
        """
        try:
            return FileManager.read_strip(f"/sys/block/{disk}/queue/physical_block_size")
        except (OSError, IOError):
            return ""

    def get_logical_block_size(self, disk: str) -> str:
        """دریافت اندازه منطقی بلاک دیسک به بایت.

        Args: disk (str): نام دیسک (مثل 'sda').
        Returns: str: اندازه بلاک منطقی (معمولاً '512') یا رشته خالی.
        """
        try:
            return FileManager.read_strip(f"/sys/block/{disk}/queue/logical_block_size")
        except (OSError, IOError):
            return ""

    def get_scheduler(self, disk: str) -> str:
        """دریافت الگوریتم زمان‌بندی I/O دیسک.
        Args:
            disk (str): نام دیسک (مثل 'sda').

        Returns: str: نام scheduler (مثل 'mq-deadline [none]') یا رشته خالی.
        """
        try:
            return FileManager.read_strip(f"/sys/block/{disk}/queue/scheduler")
        except (OSError, IOError):
            return ""

    def get_wwid(self, disk: str) -> str:
        """دریافت شناسه جهانی WWID دیسک (اگر در دسترس باشد).
        Args: disk (str): نام دیسک (مثل 'sda').
        Returns: str: WWID (مثل '0x5002538d...') یا رشته خالی.
        """
        try:
            return FileManager.read_strip(f"/sys/block/{disk}/device/wwid")
        except (OSError, IOError):
            return ""

    def get_path(self, disk: str) -> str:
        """دریافت مسیر واقعی (realpath) دیسک در سیستم فایل.
        Args:
            disk (str): نام دیسک (مثل 'sda').

        Returns: str: مسیر واقعی یا رشته خالی در صورت خطا.
        """
        try:
            return os.path.realpath(f"/sys/block/{disk}")
        except (OSError, IOError):
            return ""

    def get_usage(self, disk: str) -> Dict[str, Optional[int]]:
        """محاسبه حجم کل، مصرفی، آزاد و درصد استفاده برای دیسک.
        این تابع تمام پارتیشن‌های mount شده مربوط به دیسک را بررسی می‌کند.

        Args: disk (str): نام دیسک (مثل 'sda').
        Returns: Dict[str, Optional[int]]: دیکشنری شامل:
                - total_bytes: حجم کل (بایت)
                - used_bytes: حجم مصرفی (بایت)
                - free_bytes: حجم آزاد (بایت)
                - usage_percent: درصد استفاده (0-100)
        """
        total = used = free = 0
        mount_points = []

        try:
            with open(self.PROC_MOUNTS, 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 3 or not parts[0].startswith('/dev/'):
                        continue
                    dev = parts[0]
                    mount_point = parts[1]
                    # بررسی اینکه آیا پارتیشن متعلق به دیسک ما است
                    if os.path.basename(dev).startswith(disk):
                        mount_points.append(mount_point)
        except (OSError, IOError):
            pass

        for mp in mount_points:
            try:
                stat = os.statvfs(mp)
                total += stat.f_frsize * stat.f_blocks
                free += stat.f_frsize * stat.f_bavail
                used += stat.f_frsize * (stat.f_blocks - stat.f_bfree)
            except (OSError, IOError):
                continue

        usage_percent = round(used / total * 100, 2) if total > 0 else 0.0

        return {
            "total_bytes": total if total > 0 else None,
            "used_bytes": used if total > 0 else None,
            "free_bytes": free if total > 0 else None,
            "usage_percent": usage_percent if total > 0 else None,
        }

    def get_temperature_from_hwmon(self, disk: str) -> Optional[int]:
        """سعی در خواندن دما از hwmon برای دیسک داده‌شده.

        Args: disk (str): نام دیسک (مثل 'sda').
        Returns: Optional[int]: دمای دیسک به سانتی‌گراد یا None.
        """
        if not os.path.exists(self.SYS_CLASS_HWMON):
            return None
        try:
            for hwmon_dir in os.listdir(self.SYS_CLASS_HWMON):
                hwmon_path = os.path.join(self.SYS_CLASS_HWMON, hwmon_dir)
                name_path = os.path.join(hwmon_path, "name")
                if os.path.exists(name_path):
                    name = FileManager.read_strip(name_path)
                    if disk in name or "drivetemp" in name.lower():
                        temp_path = os.path.join(hwmon_path, "temp1_input")
                        if os.path.exists(temp_path):
                            temp_raw = FileManager.read_strip(temp_path)
                            if temp_raw.isdigit():
                                return int(temp_raw) // 1000  # µ°C → °C
        except (OSError, ValueError, IOError):
            pass
        return None

    def get_temperature_from_scsi(self, disk: str) -> Optional[int]:
        """سعی در خواندن دما از scsi_disk برای دیسک‌های SCSI/SATA.

        Args: disk (str): نام دیسک (مثل 'sda').
        Returns: Optional[int]: دمای دیسک به سانتی‌گراد یا None.
        """
        if not os.path.exists(self.SYS_SCSI_DISK):
            return None
        try:
            for scsi_entry in os.listdir(self.SYS_SCSI_DISK):
                device_path = os.path.join(self.SYS_SCSI_DISK, scsi_entry, "device")
                block_link = os.path.join(device_path, "block")
                if os.path.exists(block_link):
                    try:
                        resolved = os.readlink(block_link)
                        if resolved == disk:
                            temp_path = os.path.join(device_path, "temperature")
                            if os.path.exists(temp_path):
                                temp_str = FileManager.read_strip(temp_path)
                                if temp_str.isdigit():
                                    return int(temp_str)
                    except (OSError, ValueError):
                        continue
        except (OSError, IOError):
            pass
        return None

    def get_temperature(self, disk: str) -> Optional[int]:
        """دریافت دمای دیسک از منابع مختلف سیستم.

        Args: disk (str): نام دیسک (مثل 'sda').
        Returns: Optional[int]: دمای دیسک به سانتی‌گراد یا None.
        """
        temp = self.get_temperature_from_hwmon(disk)
        if temp is not None:
            return temp
        return self.get_temperature_from_scsi(disk)

    def get_disk_info(self, disk: str) -> Dict[str, Any]:
        """جمع‌آوری تمام اطلاعات یک دیسک خاص.
        Args: disk (str): نام دیسک (مثل 'sda').
        Returns: Dict[str, Any]: دیکشنری کامل اطلاعات دیسک.
        """
        usage = self.get_usage(disk)
        return {
            "disk": disk,
            "model": self.get_model(disk),
            "vendor": self.get_vendor(disk),
            "state": self.get_stat(disk),
            "device_path": self.get_path(disk),
            "physical_block_size": self.get_physical_block_size(disk),
            "logical_block_size": self.get_logical_block_size(disk),
            "scheduler": self.get_scheduler(disk),
            "wwid": self.get_wwid(disk),
            "total_bytes": usage["total_bytes"],
            "used_bytes": usage["used_bytes"],
            "free_bytes": usage["free_bytes"],
            "usage_percent": usage["usage_percent"],
            "temperature_celsius": self.get_temperature(disk),
            "wwn": self.get_wwn(disk),
            "uuid": self.get_uuid(disk),
            "slot_number": self.get_slot_number(disk),
        }

    def get_all_disks_info(self) -> List[Dict[str, Any]]:
        """جمع‌آوری اطلاعات تمام دیسک‌های سیستم.

        Returns: List[Dict[str, Any]]: لیستی از دیکشنری‌های اطلاعات دیسک.
        """
        return [self.get_disk_info(disk) for disk in self.disks]

    def get_wwn(self, disk: str) -> str:
        """دریافت World Wide Name (WWN) دیسک از فایل‌های سیستمی کرنل.

        WWN معمولاً در دیسک‌های enterprise (SCSI/SAS) در دسترس است.

        Args: disk (str): نام دیسک (مثل 'sda').
        Returns: str: WWN (مثل '0x5002538d40b3f2a3') یا رشته خالی اگر در دسترس نباشد.
        """
        # مسیرهای رایج برای WWN در لینوکس
        wwn_paths = [
            f"/sys/block/{disk}/device/wwid",
            f"/sys/block/{disk}/device/vpd_pg83",
            f"/sys/block/{disk}/wwid",  # برخی درایورها مستقیم اینجا می‌نویسند
        ]
        for path in wwn_paths:
            try:
                with open(path, 'r') as f:
                    content = f.read().strip()
                    if content and ("0x" in content or "naa." in content.lower()):
                        return content
            except (OSError, IOError):
                continue
        return ""

    def get_uuid(self, disk: str) -> Optional[str]:
        """دریافت UUID مربوط به پارتیشن‌های دیسک از سیستم فایل /dev/disk/by-uuid/.

        این متد اولین UUID مرتبط با هر پارتیشن روی دیسک را برمی‌گرداند.
        توجه: UUID متعلق به پارتیشن است، نه کل دیسک.

        Args: disk (str): نام دیسک (مثل 'sda').
        Returns: Optional[str]: UUID (مثل '123e4567-e89b-12d3-a456-426614174000') یا None.
        """
        try:
            # الگوی پارتیشن‌های مربوط به دیسک: sda1, sda2, nvme0n1p1, ...
            partition_pattern = f"/dev/{disk}[0-9]*"
            partitions = glob.glob(partition_pattern)

            # همچنین برای NVMe: nvme0n1p1, nvme0n1p2, ...
            if "nvme" in disk:
                partition_pattern = f"/dev/{disk}p[0-9]*"
                partitions += glob.glob(partition_pattern)

            # گشتن در /dev/disk/by-uuid/
            uuid_dir = "/dev/disk/by-uuid"
            if not os.path.exists(uuid_dir):
                return None

            for uuid_name in os.listdir(uuid_dir):
                uuid_path = os.path.join(uuid_dir, uuid_name)
                try:
                    # بررسی اینکه آیا این UUID متعلق به یکی از پارتیشن‌های دیسک است
                    resolved = os.path.realpath(uuid_path)
                    if any(resolved == part for part in partitions):
                        return uuid_name
                except (OSError, IOError):
                    continue
        except (OSError, IOError):
            pass
        return None

    def get_slot_number(self, disk: str) -> Optional[str]:
        """دریافت شماره اسلات (slot) دیسک از فایل‌های سیستمی.

        این اطلاعات معمولاً در سرورهای enterprise (با backplane یا enclosure) در دسترس است.
        مسیرهای رایج: /sys/block/sda/device/slot, /sys/class/scsi_disk/*/device/enclosure*

        Args: disk (str): نام دیسک (مثل 'sda').
        Returns: Optional[str]: شماره اسلات (مثل '2') یا None اگر در دسترس نباشد.
        """
        # روش ۱: فایل مستقیم slot
        slot_path = f"/sys/block/{disk}/device/slot"
        if os.path.exists(slot_path):
            try:
                with open(slot_path, 'r') as f:
                    return f.read().strip()
            except (OSError, IOError):
                pass

        # روش ۲: جستجو در scsi_disk برای enclosure
        scsi_base = "/sys/class/scsi_disk"
        if os.path.exists(scsi_base):
            try:
                for entry in os.listdir(scsi_base):
                    device_path = os.path.join(scsi_base, entry, "device")
                    block_link = os.path.join(device_path, "block")
                    if os.path.exists(block_link):
                        try:
                            resolved = os.readlink(block_link)
                            if resolved == disk:
                                # جستجوی فایل‌های مرتبط با enclosure/slot
                                for fname in os.listdir(device_path):
                                    if "enclosure" in fname or "slot" in fname:
                                        slot_val = FileManager.read_strip(os.path.join(device_path, fname))
                                        if slot_val.isdigit():
                                            return slot_val
                        except (OSError, ValueError):
                            continue
            except (OSError, IOError):
                pass

        return None
