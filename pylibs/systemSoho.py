#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
from typing import Any, Dict, Optional, List

def ok(data: Any, details: Any = None) -> Dict[str, Any]:
    return {
        "ok": True,
        "error": None,
        "data": data,
        "details": details or {}
    }

def fail(message: str, code: str = "service_error", extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "ok": False,
        "error": {"code": code, "message": message, "extra": extra or {}},
        "data": None,
        "details": {}
    }

class SystemManagements:
    def __init__(self, config_path: str = "/etc/passwd") -> None:
        self.config_path = config_path

    def list_users(self, include_system: bool = True) -> Dict[str, Any]:
        """
        Return a list of Linux system users.

        Args:
            include_system (bool): If False (default), exclude system users (UID < 1000).
                                   If True, include all users from /etc/passwd.

        Returns:
            Dict in the format of ok() or fail().
        """
        try:
            users = []
            with open("/etc/passwd", "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(":")
                    if len(parts) < 3:
                        continue
                    username = parts[0]
                    try:
                        uid = int(parts[2])
                    except ValueError:
                        continue

                    # Exclude system users by default (UID < 1000)
                    if not include_system and uid < 1000:
                        continue

                    users.append(username)

            users.sort()
            return ok(users, details={"count": len(users), "include_system": include_system})

        except FileNotFoundError:
            return fail("/etc/passwd not found – are you on a Linux system?")
        except PermissionError:
            return fail("Permission denied reading /etc/passwd")
        except Exception as e:
            return fail(f"Unexpected error while reading user list: {str(e)}", extra={"exception": str(e)})

    def add_user(self, username: str,login_shell: str = "/bin/bash"):
        """
        Add a new system user with:
          - No home directory (-M)
          - No shell access (-s /usr/sbin/nologin)

        Args:
            username (str): Desired username (must be valid for Linux)
            login_shell: [login_shell] or  [/usr/sbin/nologin]
        Returns:
            Dict in ok()/fail() format.
        """
        if not username or not isinstance(username, str):
            return fail("Username must be a non-empty string.")

        # Basic validation (Linux username rules)
        if not username.replace("_", "").replace("-", "").replace(".", "").isalnum():
            return fail("Invalid username: only letters, digits, ., -, _ allowed.")
        if username.startswith("-") or len(username) > 32:
            return fail("Username too long or starts with invalid character.")

        try:
            result = subprocess.run(
                ["/usr/bin/sudo","/usr/sbin/useradd", "-M", "-s", login_shell, username],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode == 0:
                return ok(
                    {"username": username},
                    details="User created successfully with no home and no shell."
                )
            else:
                stderr = result.stderr.strip()
                if "already exists" in stderr.lower():
                    return fail(f"User '{username}' already exists.", code="user_exists")
                else:
                    return fail(
                        f"Failed to create user: {stderr}",
                        code="user_creation_failed",
                        extra={"stderr": stderr, "stdout": result.stdout}
                    )

        except FileNotFoundError:
            return fail("useradd command not found – is this a Linux system?")
        except Exception as e:
            return fail(f"Exception during user creation: {str(e)}", extra={"exception": str(e)})

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