#!/usr/bin/env python3  # شِبانگ (shebang) به سیستم‌عامل می‌گوید این فایل با مفسر python3 اجرا شود؛ در اسکریپت‌ها کاربرد دارد.
# -*- coding: utf-8 -*-  # تعیین کُدگذاری فایل روی UTF-8 تا کاراکترهای فارسی در کامنت‌ها و داک‌استرینگ‌ها درست تفسیر شوند.

"""
FA (توضیح ماژول):
این ماژول یک کلاس سطح‌بالا به نام ZFSManager فراهم می‌کند که با استفاده از کتابخانهٔ رسمی libzfs
و در جاهایی که API کامل در دسترس نیست با fallback ایمن به CLIهای رسمی (zfs/zpool) عملیات روی ZFS را انجام می‌دهد.
طراحی کلاس به‌صورت JSON-Ready است تا در فریم‌ورک Django REST Framework (DRF) به‌سادگی به عنوان خروجی View/APIView برگردانده شود.
تمام متدهای عمومی، دیکشنری‌هایی برمی‌گردانند که دارای کلیدهای ok/error/data/meta هستند و مستقیماً قابل استفاده در Response() می‌باشند.

- رویکرد: ابتدا سعی در استفاده از libzfs برای کارهای introspection و set/get property، و هرجا لازم باشد
  اجرای امن CLI بدون shell=True برای جلوگیری از تزریق فرمان.
- مخاطب: توسعه‌دهندگان مبتدی تا پیشرفته؛ برای مبتدی‌ها داک‌استرینگ‌ها و کامنت‌های فارسی مفصل ارائه شده است.
- ملاحظات امنیتی: عمیات مخرب مانند destroy و rollback خطرناک‌اند؛ در محیط تولید باید احراز هویت/مجوزدهی مناسب در DRF اعمال شود.
- سازگاری: بسته به پلتفرم (FreeBSD/OpenZFS on Linux) ممکن است برخی پراپرتی‌ها متفاوت باشند؛ کد با مدیریت خطا و fallback سعی در سازگاری دارد.

EN (module quick note):
High-level ZFS manager for use with Django REST Framework. Methods return JSON-serializable dicts.
Uses libzfs primarily and falls back to zfs/zpool CLI where necessary.
"""

import libzfs  # ایمپورت binding رسمی libzfs برای دسترسی مستقیم به ساختارها و پراپرتی‌های ZFS.
import subprocess  # اجرای امن فرمان‌های سیستمی (zfs/zpool) وقتی API کامل نیست یا برای گزارش خام.
import shlex  # کوئوت و توکِنایز ایمن آرگومان‌ها برای جلوگیری از تزریق فرمان.
from typing import Dict, List, Optional, Iterable, Tuple, Any  # تایپ‌هینت‌ها برای خوانایی و ابزارهای استاتیک‌آنالایزر.


# --------------------------- JSON envelopes ---------------------------  # الگوی یکسان پاسخ برای DRF (موفق/ناموفق).

