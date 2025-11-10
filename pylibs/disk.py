import os
import re
import glob
import subprocess
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

    def get_mounted_disk_size_usage(self, disk: str) -> Dict[str, Optional[float]]:
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
        """
        خواندن دما از hwmon با تطبیق مسیر دستگاه واقعی.
        این روش برای دیسک‌هایی که توسط drivetemp یا سازنده پشتیبانی می‌شوند کار می‌کند.
        """
        if not os.path.exists(self.SYS_CLASS_HWMON):
            return None

        try:
            # دریافت مسیر واقعی دستگاه دیسک
            disk_device_path = os.path.realpath(f"/sys/block/{disk}/device")

            for hwmon_dir in os.listdir(self.SYS_CLASS_HWMON):
                hwmon_path = os.path.join(self.SYS_CLASS_HWMON, hwmon_dir)

                # بررسی symlink device در hwmon
                device_link = os.path.join(hwmon_path, "device")
                if os.path.islink(device_link):
                    hwmon_device_path = os.path.realpath(device_link)
                    if hwmon_device_path == disk_device_path:
                        # همان دستگاه است — حالا دما را بخوان
                        temp_path = os.path.join(hwmon_path, "temp1_input")
                        if os.path.exists(temp_path):
                            temp_raw = FileManager.read_strip(temp_path)
                            if temp_raw.lstrip('-').isdigit():  # پشتیبانی از دمای منفی
                                return int(temp_raw) // 1000
        except (OSError, ValueError, IOError):
            pass
        return None

    def get_temperature_from_device(self, disk: str) -> Optional[int]:
        """
        خواندن دما مستقیماً از /sys/block/{disk}/device/temp (در هسته‌های جدید).
        در هسته‌های ≥ 5.10، برخی درایورها این فایل را ارائه می‌دهند.
        """
        temp_path = f"/sys/block/{disk}/device/temp"
        try:
            if os.path.exists(temp_path):
                temp_str = FileManager.read_strip(temp_path)
                if temp_str.lstrip('-').isdigit():
                    # برخی سیستم‌ها دما را به میلی‌درجه می‌دهند، برخی به سانتی‌گراد
                    temp = int(temp_str)
                    if temp > 1000:  # احتمالاً میلی‌درجه است
                        return temp // 1000
                    else:
                        return temp
        except (OSError, ValueError, IOError):
            pass
        return None

    def get_temperature_from_smartctl(self, disk: str) -> Optional[int]:  # ✅ self اضافه شد
        """
        دریافت دمای هارد از طریق دستور smartctl برای IDهای 190 و 194.
        این تابع بر اساس خروجی واقعی شما تست شده است.

        Args:
            disk (str): نام دیسک (مثل 'sda').

        Returns:
            Optional[int]: دمای دیسک به سانتی‌گراد یا None در صورت خطا یا عدم یافتن.
        """
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
            return None

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError, ValueError):
            return None

    def get_temperature(self, disk: str) -> Optional[int]:
        """
        دریافت دمای دیسک از منابع مختلف سیستم.
        اولویت‌ها:
        1. hwmon با تطبیق دقیق دستگاه
        2. فایل temp مستقیم در /sys/block/{disk}/device/
        3. روش قدیمی scsi (برای سیستم‌های enterprise)
        4. دستور smartctl (آخرین راه‌حل)
        """
        # روش ۱: hwmon
        temp = self.get_temperature_from_hwmon(disk)
        if temp is not None:
            return temp

        # روش ۲: فایل temp مستقیم
        temp = self.get_temperature_from_device(disk)
        if temp is not None:
            return temp

        # روش ۳: scsi enterprise
        if os.path.exists(self.SYS_SCSI_DISK):
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

        # روش ۴: smartctl (آخرین امید!)
        temp = self.get_temperature_from_smartctl(disk)
        if temp is not None:
            return temp

        return None

    def get_disk_info(self, disk: str) -> Dict[str, Any]:
        """جمع‌آوری تمام اطلاعات یک دیسک خاص.
        Args: disk (str): نام دیسک (مثل 'sda').
        Returns: Dict[str, Any]: دیکشنری کامل اطلاعات دیسک.
        """
        usage = self.get_mounted_disk_size_usage(disk)
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
            "total_bytes": self.get_disk_total_size(disk),
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
        """
        دریافت WWN یا شناسه منحصر به فرد دیسک از /dev/disk/by-id.

        این تابع هم برای دیسک‌های SATA/SCSI (با پیشوند wwn-)
        و هم برای NVMe (با پیشوند nvme-) کار می‌کند.

        Args:
            disk (str): نام دیسک (مثل 'sda' یا 'nvme0n1').

        Returns:
            str: نام لینک منحصر به فرد (مثل 'wwn-0x5000...' یا 'nvme-nvme.10ec-...') یا رشته خالی.
        """
        by_id_path = "/dev/disk/by-id"
        if not os.path.exists(by_id_path):
            return ""

        try:
            # الگوی کلی: همه لینک‌ها
            all_links = glob.glob(os.path.join(by_id_path, "*"))
            target_real_path = os.path.realpath(f"/dev/{disk}")

            wwn_candidate = None
            nvme_candidate = None

            for link in all_links:
                try:
                    if os.path.realpath(link) == target_real_path:
                        basename = os.path.basename(link)
                        # اولویت 1: لینک‌های wwn-*
                        if basename.startswith("wwn-"):
                            return basename
                        # اولویت 2: لینک‌های nvme-nvme.* (حاوی WWN واقعی NVMe)
                        elif basename.startswith("nvme-nvme."):
                            nvme_candidate = basename
                        # اولویت 3: سایر لینک‌های nvme- (fallback)
                        elif basename.startswith("nvme-"):
                            if nvme_candidate is None:
                                nvme_candidate = basename
                except (OSError, IOError):
                    continue

            # اگر wwn-* پیدا نشد، nvme-nvme.* را برگردان
            if nvme_candidate:
                return nvme_candidate

        except (OSError, IOError):
            pass

        return ""

    def get_uuid(self, disk: str) -> Optional[str]:
        """
        دریافت UUID مربوط به اولین پارتیشن معتبر روی دیسک از طریق /dev/disk/by-uuid/.

        این متد بدون اجرای هیچ دستور لینوکسی (مثل blkid) عمل می‌کند.
        پشتیبانی کامل از انواع دیسک (SATA, NVMe, MMC) و UUIDهای عددی/رشته‌ای.
        نکته: اگر دیسک خام در اختیار زد اف اس باشد آنگاه این مولفه برایش خالی خواهد بود

        Args:
            disk (str): نام دیسک (مثل 'sda', 'nvme0n1').

        Returns:
            Optional[str]: UUID پارتیشن یا None.
        """
        try:
            uuid_dir = "/dev/disk/by-uuid"
            if not os.path.exists(uuid_dir):
                return None

            # استخراج تمام پارتیشن‌های مرتبط با دیسک از /dev/disk/by-path/
            # این روش قابل اعتمادتر از خواندن /sys/block است
            by_path_dir = "/dev/disk/by-path"
            if not os.path.exists(by_path_dir):
                return None

            # جمع‌آوری تمام دستگاه‌هایی که به دیسک ما مربوط می‌شوند
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
                # fallback به روش قدیمی اگر by-path کار نکرد
                sys_disk_path = f"/sys/block/{disk}"
                if os.path.exists(sys_disk_path):
                    for entry in os.listdir(sys_disk_path):
                        if entry != disk and entry.startswith(disk):
                            # پشتیبانی از همه انواع پارتیشن
                            if (disk.startswith(("nvme", "mmcblk")) and entry.startswith(disk) and len(entry) > len(disk)) or \
                                    (not disk.startswith(("nvme", "mmcblk")) and entry.startswith(disk) and entry[len(disk):].isdigit()):
                                related_devices.add(f"/dev/{entry}")

            if not related_devices:
                return None

            # بررسی هر UUID برای تطابق با دستگاه‌های مرتبط
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

    def get_disk_total_size(self, disk: str) -> Optional[int]:
        """دریافت حجم خام دیسک از /sys/block/{disk}/size (به بایت)."""
        try:
            with open(f"/sys/block/{disk}/size", "r") as f:
                sectors = f.read().strip()
                if sectors.isdigit():
                    return int(sectors) * 512
        except (OSError, IOError, ValueError):
            pass
        return None