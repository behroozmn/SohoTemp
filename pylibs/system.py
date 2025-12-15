# soho_core_api/pylibs/power.py
from __future__ import annotations
from typing import Dict, Any
from pylibs import CLICommandError, run_cli_command


class PowerManager:
    """
    مدیریت عملیات خاموش‌کردن و ریبوت سیستم از طریق systemd.

    این کلاس فقط دو عملیات مجاز را پشتیبانی می‌کند:
    - خاموش‌کردن سیستم (poweroff)
    - راه‌اندازی مجدد سیستم (reboot)

    تمام دستورات با استفاده از systemctl و sudo اجرا می‌شوند.
    """

    def _execute_power_command(self, action: str) -> None:
        """
        اجرای دستور systemctl برای عملیات خاموش‌کردن یا ریبوت.

        Args:
            action (str): یکی از مقادیر "poweroff" یا "reboot"

        Raises:
            ValueError: اگر action معتبر نباشد
            CLICommandError: در صورت خطا در اجرای دستور
        """
        if action not in ("poweroff", "reboot"):
            raise ValueError(f"عملیات '{action}' پشتیبانی نمی‌شود. مقادیر مجاز: poweroff, reboot")
        run_cli_command(["/usr/bin/systemctl", action], use_sudo=True)

    def poweroff(self) -> None:
        """
        خاموش‌کردن سیستم با استفاده از `systemctl poweroff`.

        Raises:
            CLICommandError: در صورت خطا در اجرای دستور
        """
        self._execute_power_command("poweroff")

    def reboot(self) -> None:
        """
        راه‌اندازی مجدد سیستم با استفاده از `systemctl reboot`.

        Raises:
            CLICommandError: در صورت خطا در اجرای دستور
        """
        self._execute_power_command("reboot")


# soho_core_api/pylibs/django_user.py
from typing import Dict, Any, Optional, List, Union
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from pylibs import logger


class DjangoUserManager:
    """
    مدیریت کاربران داخلی جنگو (Django Users) با پشتیبانی از فارسی و تمام عملیات رایج.

    این کلاس:
    - فقط با مدل داخلی `django.contrib.auth.models.User` کار می‌کند.
    - از تاپل برای بازگشتی استفاده نمی‌کند.
    - مستقل از `StandardResponse` است.
    - تمام خطاها را به‌صورت استثنا (Exception) raise می‌کند.
    """

    def create_user(self, username: str, password: str, email: Optional[str] = None, first_name: Optional[str] = None, last_name: Optional[str] = None, is_active: bool = True, is_staff: bool = False, is_superuser: bool = False, ) -> Dict[str, Any]:
        """
        ایجاد یک کاربر جدید در دیتابیس جنگو.

        Args:
            username: نام کاربری (منحصربه‌فرد، الفبای لاتین یا فارسی مجاز است)
            password: رمز عبور
            email: ایمیل (اختیاری)
            first_name: نام (پشتیبانی از فارسی)
            last_name: نام خانوادگی (پشتیبانی از فارسی)
            is_active: آیا کاربر فعال باشد؟
            is_staff: دسترسی به پنل ادمین
            is_superuser: کاربر ادمین کامل

        Returns:
            Dict شامل جزئیات کاربر ایجادشده

        Raises:
            IntegrityError: اگر نام کاربری تکراری باشد
            ValidationError: اگر داده‌ها معتبر نباشند
        """
        if not username:
            raise ValueError("نام کاربری اجباری است.")

        try:
            with transaction.atomic():
                user = User.objects.create_user(username=username, password=password,
                                                email=email or "",
                                                first_name=first_name or "",
                                                last_name=last_name or "", )
                user.is_active = is_active
                user.is_staff = is_staff
                user.is_superuser = is_superuser
                user.save()

                return self._serialize_user(user)
        except IntegrityError as e:
            logger.error(f"خطا در ایجاد کاربر '{username}': {e}")
            raise
        except ValidationError as e:
            logger.error(f"اعتبارسنجی ناموفق برای کاربر '{username}': {e}")
            raise

    def delete_user(self, username: str) -> None:
        """
        حذف یک کاربر از دیتابیس جنگو.

        Args:
            username: نام کاربری

        Raises:
            User.DoesNotExist: اگر کاربر یافت نشود
        """
        try:
            user = User.objects.get(username=username)
            user.delete()
        except User.DoesNotExist:
            raise

    def change_password(self, username: str, new_password: str) -> None:
        """
        تغییر رمز عبور یک کاربر.

        Args:
            username: نام کاربری
            new_password: رمز عبور جدید

        Raises:
            User.DoesNotExist: اگر کاربر یافت نشود
        """
        try:
            user = User.objects.get(username=username)
            user.set_password(new_password)
            user.save(update_fields=["password"])
        except User.DoesNotExist:
            raise

    def update_user(self, username: str, email: Optional[str] = None, first_name: Optional[str] = None, last_name: Optional[str] = None, is_active: Optional[bool] = None, is_staff: Optional[bool] = None, is_superuser: Optional[bool] = None, ) -> Dict[str, Any]:
        """
        به‌روزرسانی فیلدهای یک کاربر.

        Args:
            username: نام کاربری
            سایر فیلدها: مقدار جدید (None = بدون تغییر)

        Returns:
            Dict به‌روزشده

        Raises:
            User.DoesNotExist: اگر کاربر یافت نشود
        """
        try:
            user = User.objects.get(username=username)
            if email is not None:
                user.email = email
            if first_name is not None:
                user.first_name = first_name
            if last_name is not None:
                user.last_name = last_name
            if is_active is not None:
                user.is_active = is_active
            if is_staff is not None:
                user.is_staff = is_staff
            if is_superuser is not None:
                user.is_superuser = is_superuser
            user.save()
            return self._serialize_user(user)
        except User.DoesNotExist:
            raise

    def get_user(self, username: str) -> Dict[str, Any]:
        """
        دریافت اطلاعات یک کاربر.

        Raises:
            User.DoesNotExist
        """
        user = User.objects.get(username=username)
        return self._serialize_user(user)

    def list_users(self) -> List[Dict[str, Any]]:
        """لیست تمام کاربران."""
        return [self._serialize_user(u) for u in User.objects.all()]

    def _serialize_user(self, user: User) -> Dict[str, Any]:
        """تبدیل مدل User به دیکشنری قابل JSON."""
        return {"id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "date_joined": user.date_joined.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None, }
