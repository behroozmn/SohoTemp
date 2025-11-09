import os
import re
from typing import Dict, Any, Optional, List
from pylibs.file import FileManager


class DiskManager:
    SYS_BLOCK = "/sys/block"
    PROC_MOUNTS = "/proc/mounts"
    PROC_DISKSTATS = "/proc/diskstats"

    def __init__(self):
        self.os_disk = self.get_os_disk()
        self.disks = self.get_disks_all()

    def get_disks_all(
            self,
            contain_os_disk: bool = True,
            exclude: tuple = ('loop', 'ram', 'sr', 'fd', 'md', 'dm-', 'zram')
    ) -> List[str]:
        if not os.path.exists(self.SYS_BLOCK):
            raise Exception("/sys/block not found – OS is not Linux?")

        found_disks = []
        for entry in os.listdir(self.SYS_BLOCK):
            # Skip excluded prefixes
            if any(entry.startswith(prefix) for prefix in exclude):
                continue

            if re.match(r'^(sd[a-z]+|nvme[0-9]+n[0-9]+|vd[a-z]+|hd[a-z]+)$', entry):
                if not contain_os_disk and entry == self.os_disk:
                    continue
                found_disks.append(entry)

        return sorted(found_disks)

    def get_os_disk(self) -> Optional[str]:
        """Find the disk that contains the root filesystem '/'"""
        try:
            with open(self.PROC_MOUNTS, 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 3 and parts[1] == '/' and parts[0].startswith('/dev/'):
                        dev_name = os.path.basename(parts[0])  # e.g., 'sda2'
                        # Match with base disk (e.g., 'sda2' → 'sda')
                        for disk in os.listdir(self.SYS_BLOCK):
                            if dev_name.startswith(disk):
                                return disk
        except Exception:
            pass
        return None

    def get_model(self, disk: str) -> str:
        try:
            return FileManager.read_strip(f"/sys/block/{disk}/device/model")
        except (OSError, IOError):
            return ""

    def get_vendor(self, disk: str) -> str:
        try:
            return FileManager.read_strip(f"/sys/block/{disk}/device/vendor")
        except (OSError, IOError):
            return ""

    def get_stat(self, disk: str) -> str:
        try:
            return FileManager.read_strip(f"/sys/block/{disk}/device/state")
        except (OSError, IOError):
            return ""

    def get_physical_block_size(self, disk: str) -> str:
        try:
            return FileManager.read_strip(f"/sys/block/{disk}/queue/physical_block_size")
        except (OSError, IOError):
            return ""

    def get_logical_block_size(self, disk: str) -> str:
        try:
            return FileManager.read_strip(f"/sys/block/{disk}/queue/logical_block_size")
        except (OSError, IOError):
            return ""

    def get_scheduler(self, disk: str) -> str:
        try:
            return FileManager.read_strip(f"/sys/block/{disk}/queue/scheduler")
        except (OSError, IOError):
            return ""

    def get_wwid(self, disk: str) -> str:
        try:
            return FileManager.read_strip(f"/sys/block/{disk}/device/wwid")
        except (OSError, IOError):
            return ""

    def get_path(self, disk: str) -> str:
        try:
            return os.path.realpath(f"/sys/block/{disk}")
        except (OSError, IOError):
            return ""

    def get_disk_info(self, disk: str) -> Dict[str, Any]:
        return {
            "disk": disk,
            "model": self.get_model(disk),
            "vendor": self.get_vendor(disk),
            "state": self.get_stat(disk),
            "device_path": self.get_path(disk),
            "physical_block_size": self.get_physical_block_size(disk),
            "logical_block_size": self.get_logical_block_size(disk),
            "scheduler": self.get_scheduler(disk),
            "wwn": self.get_wwid(disk),
        }
