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

    def get_usage(self, disk: str) -> Dict[str, Optional[float]]:
        """
        محاسبه حجم کل، مصرفی، آزاد و درصد استفاده برای دیسک.
        این تابع تمام پارتیشن‌های mount شده مربوط به دیسک را بررسی می‌کند.

        Args:
            disk (str): نام دیسک (مثل 'sda', 'nvme0n1', 'mmcblk0').

        Returns:
            Dict[str, Optional[float]]: دیکشنری شامل:
                - total_bytes: حجم کل (بایت)
                - used_bytes: حجم مصرفی (بایت)
                - free_bytes: حجم آزاد (بایت)
                - usage_percent: درصد استفاده (0-100)
        """
        total = used = free = 0
        mount_points = []

        # ساخت الگوی regex برای پارتیشن‌های معتبر
        if disk.startswith("nvme") or disk.startswith("mmcblk"):
            # NVMe: nvme0n1 → nvme0n1p1, mmcblk0 → mmcblk0p1
            partition_pattern = re.compile(rf"^{re.escape(disk)}p\d+$")
        else:
            # SATA/SCSI: sda → sda1, sda10, ...
            partition_pattern = re.compile(rf"^{re.escape(disk)}\d+$")

        try:
            with open(self.PROC_MOUNTS, 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 3 or not parts[0].startswith('/dev/'):
                        continue
                    dev_path = parts[0]  # مثل /dev/sda1
                    mount_point = parts[1]
                    dev_name = os.path.basename(dev_path)  # مثل sda1

                    # بررسی اینکه آیا پارتیشن متعلق به دیسک ما است
                    if partition_pattern.match(dev_name):
                        mount_points.append(mount_point)
        except (OSError, IOError):
            pass

        # جمع‌آوری آمار فضا
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
            "type": self.get_disk_type(disk),
        }

    def get_all_disks_info(self) -> List[Dict[str, Any]]:
        """جمع‌آوری اطلاعات تمام دیسک‌های سیستم.

        Returns: List[Dict[str, Any]]: لیستی از دیکشنری‌های اطلاعات دیسک.
        """
        return [self.get_disk_info(disk) for disk in self.disks]

    def get_wwn(self, disk: str) -> str:
        by_id_path = "/dev/disk/by-id"
        if not os.path.exists(by_id_path):
            return ""

        try:
            wwn_links = glob.glob(os.path.join(by_id_path, "wwn-*")) # الگوی لینک‌های WWN: wwn-*
            target_dev = f"../../{disk}"

            for link in wwn_links:
                try:
                    if os.path.realpath(link) == f"/dev/{disk}":  # بررسی مقصد لینک
                        return os.path.basename(link)  # نام فایل (مثل 'wwn-0x5000c500e8272848') را برگردان
                except (OSError, IOError):
                    continue
        except (OSError, IOError):
            pass

        return ""

    def get_uuid(self, disk: str) -> Optional[str]:
        """
        دریافت UUID مربوط به اولین پارتیشن معتبر روی دیسک از طریق /dev/disk/by-uuid/.

        این متد بدون اجرای هیچ دستور لینوکسی (مثل blkid) عمل می‌کند و فقط از ساختار
        سیستم فایل لینوکس (/dev/disk/by-uuid و /sys/block) استفاده می‌کند.

        توجه: UUID متعلق به پارتیشن است، نه دیسک خام. اگر دیسک بدون پارتیشن باشد، None برمی‌گردد.

        Args:
            disk (str): نام دیسک (مثل 'sda', 'nvme0n1', 'mmcblk0').

        Returns:
            Optional[str]: UUID پارتیشن (مثل 'a1b2c3d4-...') یا None اگر یافت نشد.
        """
        try:
            # مرحله 1: دریافت لیست واقعی پارتیشن‌ها از /sys/block/{disk}/
            sys_disk_path = f"/sys/block/{disk}"
            if not os.path.exists(sys_disk_path):
                return None

            partitions: List[str] = []
            for entry in os.listdir(sys_disk_path):
                # پارتیشن‌ها زیردایرکتوری هستند و با نام دیسک شروع می‌شوند
                if entry.startswith(disk) and entry != disk:
                    partitions.append(f"/dev/{entry}")

            if not partitions:
                return None

            # مرحله 2: جستجو در /dev/disk/by-uuid/
            uuid_dir = "/dev/disk/by-uuid"
            if not os.path.exists(uuid_dir):
                return None

            # مرحله 3: بررسی هر UUID برای تطابق با پارتیشن‌های دیسک
            for uuid_name in sorted(os.listdir(uuid_dir)):  # مرتب‌سازی برای پیش‌بینی‌پذیری
                uuid_path = os.path.join(uuid_dir, uuid_name)
                try:
                    resolved = os.path.realpath(uuid_path)
                    if resolved in partitions:
                        return uuid_name
                except (OSError, IOError):
                    continue

        except (OSError, IOError, ValueError):
            # هرگونه خطا به صورت ایمن نادیده گرفته می‌شود
            pass

        return None

    def get_slot_number(self, disk: str) -> Optional[str]:
        """
        دریافت شماره اسلات (slot) دیسک از فایل‌های سیستمی.

        اولویت‌ها:
        1. فایل مستقیم `/sys/block/{disk}/device/slot`
        2. فایل‌های enclosure در `/sys/class/scsi_disk/`
        3. استخراج از مسیر دستگاه (device_path) مانند:
           /sys/devices/.../target3:0:0/3:0:0:0/block/sdd → slot = '3'

        Args:
            disk (str): نام دیسک (مثل 'sda').

        Returns:
            Optional[str]: شماره اسلات (مثل '3') یا None اگر در دسترس نباشد.
        """
        # روش ۱: فایل مستقیم slot
        slot_path = f"/sys/block/{disk}/device/slot"
        if os.path.exists(slot_path):
            try:
                return self._read_file(slot_path)
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
                                for fname in os.listdir(device_path):
                                    if "enclosure" in fname or "slot" in fname:
                                        slot_val = self._read_file(os.path.join(device_path, fname))
                                        if slot_val.isdigit():
                                            return slot_val
                        except (OSError, ValueError):
                            continue
            except (OSError, IOError):
                pass

        # روش ۳: استخراج از مسیر device_path
        try:
            device_path = os.path.realpath(f"/sys/block/{disk}")
            # مسیر نمونه: /sys/devices/pci0000:00/.../target3:0:0/3:0:0:0/block/sdd
            # ما به دنبال الگویی مثل ".../3:0:0:0/block/sdd" هستیم
            match = re.search(r'/(\d+):0:0:0/block/' + re.escape(disk) + r'$', device_path)
            if match:
                return match.group(1)

            # یا الگوی targetX:0:0
            match2 = re.search(r'/target(\d+):0:0/', device_path)
            if match2:
                return match2.group(1)
        except (OSError, IOError, TypeError):
            pass

        return None

    def get_disk_type(self, disk: str) -> str:
        """
        تشخیص نوع دیسک (NVMe, SATA, SCSI, VirtIO, MMC, IDE, و غیره) بدون اجرای دستور.

        این تابع از ساختار مسیر دستگاه در /sys استفاده می‌کند تا نوع کنترلر یا پروتکل را شناسایی کند.

        Args:
            disk (str): نام دیسک (مثل 'sda', 'nvme0n1', 'mmcblk0').

        Returns:
            str: نوع دیسک. مقادیر ممکن:
                - 'nvme'
                - 'sata'
                - 'scsi'
                - 'virtio'
                - 'mmc'
                - 'ide'
                - 'usb'
                - 'unknown'
        """
        try:
            # دریافت مسیر واقعی دستگاه (realpath)
            sys_block_path = f"/sys/block/{disk}"
            if not os.path.exists(sys_block_path):
                return "unknown"

            # رسیدن به device symlink
            device_path = os.path.realpath(os.path.join(sys_block_path, "device"))
            device_path_str = device_path.lower()

            # تشخیص بر اساس نام یا مسیر دستگاه
            if "nvme" in device_path_str or disk.startswith("nvme"):
                return "nvme"
            elif "virtio" in device_path_str or disk.startswith("vd"):
                return "virtio"
            elif "mmc" in device_path_str or disk.startswith("mmcblk"):
                return "mmc"
            elif "usb" in device_path_str:
                return "usb"
            elif "ide" in device_path_str or disk.startswith("hd"):
                return "ide"
            elif "scsi" in device_path_str or any(
                    disk.startswith(prefix) for prefix in ("sd", "sr")
            ):
                # اکنون باید بین SATA و SCSI تمایز بگذاریم
                # SATA دیسک‌ها معمولاً از طریق کنترلرهای AHCI/ATA به عنوان SCSI در معرض هستند
                # اما مسیر آن‌ها شامل 'ata' می‌شود
                if "ata" in device_path_str:
                    return "sata"
                else:
                    return "scsi"
            else:
                return "unknown"

        except (OSError, IOError, ValueError):
            return "unknown"

    def has_partitions(self, disk: str) -> bool:
        """آیا دیسک حداقل یک پارتیشن دارد؟"""
        sys_path = f"/sys/block/{disk}"
        try:
            for entry in os.listdir(sys_path):
                if entry.startswith(disk) and entry != disk:
                    return True
        except (OSError, IOError):
            pass
        return False