def ok(data: Any, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:  # تابع کمکی برای ساخت پاسخ موفق استاندارد.
    """
    FA:
    توضیح: این تابع یک پوشش (envelope) استاندارد برای پاسخ موفق تولید می‌کند تا به‌صورت مستقیم در DRF استفاده شود.
    ورودی‌ها:
      - data (Any): هر دادهٔ قابل‌سریالایز به JSON که می‌خواهید به کلاینت برگردانید؛ می‌تواند عدد/رشته/دیکشنری/لیست و ...
      - meta (dict|None): اطلاعات جانبی (metadata) اختیاری مثل منبع داده، نسخه، زمان‌بندی کش و ...
    خروجی:
      - dict: دیکشنری با ساختار {"ok": True, "error": None, "data": data, "meta": meta or {}}
    خطاها:
      - ندارد؛ این تابع فقط ساختار خروجی را می‌چیند.
    نکته:
      - این الگو با Response() در DRF سازگار است و سریالایز می‌شود.

    EN (summary): Build a success envelope for DRF-friendly responses.
    """
    return {"ok": True, "error": None, "data": data, "meta": meta or {}}  # برگرداندن ساختار استاندارد پاسخ موفق.


def fail(message: str, code: str = "zfs_error", extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:  # تابع کمکی برای ساخت پاسخ خطا.
    """
    FA:
    توضیح: این تابع ساختار یک پاسخ خطا را ایجاد می‌کند تا خطاها به‌صورت یکنواخت به کلاینت بازگردند.
    ورودی‌ها:
      - message (str): پیام خطای قابل‌خواندن برای انسان که توضیح دهد چه رخ داده است.
      - code (str): کُد منطقی/ماشینی خطا (برای تشخیص برنامه‌نویسان؛ مثل "invalid_request", "not_found", "zfs_error").
      - extra (dict|None): اطلاعات تکمیلی خطا (trace، فرمان اجراشده، stdout/stderr) در صورت لزوم.
    خروجی:
      - dict: دیکشنری با ساختار {"ok": False, "error": {"code": code, "message": message, "extra": extra or {}}, "data": None, "meta": {}}
    خطاها:
      - ندارد؛ فقط یک ساختار ثابت تولید می‌شود.

    EN (summary): Build an error envelope for DRF-friendly responses.
    """
    return {"ok": False, "error": {"code": code, "message": message, "extra": extra or {}}, "data": None, "meta": {}}  # برگرداندن ساختار استاندارد پاسخ خطا.


class ZFSError(Exception):  # استثنای اختصاصی دامنهٔ ZFS برای تمایز خطاها در لاجیک برنامه.
    """
    FA:
    توضیح: استثنای دامنه‌ای برای مدیریت یک‌دست خطاهای مرتبط با عملیات ZFS.
    چرا؟ برای اینکه بتوانیم خطاهای مربوط به ZFS را از سایر خطاها جدا کنیم و در handlerهای DRF واکنش مناسب نشان دهیم.
    ورودی‌ها/خروجی:
      - مانند Exception استاندارد پایتون؛ می‌توانید پیام (str) یا استثنای اصلی را پاس بدهید.
    خطاها:
      - ندارد؛ صرفاً برای تمایز نوع استثناء استفاده می‌شود.

    EN (summary): Domain-specific exception to distinguish ZFS-related errors.
    """
    pass  # بدنه‌ای لازم نیست؛ فقط تایپ سفارشی است.


class ZFSManager:  # کلاس مدیریت سطح‌بالای ZFS با خروجی JSON-Ready و fallback به CLI.
    """
    FA:
    هدف: ارائهٔ API سطح‌بالا برای مدیریت ZFS که:
      1) تا جای ممکن از libzfs برای کارهای داخل حافظه (introspection و set/get properties) استفاده کند.
      2) در جاهایی که API پوشش ندارد (مثل send/receive یا create pool)، با اجرای امن CLI (zfs/zpool) کار را انجام دهد.
      3) تمام خروجی‌ها را به‌صورت JSON-Ready برگرداند تا با DRF به‌راحتی قابل مصرف باشد.
    مخاطب: توسعه‌دهندگان مبتدی تا پیشرفته. توضیحات فارسی و انگلیسی ساده در Docstring و کامنت‌ها فراهم شده است.
    نکات مهم:
      - پارامتر dry_run: اگر True باشد، فرمان‌های تغییر دهندهٔ وضعیت اجرا نمی‌شوند و فقط رشتهٔ فرمان باز می‌گردد (برای تست امن).
      - پارامتر run_timeout: محدودیت زمانی اجرای فرمان‌های CLI (ثانیه).
      - برای عملیات خطرناک (destroy, rollback) حتماً احراز هویت و مجوزدهی سمت API را جدی بگیرید.
    خروجی متدها:
      - همگی ساختاری دارای کلیدهای ok/error/data/meta برمی‌گردانند که مستقیماً در DRF Response() قابل استفاده است.

    EN (summary):
      High-level manager for ZFS with libzfs + safe CLI fallback. All public methods return JSON-serializable envelopes.
    """

    def __init__(self, dry_run: bool = False, run_timeout: int = 180) -> None:  # سازندهٔ کلاس با تنظیمات اجرایی.
        """
        توضیح: سازندهٔ کلاس که اتصال به libzfs را برقرار می‌کند و تنظیمات پایه را می‌گیرد.
        ورودی‌ها:
          - dry_run (bool): اگر True باشد، عملیات تغییر حالت سیستم (مثل create/destroy) اجرا نمی‌شود و فقط لاگ/خروجی ساختگی تولید می‌شود.
          - run_timeout (int): محدودیت زمانی (ثانیه) برای اجرای فرمان‌های CLI؛ از hang شدن فرآیند جلوگیری می‌کند.
        خروجی:
          - None: فقط نمونه را مقداردهی می‌کند.
        خطاها:
          - در صورت مشکل در ایجاد نمونه libzfs.ZFS ممکن است استثناء از libzfs رخ دهد.

        EN: Initialize manager: create libzfs.ZFS(), set dry_run and timeout.
        """
        self.zfs = libzfs.ZFS()  # ایجاد نمونهٔ اصلی libzfs برای دسترسی به poolها و datasetها.
        self.dry_run = dry_run  # ذخیرهٔ وضعیت dry-run برای استفاده در متدهای تغییر حالت.
        self.run_timeout = run_timeout  # ذخیرهٔ محدودیت زمانی اجرای CLI برای همهٔ فراخوانی‌های _run.

    # --------------------------- internal helpers ---------------------------  # توابع کمکی داخلی؛ خارج از API عمومی.

    def _run(self, args: List[str], stdin: Optional[bytes] = None) -> Tuple[str, str]:  # اجرای امن فرمان CLI با آرگومان‌های لیستی.
        """
        توضیح: این متد داخلی فرمان‌های CLI مثل zfs/zpool را به‌صورت ایمن اجرا می‌کند.
        چرا ایمن؟ چون از لیست آرگومان (بدون shell=True) استفاده می‌کند تا از تزریق فرمان جلوگیری شود.
        ورودی‌ها:
          - args (List[str]): لیست آرگومان‌ها، مثلاً ["zfs", "list", "-H"].
          - stdin (bytes|None): در صورت نیاز، دادهٔ ورودی باینری برای فرمان‌هایی مثل `zfs receive`.
        خروجی:
          - (stdout:str, stderr:str): خروجی و خطای استاندارد به‌صورت رشته (UTF-8 decoded).
        خطاها:
          - ZFSError: اگر اجرای فرمان با non-zero exit code تمام شود یا Timeout/OSError رخ دهد.
        نکات:
          - اگر dry_run=True باشد، فرمان اجرا نمی‌شود و به‌جای آن یک خروجی ساختگی با برچسب [DRY-RUN] برگردانده می‌شود.
          - timeout از hang شدن جلوگیری می‌کند.

        EN: Safe subprocess.run wrapper. Returns decoded stdout/stderr or raises ZFSError.
        """
        cmd_str = " ".join(shlex.quote(a) for a in args)  # ساخت نسخهٔ رشته‌ای امن برای لاگ/اشکال‌زدایی.
        if self.dry_run:  # اگر در حالت dry-run هستیم، اجرا نکن و خروجی ساختگی بده.
            return f"[DRY-RUN] {cmd_str}", ""  # برگرداندن stdout ساختگی و stderr خالی.
        try:
            proc = subprocess.run(  # اجرای فرمان به‌صورت امن بدون shell؛ کنترل timeout و capture خروجی‌ها.
                args, input=stdin, capture_output=True, timeout=self.run_timeout, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as exc:  # مدیریت خطاهای سیستم‌عامل و تایم‌اوت.
            raise ZFSError(f"Command failed: {cmd_str} ({exc})") from exc  # تبدیل خطا به ZFSError برای لایهٔ بالاتر.
        if proc.returncode != 0:  # اگر کد خروج غیر صفر بود یعنی خطا رخ داده است.
            raise ZFSError(  # پرتاب استثناء با جزئیات stdout/stderr برای تشخیص بهتر.
                f"Command failed: {cmd_str}\nstdout: {proc.stdout.decode(errors='ignore')}\nstderr: {proc.stderr.decode(errors='ignore')}"
            )
        return proc.stdout.decode(errors="ignore"), proc.stderr.decode(errors="ignore")  # برگرداندن خروجی‌های متنی.

    def _get_dataset(self, name: str) -> libzfs.ZFSDataset:  # دریافت شیء دیتاست از libzfs.
        """
        توضیح: تلاش برای دریافت یک دیتاست با نام مشخص از libzfs.
        ورودی:
          - name (str): نام کامل dataset (مثل "tank/data" یا "tank/vol1").
        خروجی:
          - libzfs.ZFSDataset: شیء دیتاست در صورت موفقیت.
        خطاها:
          - ZFSError: اگر دیتاست پیدا نشود یا libzfs خطا دهد.

        EN: Get dataset object by name or raise ZFSError.
        """
        try:
            return self.zfs.get_dataset(name)  # فراخوانی مستقیم API libzfs برای دریافت دیتاست.
        except libzfs.ZFSException as exc:  # تبدیل خطای libzfs به ZFSError با پیام واضح.
            raise ZFSError(f"Dataset not found: {name}") from exc

    def _get_pool(self, name: str) -> libzfs.ZFSPool:  # دریافت شیء zpool بر اساس نام.
        """
        توضیح: در بین zpoolها پیمایش می‌کند و pool با نام داده‌شده را برمی‌گرداند.
        ورودی:
          - name (str): نام zpool (مثل "tank").
        خروجی:
          - libzfs.ZFSPool: شیء pool اگر یافت شود.
        خطاها:
          - ZFSError: اگر pool با نام مشخص وجود نداشته باشد.

        EN: Iterate pools and return matching ZFSPool or raise ZFSError.
        """
        for pool in self.zfs.pools:  # پیمایش لیست poolها از libzfs.
            if pool.name == name:  # بررسی تطابق نام.
                return pool  # بازگرداندن pool مورد نظر.
        raise ZFSError(f"Pool not found: {name}")  # اگر چیزی پیدا نشد، خطا.

    def _safe_prop_value(self, v: Any) -> Any:  # نرمال‌سازی مقدار پراپرتی libzfs به مقدار ساده.
        """
        توضیح: برخی bindingها به‌جای مقدار خام، یک شیء Property برمی‌گردانند؛ این تابع در صورت وجود صفت value آن را استخراج می‌کند.
        ورودی:
          - v (Any): مقدار/شیء پراپرتی.
        خروجی:
          - Any: مقدار سادهٔ قابل سریالایز (در صورت وجود v.value همان را برمی‌گرداند وگرنه v را).
        خطاها:
          - ندارد.

        EN: Return v.value when available; otherwise return v.
        """
        return getattr(v, "value", v)  # اگر v.value موجود بود، همان را؛ وگرنه خود v.

    # --------------------------- discovery & listing ---------------------------  # متدهای لیست و وضعیت.

    def list_pools(self) -> Dict[str, Any]:  # لیست نام تمام zpoolها.
        """
        توضیح: نام تمام zpoolهای موجود در سیستم را از libzfs می‌خواند.
        ورودی:
          - ندارد.
        خروجی:
          - dict(JSON-Ready): {"ok": True, "data": ["tank", "backup", ...], ...}
        خطاها:
          - در صورت مشکل در libzfs، خروجی fail(...) با پیام خطا برمی‌گردد.

        EN: List zpool names using libzfs.
        """
        try:
            return ok([p.name for p in self.zfs.pools])  # استخراج نام‌ها و برگرداندن در قالب JSON.
        except Exception as exc:
            return fail(str(exc))  # بسته‌بندی خطا در قالب یکنواخت JSON.

    def pool_status(self, pool: str) -> Dict[str, Any]:  # وضعیت سادهٔ یک zpool.
        """
        توضیح: وضعیت پایهٔ یک zpool شامل نام، state، health، guid و تعدادی پراپرتی رایج را برمی‌گرداند.
        ورودی:
          - pool (str): نام zpool (مثلاً "tank").
        خروجی:
          - dict(JSON-Ready): شامل فیلدهای کلیدی و dict پراپرتی‌ها.
        خطاها:
          - ZFSError: اگر pool پیدا نشود؛ در خروجی fail(...) بازتاب می‌یابد.

        EN: Basic zpool status and a few properties.
        """
        try:
            p = self._get_pool(pool)  # بازیابی شیء pool.
            extras = {}  # دیکشنری برای پراپرتی‌های اضافه.
            for prop in ("ashift", "autoexpand", "autoreplace", "autotrim", "listsnapshots"):  # پراپرتی‌های متداول.
                try:
                    if hasattr(p, "get_prop"):  # اگر API گرفتن پراپرتی وجود دارد.
                        extras[prop] = str(self._safe_prop_value(p.get_prop(prop)))  # مقداردهی با نرمال‌سازی.
                except Exception:
                    pass  # اگر خطایی شد، صرف‌نظر؛ گزارش پایه همچنان مفید است.
            return ok({
                "name": p.name,
                "state": str(getattr(p, "state", "")),
                "health": str(getattr(p, "health", "")),
                "guid": str(getattr(p, "guid", "")),
                "props": extras
            })
        except Exception as exc:
            return fail(str(exc))

    def pool_status_verbose(self, pool: str) -> Dict[str, Any]:  # FA: خروجی خام zpool status -v برای عیب‌یابی.
        """
        توضیح: خروجی کامل و خام `zpool status -v` را بازمی‌گرداند که برای عیب‌یابی دقیق (device errors, checksum, ...) کاربرد دارد.
        ورودی:
          - pool (str): نام zpool.
        خروجی:
          - dict(JSON-Ready): {"ok": True, "data": {"raw": "<full text>"}}
        خطاها:
          - ZFSError: در صورت خطا در اجرای CLI.

        EN: Return raw `zpool status -v` for troubleshooting.
        """
        try:
            out, _ = self._run(["zpool", "status", "-v", pool])  # FA: اجرای امن فرمان status -v.
            return ok({"raw": out})  # FA: بازگرداندن متن خام برای پارس بعدی در کلاینت/سرویس.
        except Exception as exc:
            return fail(str(exc))

    def pool_iostat(self, pool: Optional[str] = None, samples: int = 1, interval: int = 1) -> Dict[str, Any]:  # FA: نمونهٔ I/O stats.
        """
        توضیح: یک عکس لحظه‌ای از آمار I/O با `zpool iostat -v` می‌گیرد. برای پایش سریع کاراست.
        ورودی‌ها:
          - pool (str|None): اگر None باشد همهٔ poolها؛ در غیراینصورت فقط همان pool.
          - samples (int): تعداد نمونه‌گیری‌ها (عدد 1 یعنی یکبار).
          - interval (int): فاصلهٔ نمونه‌گیری برحسب ثانیه.
        خروجی:
          - dict(JSON-Ready): {"ok": True, "data": {"raw": "<iostat text>"}}
        خطاها:
          - ZFSError: در صورت خطا در اجرای CLI.

        EN: Return raw `zpool iostat -v` output.
        """
        try:
            args = ["zpool", "iostat", "-v"]  # FA: ساخت آرگومان پایه برای iostat مفصل.
            if pool:  # FA: اگر نام pool داده شده باشد، اضافه کن.
                args.append(pool)
            args += [str(samples), str(interval)]  # FA: افزودن پارامترهای نمونه و بازه.
            out, _ = self._run(args)  # FA: اجرای امن CLI.
            return ok({"raw": out})
        except Exception as exc:
            return fail(str(exc))

    def list_datasets(self, pool: Optional[str] = None,
                      types: Iterable[str] = ("filesystem", "volume", "snapshot")) -> Dict[str, Any]:  # FA: لیست دیتاست‌ها با نوع.
        """
        توضیح: فهرست دیتاست‌ها (filesystem, volume(zvol), snapshot) را به همراه نوعشان بازمی‌گرداند.
        ورودی‌ها:
          - pool (str|None): اگر مشخص شود، فقط دیتاست‌های زیر آن pool لیست می‌شوند.
          - types (Iterable[str]): مجموعهٔ نوع‌ها برای فیلتر (پیش‌فرض: همهٔ سه نوع رایج).
        خروجی:
          - dict(JSON-Ready): لیستی از {"name": "...", "type": "filesystem|volume|snapshot"}.
        خطاها:
          - ZFSError: در صورت خطا در اجرای CLI یا پارس خروجی.

        EN: List datasets with their type, optionally filtered by pool and types.
        """
        try:
            args = ["zfs", "list", "-H", "-o", "name,type", "-t", ",".join(types), "-r"]  # FA: لیست با خروجی tab-separated.
            if pool:
                args.append(pool)  # FA: محدودکردن به یک pool خاص.
            out, _ = self._run(args)  # FA: اجرای فرمان.
            items: List[Dict[str, str]] = []  # FA: آماده‌سازی لیست نتیجه.
            for line in out.splitlines():  # FA: پیمایش هر خط از خروجی.
                if not line.strip():
                    continue  # FA: خط خالی را رد کن.
                name_i, type_i = line.split("\t")  # FA: جدا کردن نام و نوع بر اساس tab.
                if pool is None or name_i.split("/")[0] == pool:  # FA: در صورت نبود فیلتر pool، همه را می‌پذیریم.
                    items.append({"name": name_i, "type": type_i})  # FA: افزودن به نتیجه.
            return ok(items)
        except Exception as exc:
            return fail(str(exc))

    def get_props(self, target: str) -> Dict[str, Any]:  # FA: گرفتن همهٔ پراپرتی‌ها برای یک دیتاست.
        """
        توضیح: تمام پراپرتی‌های قابل مشاهدهٔ یک دیتاست را (ترجیحاً با libzfs و در غیر اینصورت با CLI) بازمی‌گرداند.
        ورودی:
          - target (str): نام دیتاست (مانند "tank/data" یا "tank/vol").
        خروجی:
          - dict(JSON-Ready): map پراپرتی به مقدار آن (همه رشته).
        خطاها:
          - ZFSError: در صورت خطا در libzfs یا اجرای CLI.

        EN: Get all visible properties for a dataset (libzfs first, fallback CLI).
        """
        try:
            try:
                ds = self._get_dataset(target)  # FA: تلاش از libzfs.
                result: Dict[str, Any] = {}  # FA: نتیجهٔ پراپرتی‌ها.
                if hasattr(ds, "properties"):  # FA: در برخی bindingها dict-مانند است.
                    for k, v in ds.properties.items():  # FA: پیمایش کلید/مقدار.
                        result[k] = str(self._safe_prop_value(v))  # FA: نرمال‌سازی مقدار.
                    return ok(result)
            except ZFSError:
                pass  # FA: اگر libzfs شکست خورد، به CLI می‌رویم.
            out, _ = self._run(["zfs", "get", "-H", "-o", "property,value", "all", target])  # FA: خواندن همهٔ پراپرتی‌ها با CLI.
            props: Dict[str, Any] = {}
            for line in out.splitlines():
                if not line.strip():
                    continue
                k, v = line.split("\t")
                props[k] = v
            return ok(props)
        except Exception as exc:
            return fail(str(exc))

    # --------------------------- pool operations ---------------------------  # FA: متدهای ساخت/حذف/وضعیت pool.

    def create_pool(self, name: str, vdevs: List[List[str]],
                    properties: Optional[Dict[str, str]] = None,
                    force: bool = False, altroot: Optional[str] = None,
                    ashift: Optional[int] = None) -> Dict[str, Any]:  # FA: ساخت zpool جدید با CLI.
        """
        توضیح: یک zpool جدید می‌سازد. برای vdevها باید آرایه‌ای از گروه‌ها بدهید (مثلاً [["mirror","/dev/sdb","/dev/sdc"], ["raidz1",...]]).
        ورودی‌ها:
          - name (str): نام zpool (مثلاً "tank").
          - vdevs (List[List[str]]): گروه‌های vdev به همان ترتیبی که در CLI می‌دهید (مانند mirror/raidz/diskها).
          - properties (dict|None): پراپرتی‌های سطح pool (مثل {"autoexpand": "on"}).
          - force (bool): افزودن فلگ -f برای ایجاد اجباری.
          - altroot (str|None): استفاده از -R <path> برای روت جایگزین.
          - ashift (int|None): ست کردن ashift با -o ashift=N (برای سایز بلاک فیزیکی دیسک).
        خروجی:
          - dict(JSON-Ready): شامل وضعیت ساخت و متن stdout.
        خطاها:
          - ZFSError: اگر اجرای CLI شکست بخورد (مثلاً دیسک‌ها در استفاده باشند).

        EN: Create a zpool using CLI. Provide vdev groups just like zpool create syntax.
        """
        try:
            args = ["zpool", "create"]  # FA: آغاز آرگومان‌های ساخت pool.
            if force:
                args.append("-f")  # FA: فلگ اجباری.
            if altroot:
                args += ["-R", altroot]  # FA: تنظیم روت جایگزین.
            if ashift is not None:
                args += ["-o", f"ashift={ashift}"]  # FA: پراپرتی ashift.
            if properties:
                for k, v in properties.items():
                    args += ["-o", f"{k}={v}"]  # افزودن سایر پراپرتی‌ها.
            args.append(name)  # FA: نام pool.
            for grp in vdevs:
                args += grp  # FA: افزودن گروه vdevها دقیقا به ترتیب.
            out, _ = self._run(args)  # FA: اجرای ساخت.
            return ok({"created": True, "pool": name, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def destroy_pool(self, name: str, force: bool = False) -> Dict[str, Any]:  # FA: حذف zpool (خطرناک).
        """
        توضیح: یک zpool را به‌طور کامل حذف می‌کند. بسیار خطرناک است و همهٔ داده‌ها از دست می‌رود.
        ورودی‌ها:
          - name (str): نام pool که باید حذف شود.
          - force (bool): استفاده از -f برای اجبار.
        خروجی:
          - dict(JSON-Ready): نتیجهٔ عملیات با stdout.
        خطاها:
          - ZFSError: خطا در اجرای CLI.

        EN: Destroy a zpool (dangerous!).
        """
        try:
            args = ["zpool", "destroy"]
            if force:
                args.append("-f")
            args.append(name)
            out, _ = self._run(args)
            return ok({"destroyed": True, "pool": name, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def import_pool(self, name: Optional[str] = None,
                    dir_hint: Optional[str] = None, readonly: bool = False) -> Dict[str, Any]:  # FA: ایمپورت pool.
        """
        توضیح: ایمپورت یک zpool از دیسک‌ها. می‌توانید مسیر جستجو بدهید یا حالت فقط‌خواندنی تنظیم کنید.
        ورودی‌ها:
          - name (str|None): نام pool برای ایمپورت؛ اگر None باشد لیست ایمپورت‌ها را نشان می‌دهد/همه را ایمپورت می‌کند.
          - dir_hint (str|None): استفاده از -d <dir> برای مشخص کردن مسیر جستجو.
          - readonly (bool): اگر True باشد -o readonly=on اعمال می‌شود.
        خروجی:
          - dict(JSON-Ready): نتیجهٔ عملیات با stdout.
        خطاها:
          - ZFSError: خطا در اجرای CLI.

        EN: Import a zpool (optionally readonly and with -d search dir).
        """
        try:
            args = ["zpool", "import"]
            if dir_hint:
                args += ["-d", dir_hint]
            if readonly:
                args += ["-o", "readonly=on"]
            if name:
                args.append(name)
            out, _ = self._run(args)
            return ok({"imported": True, "pool": name, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def export_pool(self, name: str, force: bool = False) -> Dict[str, Any]:  # FA: اکسپورت pool.
        """
        توضیح: zpool را از سیستم جاری خارج (export) می‌کند تا در سیستم دیگری import شود.
        ورودی‌ها:
          - name (str): نام pool.
          - force (bool): استفاده از -f برای اجبار در خروج.
        خروجی:
          - dict(JSON-Ready): وضعیت عملیات با stdout.
        خطاها:
          - ZFSError: خطا در اجرای CLI.

        EN: Export a zpool (prepare to move/attach on another host).
        """
        try:
            args = ["zpool", "export"]
            if force:
                args.append("-f")
            args.append(name)
            out, _ = self._run(args)
            return ok({"exported": True, "pool": name, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def scrub_pool(self, name: str, stop: bool = False) -> Dict[str, Any]:  # FA: شروع/توقف scrub.
        """
        توضیح: اسکراب را برای بررسی و اصلاح silent errorها در pool آغاز یا متوقف می‌کند.
        ورودی‌ها:
          - name (str): نام pool.
          - stop (bool): اگر True باشد scrub متوقف می‌شود وگرنه شروع می‌گردد.
        خروجی:
          - dict(JSON-Ready): شامل وضعیت "started"/"stopped".
        خطاها:
          - ZFSError: خطا در اجرای CLI.

        EN: Start or stop zpool scrub.
        """
        try:
            args = ["zpool", "scrub"]
            if stop:
                args.append("-s")
            args.append(name)
            out, _ = self._run(args)
            return ok({"scrub": "stopped" if stop else "started", "pool": name, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def clear_pool(self, name: str, device: Optional[str] = None) -> Dict[str, Any]:  # FA: پاک‌سازی شمارنده‌های خطا.
        """
        توضیح: شمارنده‌های خطا را در سطح pool یا یک وسیلهٔ خاص پاک می‌کند (zpool clear).
        ورودی‌ها:
          - name (str): نام pool.
          - device (str|None): نام وسیلهٔ مشخص برای پاک‌سازی هدفمند (اختیاری).
        خروجی:
          - dict(JSON-Ready): نتیجهٔ عملیات با stdout.
        خطاها:
          - ZFSError: خطا در اجرای CLI.

        EN: Clear error counters on pool/device.
        """
        try:
            args = ["zpool", "clear", name]
            if device:
                args.append(device)
            out, _ = self._run(args)
            return ok({"cleared": True, "pool": name, "device": device, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def features(self, pool: str) -> Dict[str, Any]:  # FA: لیست feature@* ها.
        """
        توضیح: با استفاده از `zpool get all` فهرست feature@* و وضعیتشان را استخراج می‌کند.
        ورودی:
          - pool (str): نام pool.
        خروجی:
          - dict(JSON-Ready): لیستی از {"property": "feature@xyz", "value": "enabled/active/...","source":"..."}.
        خطاها:
          - ZFSError: خطا در اجرای CLI.

        EN: List ZFS feature flags for the given pool.
        """
        try:
            out, _ = self._run(["zpool", "get", "-H", "-o", "name,property,value,source", "all", pool])
            rows: List[Dict[str, str]] = []
            for ln in out.splitlines():
                if not ln.strip():
                    continue
                name, prop, value, source = ln.split("\t")
                if prop.startswith("feature@"):
                    rows.append({"property": prop, "value": value, "source": source})
            return ok(rows)
        except Exception as exc:
            return fail(str(exc))

    # --------------------------- dataset operations ---------------------------  # FA: متدهای مدیریت دیتاست/زول.

    def create_dataset(self, name: str, properties: Optional[Dict[str, str]] = None,
                       dataset_type: str = "filesystem") -> Dict[str, Any]:  # FA: ایجاد filesystem یا zvol.
        """
        توضیح: یک دیتاست جدید می‌سازد؛ اگر نوع "volume" انتخاب شود، باید حتماً پراپرتی "volsize" تعیین شود.
        ورودی‌ها:
          - name (str): نام کامل دیتاست (مانند "tank/data" یا "tank/vms/vol01").
          - properties (dict|None): پراپرتی‌های اولیه (مثلاً compression, mountpoint, volsize, volblocksize).
          - dataset_type (str): "filesystem" یا "volume". پیش‌فرض "filesystem".
        خروجی:
          - dict(JSON-Ready): نتیجهٔ ساخت با stdout.
        خطاها:
          - ZFSError: خطا در اجرای CLI (مانند نبودن volsize برای volume).

        EN: Create a filesystem or zvol. For zvol, 'volsize' is required.
        """
        try:
            args = ["zfs", "create", "-p"]
            if dataset_type == "volume":
                if not properties or "volsize" not in properties:
                    return fail("Creating a volume requires 'volsize' property.", code="invalid_request")
            if properties:
                for k, v in properties.items():
                    args += ["-o", f"{k}={v}"]
            args.append(name)
            out, _ = self._run(args)
            return ok({"created": True, "dataset": name, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def destroy_dataset(self, name: str, recursive: bool = False, force: bool = False) -> Dict[str, Any]:  # FA: حذف دیتاست.
        """
        توضیح: دیتاست را حذف می‌کند؛ با گزینهٔ recursive می‌توانید فرزندان/اسنپ‌شات‌ها را هم حذف کنید.
        ورودی‌ها:
          - name (str): نام دیتاست.
          - recursive (bool): افزودن -r برای حذف بازگشتی.
          - force (bool): افزودن -f برای اجبار.
        خروجی:
          - dict(JSON-Ready): نتیجهٔ عملیات با stdout.
        خطاها:
          - ZFSError: در صورت خطا در اجرای CLI.

        EN: Destroy dataset; optionally recursive/force.
        """
        try:
            args = ["zfs", "destroy"]
            if recursive:
                args.append("-r")
            if force:
                args.append("-f")
            args.append(name)
            out, _ = self._run(args)
            return ok({"destroyed": True, "dataset": name, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def set_props(self, target: str, properties: Dict[str, str]) -> Dict[str, Any]:  # FA: ست‌کردن پراپرتی‌ها.
        """
        توضیح: پراپرتی‌های یک دیتاست را تنظیم می‌کند؛ ابتدا سعی با libzfs و در صورت نیاز با CLI.
        ورودی‌ها:
          - target (str): نام دیتاست هدف.
          - properties (dict): نگاشت کلید-مقدار پراپرتی‌ها (مثل {"compression":"zstd","atime":"off"}).
        خروجی:
          - dict(JSON-Ready): پراپرتی‌هایی که تغییر کرده‌اند.
        خطاها:
          - ZFSError: اگر تنظیم با خطا مواجه شود (مثلاً مقدار نامعتبر).

        EN: Set dataset properties (libzfs first, fallback to CLI).
        """
        try:
            ds = self._get_dataset(target)
            changed: Dict[str, str] = {}
            for k, v in properties.items():
                try:
                    if hasattr(ds, "set_property"):
                        ds.set_property(k, v)
                        changed[k] = str(v)
                    else:
                        out, _ = self._run(["zfs", "set", f"{k}={v}", target])
                        changed[k] = str(v)
                except Exception as inner:
                    return fail(f"Failed to set {k}: {inner}")
            return ok({"target": target, "changed": changed})
        except Exception:
            try:
                changed: Dict[str, str] = {}
                for k, v in properties.items():
                    out, _ = self._run(["zfs", "set", f"{k}={v}", target])
                    changed[k] = str(v)
                return ok({"target": target, "changed": changed, "method": "cli_fallback"})
            except Exception as exc2:
                return fail(str(exc2))

    def snapshot(self, name: str, recursive: bool = False, props: Optional[Dict[str, str]] = None) -> Dict[str, Any]:  # FA: ساخت snapshot.
        """
        توضیح: یک snapshot به فرم <dataset>@<snap> ایجاد می‌کند؛ می‌توانید recursive و پراپرتی‌های لازم را بدهید.
        ورودی‌ها:
          - name (str): نام اسنپ‌شات مثل "tank/data@before-deploy".
          - recursive (bool): اگر True، روی زیرمجموعه‌ها هم اعمال می‌شود (-r).
          - props (dict|None): پراپرتی‌های اختیاری در زمان snapshot (با -o key=value).
        خروجی:
          - dict(JSON-Ready): نتیجهٔ ساخت.
        خطاها:
          - ZFSError: خطای اجرای CLI.

        EN: Create a snapshot.
        """
        try:
            args = ["zfs", "snapshot"]
            if recursive:
                args.append("-r")
            if props:
                for k, v in props.items():
                    args += ["-o", f"{k}={v}"]
            args.append(name)
            out, _ = self._run(args)
            return ok({"snapshot": name, "created": True, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def list_snapshots(self, dataset: Optional[str] = None) -> Dict[str, Any]:  # FA: فهرست snapshotها.
        """
        توضیح: لیست snapshotها را با ستون‌های مفید (name, creation, used, refer) بازمی‌گرداند.
        ورودی:
          - dataset (str|None): اگر None باشد، همهٔ snapshotهای سیستم لیست می‌شوند.
        خروجی:
          - dict(JSON-Ready): لیستی از اسنپ‌شات‌ها با اطلاعات پایه.
        خطاها:
          - ZFSError: خطا در اجرای CLI.

        EN: List snapshots with basic columns.
        """
        try:
            target = dataset or ""
            out, _ = self._run(["zfs", "list", "-H", "-o", "name,creation,used,refer", "-t", "snapshot", "-r", target])
            snaps: List[Dict[str, str]] = []
            for ln in out.splitlines():
                if not ln.strip():
                    continue
                name, creation, used, refer = ln.split("\t")
                snaps.append({"name": name, "creation": creation, "used": used, "refer": refer})
            return ok(snaps)
        except Exception as exc:
            return fail(str(exc))

    def bookmark(self, snapshot: str, bookmark: str) -> Dict[str, Any]:  # FA: ساخت bookmark از snapshot.
        """
        توضیح: یک bookmark سبک از snapshot می‌سازد که برای ریپلیکیشن و مرجع‌گذاری مفید است.
        ورودی‌ها:
          - snapshot (str): نام snapshot مبدأ (مانند "tank/data@pre").
          - bookmark (str): نام bookmark مقصد (مانند "tank/data#pre").
        خروجی:
          - dict(JSON-Ready): نتیجهٔ ساخت.
        خطاها:
          - ZFSError: خطا در اجرای CLI.

        EN: Create a bookmark from snapshot.
        """
        try:
            out, _ = self._run(["zfs", "bookmark", snapshot, bookmark])
            return ok({"bookmark": bookmark, "from_snapshot": snapshot, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def list_bookmarks(self, dataset: Optional[str] = None) -> Dict[str, Any]:  # FA: لیست bookmarkها.
        """
        توضیح: تمام bookmarkها را (یا زیر یک دیتاست مشخص) لیست می‌کند.
        ورودی:
          - dataset (str|None): اگر مشخص شود، با -r زیر همان دیتاست جستجو می‌شود.
        خروجی:
          - dict(JSON-Ready): لیست اسامی bookmarkها.
        خطاها:
          - ZFSError: خطا در اجرای CLI.

        EN: List bookmarks under dataset or globally.
        """
        try:
            args = ["zfs", "list", "-H", "-o", "name", "-t", "bookmark"]
            if dataset:
                args += ["-r", dataset]
            out, _ = self._run(args)
            items = [ln.strip() for ln in out.splitlines() if ln.strip()]
            return ok(items)
        except Exception as exc:
            return fail(str(exc))

    def clone(self, snapshot: str, target: str, properties: Optional[Dict[str, str]] = None) -> Dict[str, Any]:  # FA: کلون از snapshot.
        """
        توضیح: از snapshot یک دیتاست نوشتنی جدید می‌سازد (clone) که برای تست/ایزوله‌سازی تغییرات مفید است.
        ورودی‌ها:
          - snapshot (str): نام snapshot مبدأ (مثل "tank/data@pre").
          - target (str): نام دیتاست مقصد (مثل "tank/test/data").
          - properties (dict|None): پراپرتی‌های اولیه برای کلون.
        خروجی:
          - dict(JSON-Ready): نتیجهٔ کلون.
        خطاها:
          - ZFSError: خطا در اجرای CLI.

        EN: Clone a snapshot into a writable dataset.
        """
        try:
            args = ["zfs", "clone"]
            if properties:
                for k, v in properties.items():
                    args += ["-o", f"{k}={v}"]
            args += [snapshot, target]
            out, _ = self._run(args)
            return ok({"cloned": True, "from": snapshot, "to": target, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def promote(self, dataset: str) -> Dict[str, Any]:  # FA: promote کلون برای مستقل‌سازی.
        """
        توضیح: کلون را به دیتاست معمولی تبدیل می‌کند تا وابستگی به والد قطع شود (zfs promote).
        ورودی:
          - dataset (str): نام دیتاست کلون که باید promote شود.
        خروجی:
          - dict(JSON-Ready): نتیجهٔ عملیات.
        خطاها:
          - ZFSError: خطا در اجرای CLI.

        EN: Promote a clone to a normal dataset.
        """
        try:
            out, _ = self._run(["zfs", "promote", dataset])
            return ok({"promoted": dataset, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def rename(self, src: str, dst: str, recursive: bool = False) -> Dict[str, Any]:  # FA: تغییر نام دیتاست.
        """
        توضیح: نام دیتاست را تغییر می‌دهد؛ می‌توان به‌صورت بازگشتی نیز عمل کرد.
        ورودی‌ها:
          - src (str): نام فعلی.
          - dst (str): نام جدید.
          - recursive (bool): اگر True، -r اضافه می‌شود.
        خروجی:
          - dict(JSON-Ready): نتیجهٔ عملیات.
        خطاها:
          - ZFSError: خطا در اجرای CLI.

        EN: Rename dataset (optionally recursive).
        """
        try:
            args = ["zfs", "rename"]
            if recursive:
                args.append("-r")
            args += [src, dst]
            out, _ = self._run(args)
            return ok({"renamed": True, "src": src, "dst": dst, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def rollback(self, dataset: str, to_snapshot: Optional[str] = None,
                 destroy_more_recent: bool = False) -> Dict[str, Any]:  # FA: بازگشت به snapshot.
        """
        توضیح: دیتاست را به یک snapshot مشخص یا آخرین snapshot بازمی‌گرداند. می‌توان snapshotهای جدیدتر را نیز حذف کرد.
        ورودی‌ها:
          - dataset (str): نام دیتاست.
          - to_snapshot (str|None): نام snapshot هدف (با یا بدون "dataset@"؛ هر دو پذیرفته می‌شود).
          - destroy_more_recent (bool): اگر True، -r اضافه می‌شود تا snapshotهای جدیدتر حذف شوند.
        خروجی:
          - dict(JSON-Ready): نتیجهٔ عمل.
        خطاها:
          - ZFSError: خطا در اجرای CLI.

        EN: Rollback dataset to specific or latest snapshot.
        """
        try:
            args = ["zfs", "rollback"]
            if destroy_more_recent:
                args.append("-r")
            if to_snapshot:
                args.append(f"{dataset}@{to_snapshot}" if "@" not in to_snapshot else to_snapshot)
            else:
                args.append(dataset)
            out, _ = self._run(args)
            return ok({"rolled_back": dataset, "to": to_snapshot or "latest", "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def mount(self, dataset: str) -> Dict[str, Any]:  # FA: مونت دیتاست.
        """
        توضیح: دیتاست نوع filesystem را طبق mountpoint خودش سوار می‌کند.
        ورودی:
          - dataset (str): نام دیتاست.
        خروجی:
          - dict(JSON-Ready): نتیجهٔ مونت.
        خطاها:
          - ZFSError: خطا در اجرای CLI.

        EN: Mount filesystem dataset at its mountpoint.
        """
        try:
            out, _ = self._run(["zfs", "mount", dataset])
            return ok({"mounted": dataset, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    def unmount(self, dataset: str, force: bool = False) -> Dict[str, Any]:  # FA: آن‌مونت دیتاست.
        """
        توضیح: دیتاست را پیاده می‌کند؛ در صورت نیاز با -f.
        ورودی‌ها:
          - dataset (str): نام دیتاست.
          - force (bool): اگر True، -f اضافه می‌شود.
        خروجی:
          - dict(JSON-Ready): نتیجهٔ آن‌مونت.
        خطاها:
          - ZFSError: خطا در اجرای CLI.

        EN: Unmount dataset; can force with -f.
        """
        try:
            args = ["zfs", "unmount"]
            if force:
                args.append("-f")
            args.append(dataset)
            out, _ = self._run(args)
            return ok({"unmounted": dataset, "force": force, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    # --------------------------- quotas & space ---------------------------  # FA: سهمیه‌ها و رزرو فضا.

    def set_quota(self, dataset: str, size: str) -> Dict[str, Any]:  # FA: تعیین quota.
        """
        توضیح: محدودیت فضا (quota) را روی دیتاست تنظیم می‌کند؛ مثل "100G" یا "none".
        ورودی‌ها:
          - dataset (str): نام دیتاست.
          - size (str): مقدار سهمیه (مثلاً "100G") یا "none".
        خروجی:
          - dict(JSON-Ready): نتیجهٔ تنظیم.
        خطاها:
          - ZFSError: مقدار نامعتبر یا خطای CLI.

        EN: Set dataset quota (e.g., "100G" or "none").
        """
        return self.set_props(dataset, {"quota": size})

    def set_refquota(self, dataset: str, size: str) -> Dict[str, Any]:  # FA: تعیین refquota.
        """
        توضیح: محدودیت فضا بر مبنای فضای referenced.
        ورودی‌ها:
          - dataset (str): نام دیتاست.
          - size (str): مقدار refquota (مثل "50G" یا "none").
        خروجی:
          - dict(JSON-Ready): نتیجهٔ تنظیم.
        خطاها:
          - ZFSError: خطا در اجرای CLI یا مقدار نامعتبر.

        EN: Set referenced quota.
        """
        return self.set_props(dataset, {"refquota": size})

    def set_reservation(self, dataset: str, size: str) -> Dict[str, Any]:  # FA: تعیین reservation.
        """
        توضیح: رزرو فضای تضمین‌شده برای دیتاست (reservation) را ست می‌کند.
        ورودی‌ها:
          - dataset (str): نام دیتاست.
          - size (str): مقدار رزرو مثل "10G" یا "none".
        خروجی:
          - dict(JSON-Ready): نتیجهٔ تنظیم.
        خطاها:
          - ZFSError: خطا در تنظیم.

        EN: Set reservation.
        """
        return self.set_props(dataset, {"reservation": size})

    def set_refreservation(self, dataset: str, size: str) -> Dict[str, Any]:  # FA: تعیین refreservation.
        """
        توضیح: رزرو بر اساس referenced space را تنظیم می‌کند.
        ورودی‌ها:
          - dataset (str): نام دیتاست.
          - size (str): مقدار (مثل "10G" یا "none").
        خروجی:
          - dict(JSON-Ready): نتیجهٔ تنظیم.
        خطاها:
          - ZFSError: خطا در اجرای CLI.

        EN: Set referenced reservation.
        """
        return self.set_props(dataset, {"refreservation": size})

    def list_user_quotas(self, dataset: str) -> Dict[str, Any]:  # FA: لیست سهمیه‌های کاربر/گروه.
        """
        توضیح: با استفاده از `zfs userspace` و `zfs groupspace` سهمیه‌ها و مصرف کاربران/گروه‌ها را گزارش می‌کند.
        ورودی:
          - dataset (str): نام دیتاست هدف.
        خروجی:
          - dict(JSON-Ready): {"users":[{"name":...,"used":...,"quota":...},...], "groups":[...]}.
        خطاها:
          - ZFSError: خطا در اجرای CLI یا پارس خروجی.

        EN: List per-user and per-group space usage and quotas.
        """
        try:
            out_u, _ = self._run(["zfs", "userspace", "-H", "-o", "name,used,quota", dataset])
            out_g, _ = self._run(["zfs", "groupspace", "-H", "-o", "name,used,quota", dataset])
        except Exception as exc:
            return fail(str(exc))
        try:
            def parse(txt: str) -> List[Dict[str, str]]:
                rows: List[Dict[str, str]] = []
                for ln in txt.splitlines():
                    if not ln.strip():
                        continue
                    n, u, q = ln.split("\t")
                    rows.append({"name": n, "used": u, "quota": q})
                return rows

            return ok({"users": parse(out_u), "groups": parse(out_g)})
        except Exception as exc:
            return fail(str(exc))

    # --------------------------- tuning ---------------------------  # FA: تنظیمات عملکردی مانند compression/dedup/...

    def enable_compression(self, dataset: str, algo: str = "lz4") -> Dict[str, Any]:  # FA: فعال‌سازی compression.
        """
        توضیح: فشرده‌سازی را برای دیتاست فعال می‌کند. الگوریتم‌ها: lz4, zstd, gzip, off.
        ورودی‌ها:
          - dataset (str): نام دیتاست.
          - algo (str): نام الگوریتم (پیش‌فرض lz4).
        خروجی:
          - dict(JSON-Ready): نتیجهٔ تنظیم.
        خطاها:
          - ZFSError: خطا در تنظیم.

        EN: Enable compression with given algorithm.
        """
        return self.set_props(dataset, {"compression": algo})

    def enable_dedup(self, dataset: str, mode: str = "on") -> Dict[str, Any]:  # FA: فعال‌سازی deduplication.
        """
        توضیح: deduplication را فعال/غیرفعال می‌کند. مقادیر مجاز: on, verify, off.
        ورودی‌ها:
          - dataset (str): نام دیتاست.
          - mode (str): یکی از on/verify/off.
        خروجی:
          - dict(JSON-Ready): نتیجهٔ تنظیم.
        خطاها:
          - ZFSError: خطا در تنظیم.

        EN: Enable/disable deduplication.
        """
        return self.set_props(dataset, {"dedup": mode})

    def set_record_or_volblock(self, dataset: str, size: str = "128K") -> Dict[str, Any]:  # FA: تعیین recordsize/volblocksize.
        """
        توضیح: اگر دیتاست از نوع zvol باشد volblocksize تنظیم می‌شود و اگر filesystem باشد recordsize.
        ورودی‌ها:
          - dataset (str): نام دیتاست.
          - size (str): مقدار اندازهٔ بلاک (مثلاً "16K", "128K", "1M").
        خروجی:
          - dict(JSON-Ready): نتیجهٔ تنظیم.
        خطاها:
          - ZFSError: خطا در خواندن پراپرتی‌ها یا تنظیم.

        EN: Set volblocksize for zvol or recordsize for filesystem.
        """
        props = self.get_props(dataset)
        if not props["ok"]:
            return props
        p = props["data"]
        if p.get("type") == "volume" or "volblocksize" in p:
            return self.set_props(dataset, {"volblocksize": size})
        return self.set_props(dataset, {"recordsize": size})

    def set_mountpoint(self, dataset: str, path: str) -> Dict[str, Any]:  # FA: تعیین mountpoint.
        """
        توضیح: مسیر mountpoint دیتاست را تنظیم می‌کند.
        ورودی‌ها:
          - dataset (str): نام دیتاست.
          - path (str): مسیر مقصد.
        خروجی:
          - dict(JSON-Ready): نتیجهٔ تنظیم.
        خطاها:
          - ZFSError: خطا در تنظیم.

        EN: Set dataset mountpoint path.
        """
        return self.set_props(dataset, {"mountpoint": path})

    def set_atime(self, dataset: str, mode: str = "off") -> Dict[str, Any]:  # FA: تنظیم atime.
        """
        توضیح: روشن/خاموش کردن atime برای کاهش writeهای اضافی.
        ورودی‌ها:
          - dataset (str): نام دیتاست.
          - mode (str): "on" یا "off".
        خروجی:
          - dict(JSON-Ready): نتیجهٔ تنظیم.
        خطاها:
          - ZFSError: خطا در تنظیم.

        EN: Toggle atime (on/off).
        """
        return self.set_props(dataset, {"atime": mode})

    # --------------------------- send / receive ---------------------------  # FA: ریپلیکیشن با send/receive.

    def send(self, snapshot: str, incremental_from: Optional[str] = None, raw: bool = False,
             compressed: bool = True, resume_token: Optional[str] = None,
             output_file: Optional[str] = None) -> Dict[str, Any]:  # FA: تولید استریم send.
        """
        توضیح: یک استریم send تولید می‌کند (برای ریپلیکیشن/بکاپ). پیشنهاد می‌شود برای استریم‌های بزرگ به فایل نوشته شود.
        ورودی‌ها:
          - snapshot (str): نام snapshot مبدأ (مانند "tank/data@A").
          - incremental_from (str|None): اگر داده شود، استریم افزایشی از این snapshot مبنا تولید می‌شود (-I).
          - raw (bool): اگر True، از --raw استفاده می‌شود (برای داده‌های رمزگذاری‌شده).
          - compressed (bool): اگر True، -c برای استریم فشرده اضافه می‌شود.
          - resume_token (str|None): اگر داده شود، ارسال از میانه (resume) با -t انجام می‌شود.
          - output_file (str|None): اگر داده شود، استریم در این مسیر نوشته می‌شود؛ وگرنه در حافظه گرفته و طولش گزارش می‌شود.
        خروجی:
          - dict(JSON-Ready): اگر output_file مشخص شده باشد، مسیر فایل؛ در غیر اینصورت اندازهٔ استریم بر حسب بایت.
        خطاها:
          - ZFSError: خطا در اجرای CLI یا تایم‌اوت.

        EN: Produce a replication stream (prefer writing to file).
        """
        try:
            args = ["zfs", "send"]
            if raw:
                args.append("--raw")
            if compressed:
                args.append("-c")
            if resume_tokEN:
                args += ["-t", resume_token]
            elif incremental_from:
                args += ["-I", incremental_from]
            args.append(snapshot)

            if self.dry_run:
                return ok({"stdout": " ".join(args), "dry_run": True})

            if output_file:
                with open(output_file, "wb") as f:
                    proc = subprocess.Popen(args, stdout=f, stderr=subprocess.PIPE)
                    _, err = proc.communicate(timeout=self.run_timeout)
                    if proc.returncode != 0:
                        raise ZFSError(err.decode(errors="ignore"))
                return ok({"snapshot": snapshot, "output_file": output_file})
            else:
                proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, err = proc.communicate(timeout=self.run_timeout)
                if proc.returncode != 0:
                    raise ZFSError(err.decode(errors="ignore"))
                return ok({"snapshot": snapshot, "stream_size": len(out)})
        except Exception as exc:
            return fail(str(exc))

    def receive(self, target: str, input_file: Optional[str] = None, stdin_bytes: Optional[bytes] = None,
                force: bool = False, nomount: bool = False, verbose: bool = False) -> Dict[str, Any]:  # FA: دریافت استریم.
        """
        توضیح: استریم send را در مقصد دریافت می‌کند. منبع می‌تواند فایل یا دادهٔ باینری در حافظه باشد.
        ورودی‌ها:
          - target (str): نام دیتاست مقصد (مثل "backup/data").
          - input_file (str|None): مسیر فایل حاوی استریم (اختیاری).
          - stdin_bytes (bytes|None): خود استریم به‌صورت باینری (اختیاری؛ با input_file توأمان نباشد).
          - force (bool): اگر True، -F برای rollback/destroy جدیدترها اعمال می‌شود.
          - nomount (bool): اگر True، -u برای عدم مونت پس از دریافت.
          - verbose (bool): اگر True، -v برای جزئیات بیشتر.
        خروجی:
          - dict(JSON-Ready): نتیجهٔ دریافت.
        خطاها:
          - ZFSError: خطا در اجرای CLI یا ورودی نامعتبر (هر دو منبع داده داده شده باشد).

        EN: Receive a replication stream into target dataset.
        """
        try:
            if input_file and stdin_bytes:
                return fail("Provide either input_file or stdin_bytes, not both.", code="invalid_request")
            args = ["zfs", "receive"]
            if force:
                args.append("-F")
            if nomount:
                args.append("-u")
            if verbose:
                args.append("-v")
            args.append(target)

            if input_file:
                with open(input_file, "rb") as f:
                    data = f.read()
                out, _ = self._run(args, stdin=data)
                return ok({"received": True, "target": target, "from": input_file, "stdout": out})
            else:
                out, _ = self._run(args, stdin=stdin_bytes)
                return ok({"received": True, "target": target, "stdin_bytes": stdin_bytes is not None, "stdout": out})
        except Exception as exc:
            return fail(str(exc))

    # --------------------------- diagnostics ---------------------------  # FA: ابزارهای عیب‌یابی.

    def diff(self, older: str, newer: str) -> Dict[str, Any]:  # FA: مقایسهٔ تغییرات.
        """
        توضیح: خروجی `zfs diff` را بین دو نقطه (snapshot/dataset) بازمی‌گرداند.
        ورودی‌ها:
          - older (str): نقطهٔ قدیمی‌تر (مانند "tank/data@A" یا خود "tank/data").
          - newer (str): نقطهٔ جدیدتر.
        خروجی:
          - dict(JSON-Ready): متن خام و آرایهٔ خطوط.
        خطاها:
          - ZFSError: خطا در اجرای CLI.

        EN: Return `zfs diff` output between two points.
        """
        try:
            out, _ = self._run(["zfs", "diff", older, newer])
            return ok({"raw": out, "lines": [ln for ln in out.splitlines()]})
        except Exception as exc:
            return fail(str(exc))

    def history(self, dataset_or_pool: Optional[str] = None) -> Dict[str, Any]:  # FA: تاریخچهٔ عملیات.
        """
        توضیح: تاریخچهٔ عملیات ZFS را بازمی‌گرداند (در سطح global یا محدود به یک pool/dataset).
        ورودی:
          - dataset_or_pool (str|None): اگر None باشد، `zfs history` کلی؛ اگر نام pool باشد سعی در `zpool history` می‌کنیم.
        خروجی:
          - dict(JSON-Ready): شامل raw history و scope.
        خطاها:
          - ZFSError: خطا در اجرای CLI.

        EN: Return ZFS history for auditing.
        """
        try:
            if dataset_or_pool:
                try:
                    out, _ = self._run(["zpool", "history", dataset_or_pool])
                    return ok({"scope": "pool", "name": dataset_or_pool, "raw": out})
                except ZFSError:
                    out, _ = self._run(["zfs", "history", dataset_or_pool])
                    return ok({"scope": "dataset", "name": dataset_or_pool, "raw": out})
            out, _ = self._run(["zfs", "history"])
            return ok({"scope": "global", "raw": out})
        except Exception as exc:
            return fail(str(exc))

    # --------------------------- comprehensive export ---------------------------  # FA: نمای کامل سیستم برای داشبورد/مانیتورینگ.

    def export_full_state(self) -> Dict[str, Any]:  # FA: خروجی جامع وضعیت ZFS.
        """
        توضیح: نمایی کامل و عمیق از وضعیت ZFS بازمی‌گرداند تا در داشبورد و نظارت استفاده شود. شامل:
          - اطلاعات هر pool: نام، guid، state/health، پراپرتی‌های کلیدی، featureها، خروجی خام status -v، و iostat.
          - دیتاست‌های زیر هر pool: نوع، تمام پراپرتی‌ها، لیست snapshotها و bookmarkها.
          - خلاصه‌ای از تمام snapshotهای موجود در کل سیستم.
        ورودی:
          - ندارد.
        خروجی:
          - dict(JSON-Ready): ساختار لایه‌لایهٔ کامل از وضعیت ZFS.
        خطاها:
          - ممکن است برخی بخش‌ها به‌علت خطا ناپدید شوند اما تابع در مجموع خروجی ok(...) می‌دهد مگر خطای کلی رخ دهد.

        EN: Export a deep JSON inventory of pools/datasets/snapshots/features.
        """
        try:
            full: Dict[str, Any] = {"pools": []}
            for p in self.zfs.pools:
                pool_entry: Dict[str, Any] = {
                    "name": p.name,
                    "guid": str(getattr(p, "guid", "")),
                    "state": str(getattr(p, "state", "")),
                    "health": str(getattr(p, "health", "")),
                    "props": {},
                    "features": [],
                    "status_verbose": None,
                    "iostat": None,
                    "datasets": [],
                }

                # pool props (best-effort)
                for prop in ("ashift", "autoexpand", "autoreplace", "autotrim", "comment", "cachefile"):
                    try:
                        if hasattr(p, "get_prop"):
                            pool_entry["props"][prop] = str(self._safe_prop_value(p.get_prop(prop)))
                    except Exception:
                        pass

                # features list
                try:
                    feat = self.features(p.name)
                    if feat["ok"]:
                        pool_entry["features"] = feat["data"]
                except Exception:
                    pass

                # status -v raw
                try:
                    stv = self.pool_status_verbose(p.name)
                    if stv["ok"]:
                        pool_entry["status_verbose"] = stv["data"]["raw"]
                except Exception:
                    pass

                # single iostat sample
                try:
                    io = self.pool_iostat(p.name, samples=1, interval=1)
                    if io["ok"]:
                        pool_entry["iostat"] = io["data"]["raw"]
                except Exception:
                    pass

                # datasets under pool
                try:
                    ds_list = self.list_datasets(pool=p.name, types=("filesystem", "volume"))
                    if ds_list["ok"]:
                        for item in ds_list["data"]:
                            ds_name = item["name"]
                            ds_entry: Dict[str, Any] = {
                                "name": ds_name,
                                "type": item["type"],
                                "props": {},
                                "snapshots": [],
                                "bookmarks": [],
                            }
                            gp = self.get_props(ds_name)
                            if gp["ok"]:
                                ds_entry["props"] = gp["data"]
                            snaps = self.list_snapshots(ds_name)
                            if snaps["ok"]:
                                ds_entry["snapshots"] = snaps["data"]
                            bms = self.list_bookmarks(ds_name)
                            if bms["ok"]:
                                ds_entry["bookmarks"] = bms["data"]
                            pool_entry["datasets"].append(ds_entry)
                except Exception:
                    pass

                full["pools"].append(pool_entry)

            # global snapshots
            try:
                all_snaps = self.list_snapshots()
                if all_snaps["ok"]:
                    full["all_snapshots"] = all_snaps["data"]
            except Exception:
                full["all_snapshots"] = []

            return ok(full, meta={"source": "libzfs+cli"})
        except Exception as exc:
            return fail(str(exc))


__all__ = ["ZFSManager", "ZFSError", "ok", "fail"]  # اگر درهنگام ایمپورت ماژول تمام موارد را ایمپورت کنیذ(یعنی توسط * عمل ایمپورت انجام شود) آنگاه چه مواردی از مآژول ایمپورت شوند
