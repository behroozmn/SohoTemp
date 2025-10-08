import subprocess
from typing import Dict, Any


def ok(data: Any, detail: Any = None) -> Dict[str, Any]:
    return {"ok": True, "error": None, "data": data, "details": detail}


def fail(message: str, code: str = "System_error", extra: str = None) -> Dict[str, Any]:
    """Return a failure envelope (DRF-ready)."""
    return {"ok": False, "error": {"code": code, "message": message, "extra": extra}}

class SystemManager:

    @staticmethod
    def shutdown_or_restart(action: str) -> Dict[str, Any]:
        """
        سیستم را خاموش یا ریستارت می‌کند.

        :param action: باید 'shutdown' یا 'restart' باشد.
        :return: پاسخ موفقیت یا خطا
        """
        if action not in ('shutdown', 'restart'):
            return fail("عملیات نامعتبر است. فقط 'shutdown' یا 'restart' مجاز است.", code="invalid_action")

        try:
            if action == 'shutdown':
                # استفاده از systemctl برای خاموش کردن
                subprocess.run(['/usr/bin/sudo', '/usr/bin/systemctl', 'poweroff'], check=True, timeout=10)
            elif action == 'restart':
                # استفاده از systemctl برای ریستارت
                subprocess.run(['/usr/bin/sudo', '/usr/bin/systemctl', 'reboot'], check=True, timeout=10)

            # این خط معمولاً اجرا نمی‌شود چون سیستم خاموش/ریست می‌شود!
            return ok({"action": action}, "دستور ارسال شد. سیستم در حال خاموش/ریست شدن است.")

        except subprocess.TimeoutExpired:
            return fail("زمان اجرای دستور به پایان رسید.", code="timeout")
        except subprocess.CalledProcessError as e:
            return fail(f"خطا در اجرای دستور سیستم: خروجی خطا: {e.stderr}", code="system_cmd_error")
        except PermissionError:
            return fail("عدم دسترسی: نیاز به دسترسی root دارد.", code="permission_denied")
        except Exception as e:
            return fail(f"خطای غیرمنتظره: {str(e)}", code="unexpected_error")