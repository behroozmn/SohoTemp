from django.http import JsonResponse  # FA: برای ساخت پاسخ JSON
import psutil  # FA: psutil برای خواندن آمار سیستم
from typing import Dict, List, Any, Optional  # FA: تایپ‌هینت برای خوانایی بهتر
import subprocess  # FA: اجرای دستورات سیستمی در صورت نیاز


class Memory:  # FA: تعریف کلاس اصلی
    def __init__(self):
        """
        FA: توضیح تابع __init__ — ورودی‌ها: (self) — خروجی: بر اساس پیاده‌سازی فعلی بدون تغییر منطق.
        FA: این داکیومنت تنها برای توضیح است و هیچ تغییری در رفتار تابع ایجاد نمی‌کند.
        """
        try:
            self._mem = psutil.virtual_memory()  # FA: فراخوانی تابع از psutil
        except Exception as e:
            raise RuntimeError("ERROR in getting data from system") from e

    def get(self, *fields: str) -> Dict[str, Optional[Any]]:
        """فقط فیلدهای تعیین شده را برمی‌گرداند."""
        data = self._mem
        result = {}

        for field in fields:
            result[field] = data.get(field, None)

        return result

    def to_dict(self) -> Dict[str, Any]:
        """تمام فیلدها را به صورت dict برمی‌گرداند."""
        return self._mem._asdict()

    def total(self) -> int:
        return self._mem.total  # total physical psutil.virtual_memory()ory available.  # FA: فراخوانی تابع از psutil

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


import psutil  # FA: psutil برای خواندن آمار سیستم
import time
from typing import Dict, Any, Optional, List  # FA: تایپ‌هینت برای خوانایی بهتر
from django.http import JsonResponse  # FA: برای ساخت پاسخ JSON


