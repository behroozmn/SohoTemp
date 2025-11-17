#soho_core_api/pylibs/disk.py
import os
import re
import glob
import subprocess
from typing import Dict, Any, Optional, List, Tuple
from pylibs.file import FileManager


class DiskManager:
    """مدیریت جامع اطلاعات دیسک‌های سیستم لینوکس بدون اجرای دستور خارجی.

    این کلاس اطلاعات سخت‌افزاری (مدل، vendor، wwn)، آمار فضای ذخیره‌سازی (کل، مصرفی، آزاد)
    و دمای دیسک را فقط از طریق فایل‌های سیستمی کرنل (/sys, /proc) جمع‌آوری می‌کند.
    """

    # مسیرهای ثابت سیستم
    SYS_BLOCK: str = "/sys/block"
    PROC_MOUNTS: str = "/proc/mounts"
    SYS_CLASS_HWMON: str = "/sys/class/hwmon"
    SYS_SCSI_DISK: str = "/sys/class/scsi_disk"

    # الگوی دستگاه‌های بلاکی معتبر
    VALID_DISK_PATTERN: str = r'^(sd[a-z]+|nvme[0-9]+n[0-9]+|vd[a-z]+|hd[a-z]+)$'

    # پیشوندهای دستگاه‌های مجازی برای فیلتر کردن
    EXCLUDED_PREFIXES: Tuple[str, ...] = ('loop', 'ram', 'sr', 'fd', 'md', 'dm-', 'zram')

    def __init__(self) -> None:
        """سازنده کلاس — محاسبه دیسک سیستم‌عامل و لیست تمام دیسک‌ها."""
        self.os_disk: Optional[str] = self.get_os_disk()
        self.disks: List[str] = self._get_all_disk_names()

    def _is_valid_device_name(self, device_name: str) -> bool:
        """بررسی اعتبار نام دستگاه بلاکی.

        Args:
            device_name (str): نام دستگاه (مثل 'sda' یا 'nvme0n1').

        Returns:
            bool: مقدار «ترو» اگر نام معتبر باشد.
        """
        return bool(re.match(self.VALID_DISK_PATTERN, device_name))

    def _is_block_device(self, device_name: str) -> bool:
        """بررسی اینکه آیا نام داده‌شده مربوط به یک بلاک دیوایس است.

        Args:
            device_name (str): نام دستگاه.

        Returns:
            bool: مقدار «ترو» اگر بلاک دیوایس باشد.
        """
        return os.path.exists(f"{self.SYS_BLOCK}/{device_name}")

    def _get_all_disk_names(self, contain_os_disk: bool = True) -> List[str]:
        """بازیابی لیست تمام دیسک‌های فیزیکی سیستم با فیلتر کردن دستگاه‌های مجازی.

        Args:
            contain_os_disk (bool): آیا دیسک سیستم‌عامل هم شامل شود؟

        Returns:
            List[str]: لیستی از نام دیسک‌ها (مثل ['sda', 'nvme0n1']).

        Raises:
            RuntimeError: اگر سیستم‌عامل لینوکس نباشد.
        """
        if not os.path.exists(self.SYS_BLOCK):
            raise RuntimeError("/sys/block not found – OS is not Linux?")

        found_disks: List[str] = []
        try:
            for entry in os.listdir(self.SYS_BLOCK):
                if any(entry.startswith(prefix) for prefix in self.EXCLUDED_PREFIXES):
                    continue
                if self._is_valid_device_name(entry):
                    if not contain_os_disk and entry == self.os_disk:
                        continue
                    found_disks.append(entry)
        except (OSError, IOError):
            pass
        return sorted(found_disks)

    def has_os_on_disk(self, disk: str) -> bool:
        """بررسی اینکه آیا سیستم‌عامل روی دیسک داده‌شده نصب شده است.

        Args:
            disk (str): نام دیسک (مثل 'sda', 'nvme0n1').

        Returns:
            bool: مقدار «ترو» اگر سیستم‌عامل روی این دیسک نصب شده باشد.
        """
        if not isinstance(disk, str):
            return False
        return disk == self.os_disk

    def has_partitions(self, disk: str) -> bool:
        """بررسی اینکه آیا دیسک حداقل یک پارتیشن دارد.

        Args:
            disk (str): نام دیسک.

        Returns:
            bool: مقدار «ترو» اگر پارتیشن داشته باشد.
        """
        sys_path = f"{self.SYS_BLOCK}/{disk}"
        try:
            for entry in os.listdir(sys_path):
                if entry.startswith(disk) and entry != disk:
                    return True
        except (OSError, IOError):
            pass
        return False

    def get_disk_name_from_partition_name(self, partition_name: str) -> Optional[str]:
        """استخراج نام دیسک اصلی از نام پارتیشن.

        مثال:
            'sda1' → 'sda'
            'nvme0n1p2' → 'nvme0n1'
            'mmcblk0p1' → 'mmcblk0'

        Args:
            partition_name (str): نام پارتیشن.

        Returns:
            Optional[str]: نام دیسک اصلی یا None اگر نام معتبر نباشد.
        """
        # بررسی NVMe
        nvme_match = re.match(r'^(nvme\d+n\d+)p\d+$', partition_name)
        if nvme_match:
            return nvme_match.group(1)

        # بررسی MMC
        mmc_match = re.match(r'^(mmcblk\d+)p\d+$', partition_name)
        if mmc_match:
            return mmc_match.group(1)

        # بررسی SATA/SCSI
        if re.match(r'^[a-z]+\d+$', partition_name):
            base_candidate = re.sub(r'\d+$', '', partition_name)
            if base_candidate and self._is_block_device(base_candidate):
                return base_candidate

        return None

    def get_disk_type(self, disk: str) -> str:
        """تشخیص نوع دیسک بدون اجرای دستور.

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
            sys_block_path = f"{self.SYS_BLOCK}/{disk}"
            if not os.path.exists(sys_block_path):
                return "unknown"

            device_path = os.path.realpath(os.path.join(sys_block_path, "device"))
            device_path_str = device_path.lower()

            if "nvme" in device_path_str or disk.startswith("nvme"):
                return "nvme"
            if "virtio" in device_path_str or disk.startswith("vd"):
                return "virtio"
            if "mmc" in device_path_str or disk.startswith("mmcblk"):
                return "mmc"
            if "usb" in device_path_str:
                return "usb"
            if "ide" in device_path_str or disk.startswith("hd"):
                return "ide"
            if "scsi" in device_path_str or any(disk.startswith(prefix) for prefix in ("sd", "sr")):
                # تمایز SATA از SCSI بر اساس وجود 'ata' در مسیر
                return "sata" if "ata" in device_path_str else "scsi"
            return "unknown"
        except (OSError, IOError, ValueError):
            return "unknown"

    def get_slot_number(self, disk: str) -> Optional[str]:
        """دریافت شماره اسلات (slot) دیسک از فایل‌های سیستمی.

        اولویت‌ها:
        1. فایل مستقیم `/sys/block/{disk}/device/slot`
        2. فایل‌های enclosure در `/sys/class/scsi_disk/`
        3. استخراج از مسیر دستگاه

        Args:
            disk (str): نام دیسک (مثل 'sda').

        Returns:
            Optional[str]: شماره اسلات (مثل '3') یا None اگر در دسترس نباشد.
        """
        # روش ۱: فایل مستقیم slot
        slot_path = f"{self.SYS_BLOCK}/{disk}/device/slot"
        if os.path.exists(slot_path):
            return FileManager.read_strip(slot_path)

        # روش ۲: جستجو در scsi_disk برای enclosure
        if os.path.exists(self.SYS_SCSI_DISK):
            try:
                for entry in os.listdir(self.SYS_SCSI_DISK):
                    device_path = os.path.join(self.SYS_SCSI_DISK, entry, "device")
                    block_link = os.path.join(device_path, "block")
                    if os.path.exists(block_link):
                        try:
                            resolved = os.readlink(block_link)
                            if resolved == disk:
                                for fname in os.listdir(device_path):
                                    if "enclosure" in fname or "slot" in fname:
                                        slot_val = FileManager.read_strip(os.path.join(device_path, fname))
                                        if slot_val.isdigit():
                                            return slot_val
                        except (OSError, ValueError):
                            continue
            except (OSError, IOError):
                pass

        # روش ۳: استخراج از مسیر device_path
        try:
            device_path = os.path.realpath(f"{self.SYS_BLOCK}/{disk}")
            # جستجوی الگوی targetX:0:0
            match = re.search(r'/target(\d+):0:0/', device_path)
            if match:
                return match.group(1)
            # جستجوی الگوی X:0:0:0/block/disk
            match2 = re.search(r'/(\d+):0:0:0/block/' + re.escape(disk) + r'$', device_path)
            if match2:
                return match2.group(1)
        except (OSError, IOError, TypeError):
            pass

        return None

    def get_model(self, disk: str) -> str:
        """دریافت مدل دیسک از فایل سیستمی کرنل.

        Args:
            disk (str): نام دیسک (مثل 'sda').

        Returns:
            str: نام مدل دیسک یا رشته خالی در صورت عدم دسترسی.
        """
        return FileManager.read_strip(f"{self.SYS_BLOCK}/{disk}/device/model")

    def get_vendor(self, disk: str) -> str:
        """دریافت نام تولیدکننده (vendor) دیسک.

        Args:
            disk (str): نام دیسک (مثل 'sda').

        Returns:
            str: نام vendor یا رشته خالی در صورت عدم دسترسی.
        """
        return FileManager.read_strip(f"{self.SYS_BLOCK}/{disk}/device/vendor")

    def get_stat(self, disk: str) -> str:
        """دریافت وضعیت فعلی دیسک (مثل 'running').

        Args:
            disk (str): نام دیسک (مثل 'sda').

        Returns:
            str: وضعیت دیسک یا رشته خالی در صورت عدم دسترسی.
        """
        return FileManager.read_strip(f"{self.SYS_BLOCK}/{disk}/device/state")

    def get_physical_block_size(self, disk: str) -> str:
        """دریافت اندازه فیزیکی بلاک دیسک به بایت.

        Args:
            disk (str): نام دیسک (مثل 'sda').

        Returns:
            str: اندازه بلاک فیزیکی (معمولاً '512' یا '4096') یا رشته خالی.
        """
        return FileManager.read_strip(f"{self.SYS_BLOCK}/{disk}/queue/physical_block_size")

    def get_logical_block_size(self, disk: str) -> str:
        """دریافت اندازه منطقی بلاک دیسک به بایت.

        Args:
            disk (str): نام دیسک (مثل 'sda').

        Returns:
            str: اندازه بلاک منطقی (معمولاً '512') یا رشته خالی.
        """
        return FileManager.read_strip(f"{self.SYS_BLOCK}/{disk}/queue/logical_block_size")

    def get_scheduler(self, disk: str) -> str:
        """دریافت الگوریتم زمان‌بندی I/O دیسک.

        Args:
            disk (str): نام دیسک (مثل 'sda').

        Returns:
            str: نام scheduler (مثل 'mq-deadline [none]') یا رشته خالی.
        """
        return FileManager.read_strip(f"{self.SYS_BLOCK}/{disk}/queue/scheduler")

    def get_wwid(self, disk: str) -> str:
        """دریافت شناسه جهانی WWID دیسک (اگر در دسترس باشد).

        Args:
            disk (str): نام دیسک (مثل 'sda').

        Returns:
            str: WWID (مثل '0x5002538d...') یا رشته خالی.
        """
        return FileManager.read_strip(f"{self.SYS_BLOCK}/{disk}/device/wwid")

    def get_path(self, disk: str) -> str:
        """دریافت مسیر واقعی (realpath) دیسک در سیستم فایل.

        Args:
            disk (str): نام دیسک (مثل 'sda').

        Returns:
            str: مسیر واقعی یا رشته خالی در صورت خطا.
        """
        try:
            return os.path.realpath(f"{self.SYS_BLOCK}/{disk}")
        except (OSError, IOError):
            return ""

    def get_total_size(self, entry: str) -> Optional[int]:
        """دریافت حجم کل (به بایت) برای یک دیسک یا پارتیشن.

        Args:
            entry (str): نام دیسک یا پارتیشن (مثل 'sda', 'sda1', 'nvme0n1', 'nvme0n1p1').

        Returns:
            Optional[int]: حجم به بایت یا None در صورت خطا.
        """
        try:
            base_disk = entry
            is_partition = False

            # تشخیص پارتیشن و استخراج دیسک اصلی
            base_disk = self.get_disk_name_from_partition_name(entry)
            if base_disk is not None:
                is_partition = True
            else:
                # اگر پارتیشن نبود، خود ورودی دیسک اصلی است
                base_disk = entry

            # تعیین مسیر فایل size
            if is_partition:
                size_path = f"{self.SYS_BLOCK}/{base_disk}/{entry}/size"
            else:
                size_path = f"{self.SYS_BLOCK}/{entry}/size"

            if os.path.exists(size_path):
                raw = FileManager.read_strip(size_path)
                if raw.isdigit():
                    return int(raw) * 512  # سکتور → بایت
        except (OSError, IOError, ValueError):
            pass
        return None

    def get_uuid(self, disk: str) -> Optional[str]:
        """دریافت UUID مربوط به اولین پارتیشن معتبر روی دیسک.

        این متد بدون اجرای دستور لینوکسی عمل می‌کند.

        Args:
            disk (str): نام دیسک (مثل 'sda', 'nvme0n1').

        Returns:
            Optional[str]: UUID پارتیشن یا None.
        """
        try:
            uuid_dir = "/dev/disk/by-uuid"
            if not os.path.exists(uuid_dir):
                return None

            by_path_dir = "/dev/disk/by-path"
            if not os.path.exists(by_path_dir):
                return None

            # جمع‌آوری دستگاه‌های مرتبط با دیسک
            related_devices = set()
            for entry in os.listdir(by_path_dir):
                path = os.path.join(by_path_dir, entry)
                try:
                    resolved = os.path.realpath(path)
                    if resolved.startswith(f"/dev/{disk}"):
                        related_devices.add(resolved)
                except (OSError, IOError):
                    continue

            if not related_devices:
                # fallback به روش مستقیم
                sys_disk_path = f"{self.SYS_BLOCK}/{disk}"
                if os.path.exists(sys_disk_path):
                    for entry in os.listdir(sys_disk_path):
                        if entry != disk and entry.startswith(disk):
                            if self._is_valid_device_name(entry) or entry.startswith(disk):
                                related_devices.add(f"/dev/{entry}")

            if not related_devices:
                return None

            # بررسی UUIDها
            for uuid_name in sorted(os.listdir(uuid_dir)):
                uuid_path = os.path.join(uuid_dir, uuid_name)
                try:
                    resolved = os.path.realpath(uuid_path)
                    if resolved in related_devices:
                        return uuid_name
                except (OSError, IOError):
                    continue
        except (OSError, IOError, ValueError):
            pass
        return None

    def get_wwn_by_entry(self, entry: str) -> str:
        """دریافت WWN یا شناسه منحصر به فرد برای یک دیسک یا پارتیشن.

        Args:
            entry (str): نام دیسک یا پارتیشن (مثل 'sda', 'sda1', 'nvme0n1', 'nvme0n1p1').

        Returns:
            str: شناسه منحصربه‌فرد یا رشته خالی.
        """
        by_id_path = "/dev/disk/by-id"
        if not os.path.exists(by_id_path):
            return ""

        try:
            target_real_path = os.path.realpath(f"/dev/{entry}")
            all_links = glob.glob(os.path.join(by_id_path, "*"))

            wwn_candidate = None
            nvme_candidate = None

            for link in all_links:
                try:
                    link_real = os.path.realpath(link)
                    if link_real == target_real_path:
                        basename = os.path.basename(link)
                        if basename.startswith("wwn-"):
                            return basename
                        if basename.startswith("nvme-nvme."):
                            nvme_candidate = basename
                        elif basename.startswith("nvme-") and nvme_candidate is None:
                            nvme_candidate = basename
                except (OSError, IOError):
                    continue

            return nvme_candidate or ""
        except (OSError, IOError):
            return ""

    def get_os_disk(self) -> Optional[str]:
        """شناسایی دیسکی که سیستم‌عامل روی آن نصب شده (با mountpoint = /).

        Returns:
            Optional[str]: نام دیسک سیستم‌عامل (مثل 'sda') یا None در صورت شکست.
        """
        try:
            with open(self.PROC_MOUNTS, 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 3 and parts[1] == '/' and parts[0].startswith('/dev/'):
                        dev_name = os.path.basename(parts[0])  # مثال: 'sda2'
                        for disk in os.listdir(self.SYS_BLOCK):
                            if dev_name.startswith(disk):
                                return disk
        except (OSError, IOError, ValueError):
            pass
        return None

    def get_partition_mount_info(self, partition_name: str) -> Optional[Dict[str, Any]]:
        """دریافت اطلاعات mount یک پارتیشن خاص از /proc/mounts.

        Args:
            partition_name (str): نام پارتیشن بدون مسیر (مثل 'nvme0n1p2', 'sda1').

        Returns:
            Optional[Dict[str, Any]]: اطلاعات پارتیشن یا None اگر mount نشده باشد.
        """
        device_path = f"/dev/{partition_name}"
        try:
            with open(self.PROC_MOUNTS, 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 6:
                        continue
                    if parts[0] == device_path:
                        return {
                            "device": parts[0],
                            "mount_point": parts[1],
                            "filesystem": parts[2],
                            "options": parts[3].split(','),
                            "dump": int(parts[4]),
                            "fsck": int(parts[5]),
                        }
        except (OSError, IOError, ValueError):
            pass
        return None

    def get_mounted_disk_size_usage(self, disk: str) -> Dict[str, Optional[float]]:
        """محاسبه حجم کل، مصرفی، آزاد و درصد استفاده برای دیسک.

        Args:
            disk (str): نام دیسک (مثل 'sda', 'nvme0n1', 'mmcblk0').

        Returns:
            Dict[str, Optional[float]]: دیکشنری شامل اطلاعات فضا.
        """
        # تعیین الگوی پارتیشن بر اساس نوع دیسک
        if disk.startswith(("nvme", "mmcblk")):
            partition_pattern = re.compile(rf"^{re.escape(disk)}p\d+$")
        else:
            partition_pattern = re.compile(rf"^{re.escape(disk)}\d+$")

        # یافتن نقاط mount
        mount_points: List[str] = []
        try:
            with open(self.PROC_MOUNTS, 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 3 or not parts[0].startswith('/dev/'):
                        continue
                    dev_name = os.path.basename(parts[0])
                    if partition_pattern.match(dev_name):
                        mount_points.append(parts[1])
        except (OSError, IOError):
            pass

        # محاسبه آمار فضا
        total = used = free = 0
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

    def get_temperature(self, disk: str) -> Optional[int]:
        """دریافت دمای دیسک از منابع مختلف سیستم.

        Returns:
            Optional[int]: دمای دیسک به سانتی‌گراد یا None.
        """
        # روش ۱: hwmon
        temp = self._get_temperature_from_hwmon(disk)
        if temp is not None:
            return temp

        # روش ۲: فایل temp مستقیم
        temp = self._get_temperature_from_device(disk)
        if temp is not None:
            return temp

        # روش ۳: scsi enterprise
        temp = self._get_temperature_from_scsi(disk)
        if temp is not None:
            return temp

        # روش ۴: smartctl (آخرین راه‌حل)
        return self._get_temperature_from_smartctl(disk)

    def _get_temperature_from_hwmon(self, disk: str) -> Optional[int]:
        """خواندن دما از hwmon با تطبیق مسیر دستگاه واقعی."""
        if not os.path.exists(self.SYS_CLASS_HWMON):
            return None

        try:
            disk_device_path = os.path.realpath(f"{self.SYS_BLOCK}/{disk}/device")
            for hwmon_dir in os.listdir(self.SYS_CLASS_HWMON):
                hwmon_path = os.path.join(self.SYS_CLASS_HWMON, hwmon_dir)
                device_link = os.path.join(hwmon_path, "device")
                if os.path.islink(device_link):
                    hwmon_device_path = os.path.realpath(device_link)
                    if hwmon_device_path == disk_device_path:
                        temp_path = os.path.join(hwmon_path, "temp1_input")
                        if os.path.exists(temp_path):
                            temp_raw = FileManager.read_strip(temp_path)
                            if temp_raw.lstrip('-').isdigit():
                                return int(temp_raw) // 1000
        except (OSError, ValueError, IOError):
            pass
        return None

    def _get_temperature_from_device(self, disk: str) -> Optional[int]:
        """خواندن دما مستقیماً از /sys/block/{disk}/device/temp."""
        temp_path = f"{self.SYS_BLOCK}/{disk}/device/temp"
        try:
            if os.path.exists(temp_path):
                temp_str = FileManager.read_strip(temp_path)
                if temp_str.lstrip('-').isdigit():
                    temp = int(temp_str)
                    return temp // 1000 if temp > 1000 else temp
        except (OSError, ValueError, IOError):
            pass
        return None

    def _get_temperature_from_scsi(self, disk: str) -> Optional[int]:
        """خواندن دما از scsi_disk برای دیسک‌های SCSI/SATA."""
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

    def _get_temperature_from_smartctl(self, disk: str) -> Optional[int]:
        """دریافت دمای هارد از طریق دستور smartctl برای IDهای 190 و 194."""
        try:
            device_path = f"/dev/{disk}"
            result = subprocess.run(
                ["/usr/bin/sudo", "/usr/sbin/smartctl", "-A", device_path],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )

            if result.returncode != 0 or not result.stdout:
                return None

            for line in result.stdout.splitlines():
                if re.match(r"^\s*(190|194)\s", line):
                    parts = line.split()
                    if len(parts) >= 10:
                        raw_value = parts[9]
                        match = re.match(r'^(\d+)', raw_value)
                        if match:
                            temp = int(match.group(1))
                            if 0 <= temp <= 100:
                                return temp
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError, ValueError):
            pass
        return None

    def get_disk_info(self, disk: str) -> Dict[str, Any]:
        """جمع‌آوری تمام اطلاعات یک دیسک خاص، همراه با اطلاعات پارتیشن‌ها.

        Args:
            disk (str): نام دیسک (مثل 'sda').

        Returns:
            Dict[str, Any]: دیکشنری کامل اطلاعات دیسک و پارتیشن‌ها.
        """
        has_partition = self.has_partitions(disk)
        disk_info = {
            "disk": disk,
            "model": self.get_model(disk),
            "vendor": self.get_vendor(disk),
            "state": self.get_stat(disk),
            "device_path": self.get_path(disk),
            "physical_block_size": self.get_physical_block_size(disk),
            "logical_block_size": self.get_logical_block_size(disk),
            "scheduler": self.get_scheduler(disk),
            "wwid": self.get_wwid(disk),
            "total_bytes": self.get_total_size(disk),
            "temperature_celsius": self.get_temperature(disk),
            "wwn": self.get_wwn_by_entry(disk),
            "uuid": self.get_uuid(disk),
            "slot_number": self.get_slot_number(disk),
            "type": self.get_disk_type(disk),
            "has_partition": has_partition,
        }

        # اگر پارتیشن نداشت
        if not has_partition:
            disk_info.update({
                "used_bytes": None,
                "free_bytes": None,
                "usage_percent": None,
                "partitions": []
            })
            return disk_info

        # اگر پارتیشن داشت
        usage = self.get_mounted_disk_size_usage(disk)
        disk_info.update({
            "used_bytes": usage["used_bytes"],
            "free_bytes": usage["free_bytes"],
            "usage_percent": usage["usage_percent"],
        })

        # جمع‌آوری اطلاعات پارتیشن‌ها
        partitions_info = []
        sys_disk_path = f"{self.SYS_BLOCK}/{disk}"

        try:
            for entry in os.listdir(sys_disk_path):
                if entry == disk:
                    continue
                if (disk.startswith(("nvme", "mmcblk")) and entry.startswith(disk) and len(entry) > len(disk)) or \
                   (not disk.startswith(("nvme", "mmcblk")) and entry.startswith(disk)):

                    partition_name = entry
                    partition_path = f"/dev/{partition_name}"
                    size_bytes = self.get_total_size(partition_name)
                    info_partition = self.get_partition_mount_info(partition_name)

                    # استخراج اطلاعات با مدیریت None
                    mount_point = info_partition["mount_point"] if info_partition else None
                    filesystem = info_partition["filesystem"] if info_partition else None
                    options = info_partition["options"] if info_partition else None
                    dump = info_partition["dump"] if info_partition else None
                    fsck = info_partition["fsck"] if info_partition else None

                    partitions_info.append({
                        "name": partition_name,
                        "path": partition_path,
                        "size_bytes": size_bytes,
                        "wwn": self.get_wwn_by_entry(partition_name),
                        "mount_point": mount_point,
                        "filesystem": filesystem,
                        "options": options,
                        "dump": dump,
                        "fsck": fsck,
                    })
        except (OSError, IOError):
            pass

        disk_info["partitions"] = partitions_info
        return disk_info

    def get_disks_info_all(self) -> List[Dict[str, Any]]:
        """جمع‌آوری اطلاعات تمام دیسک‌های سیستم.

        Returns:
            List[Dict[str, Any]]: لیستی از دیکشنری‌های اطلاعات دیسک.
        """
        return [self.get_disk_info(disk) for disk in self.disks]

    def disk_wipe_signatures(self, device_path: str) -> bool:
        """پاک‌کردن تمام سیگنچرهای فایل‌سیستم و پارتیشن با wipefs.

        Args:
            device_path (str): مسیر کامل دستگاه (مثل '/dev/sda').

        Returns:
            bool: مقدار «ترو» در صورت موفقیت، مقدار «فالس» در غیر این صورت.
        """
        if not isinstance(device_path, str) or not device_path.strip():
            return False

        device_path = device_path.strip()
        if not device_path.startswith("/dev/"):
            return False

        device_name = os.path.basename(device_path)
        if not self._is_valid_device_name(device_name):
            return False

        if not self._is_block_device(device_name):
            return False

        try:
            result = subprocess.run(
                ["/usr/bin/sudo", "/usr/sbin/wipefs", "-a", device_path],
                capture_output=True,
                text=True,
                timeout=120
            )
            return result.returncode == 0
        except Exception:
            return False

    def disk_clear_zfs_label(self, device_path: str) -> bool:
        """پاک‌کردن لیبل «زِد اف اس» از اولین پارتیشن یک دیسک با zpool labelclear.

        این تابع:
        1. نام دیسک را از device_path استخراج می‌کند
        2. اولین پارتیشن آن دیسک را پیدا می‌کند (مثل sda1, nvme0n1p1)
        3. دستور zpool labelclear را روی آن پارتیشن اجرا می‌کند

        Args:
            device_path (str): مسیر کامل دستگاه (مثل '/dev/sda').

        Returns:
            bool: مقدار «ترو» در صورت موفقیت یا اگر «زِد اف اس» نصب نیست، مقدار «فالس» در صورت خطا جدی.
        """
        # اعتبارسنجی اولیه - همان منطق کلاس شما
        if not isinstance(device_path, str) or not device_path.strip():
            return False

        device_path = device_path.strip()
        if not device_path.startswith("/dev/"):
            return False

        device_name = os.path.basename(device_path)
        if not self._is_valid_device_name(device_name):
            return False

        if not self._is_block_device(device_name):
            return False

        # پیدا کردن اولین پارتیشن
        sys_disk_path = f"{self.SYS_BLOCK}/{device_name}"
        partitions = []

        try:
            for entry in os.listdir(sys_disk_path):
                if entry == device_name:
                    continue
                # بررسی اینکه آیا پارتیشن است (همان منطق کلاس شما در get_disk_info)
                if (device_name.startswith(("nvme", "mmcblk")) and entry.startswith(device_name) and len(entry) > len(device_name)) or \
                        (not device_name.startswith(("nvme", "mmcblk")) and entry.startswith(device_name)):
                    partitions.append(entry)
        except (OSError, IOError):
            return False

        # اگر پارتیشنی وجود نداشت، روی خود دیسک عمل کن (برای سازگاری)
        if not partitions:
            target_path = device_path
        else:
            # مرتب‌سازی هوشمند برای پیدا کردن اولین پارتیشن (sda1 قبل از sda10)
            partitions.sort(key=lambda x: [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', x)])
            first_partition = partitions[0]
            target_path = f"/dev/{first_partition}"

        # اجرای دستور روی مسیر هدف (اولین پارتیشن یا خود دیسک)
        try:
            result = subprocess.run(
                ["/usr/bin/sudo", "/usr/bin/zpool", "labelclear", "-f", target_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode in (0, 1)
        except FileNotFoundError:
            # اگر zpool نصب نیست، فرض می‌کنیم ZFS وجود ندارد → موفقیت
            return True
        except Exception:
            return False

    def get_partition_count(self, disk: str) -> int:
        """دریافت تعداد پارتیشن‌های یک دیسک.

        Args:
            disk (str): نام دیسک (مثل 'sda', 'nvme0n1').

        Returns:
            int: تعداد پارتیشن‌ها (۰ تا n).
        """
        return len(self.get_partition_names(disk))

    def get_partition_names(self, disk: str) -> List[str]:
        """دریافت لیست نام پارتیشن‌های یک دیسک.

        این متد با استفاده از ساختار دایرکتوری /sys/block/{disk}/
        پارتیشن‌ها را شناسایی می‌کند. برای دیسک‌های NVMe و MMC هم پشتیبانی می‌شود.

        Args:
            disk (str): نام دیسک (مثل 'sda', 'nvme0n1', 'mmcblk0').

        Returns:
            List[str]: لیستی از نام پارتیشن‌ها (مثل ['sda1', 'sda2'] یا ['nvme0n1p1', 'nvme0n1p2']).
        """
        if not self._is_valid_device_name(disk) or not self._is_block_device(disk):
            return []

        sys_disk_path = f"{self.SYS_BLOCK}/{disk}"
        partition_names = []

        try:
            for entry in os.listdir(sys_disk_path):
                if entry == disk:
                    continue
                # بررسی الگوی پارتیشن برای انواع مختلف دیسک
                if disk.startswith(("nvme", "mmcblk")):
                    # مثلاً nvme0n1 → nvme0n1p1, mmcblk0 → mmcblk0p1
                    if entry.startswith(disk) and len(entry) > len(disk):
                        # بررسی اینکه بعد از نام دیسک، یک 'p' و سپس عدد بیاید
                        suffix = entry[len(disk):]
                        if re.match(r'^p\d+$', suffix):
                            partition_names.append(entry)
                else:
                    # مثلاً sda → sda1, sda10
                    if entry.startswith(disk) and entry[len(disk):].isdigit():
                        partition_names.append(entry)
        except (OSError, IOError):
            pass

        # مرتب‌سازی هوشمند: sda1 قبل از sda10
        partition_names.sort(key=lambda x: [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', x)])
        return partition_names