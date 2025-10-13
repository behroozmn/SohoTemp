#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
from typing import Any, Dict, Optional
from django.contrib.auth.models import User
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

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


class OSManagement:
    def __init__(self, config_path: str = "/etc/passwd") -> None:
        self.config_path = config_path

    def list_users(self, include_system: bool = False) -> Dict[str, Any]:
        """
        Return a list of Linux system users.
        Args:
            include_system (bool): If False (default), exclude system users (UID < 1000)
                                   If True, include all users from /etc/passwd
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

    def add_user(self, username: str, login_shell: str = "/bin/bash"):
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
                ["/usr/bin/sudo", "/usr/sbin/useradd", "-M", "-s", login_shell, username],
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

    def delete_user(self, username: str, remove_home: bool = False) -> Dict[str, Any]:
        """
        Delete a Linux system user.

        Args:
            username (str): The username to delete.
            remove_home (bool): If True, also delete the user's home directory and mail spool.

        Returns:
            Dict in ok()/fail() format.
        """
        if not username or not isinstance(username, str):
            return fail("Username must be a non-empty string.")

        if not username.replace("_", "").replace("-", "").replace(".", "").isalnum():
            return fail("Invalid username: only letters, digits, ., -, _ allowed.")

        try:
            # Build command
            cmd = ["/usr/bin/sudo", "/usr/sbin/userdel"]
            if remove_home:
                cmd.append("-r")
            cmd.append(username)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode == 0:
                details = f"User '{username}' deleted successfully."
                if remove_home:
                    details += " Home directory and mail spool were also removed."
                return ok(
                    {"username": username, "removed_home": remove_home},
                    details=details
                )
            else:
                stderr = result.stderr.strip()
                if "cannot remove" in stderr.lower() and "home" in stderr.lower():
                    return fail(
                        f"User deleted but failed to remove home directory: {stderr}",
                        code="partial_deletion",
                        extra={"stderr": stderr}
                    )
                elif "user does not exist" in stderr.lower() or "cannot find" in stderr.lower():
                    return fail(
                        f"User '{username}' does not exist.",
                        code="user_not_found",
                        extra={"stderr": stderr}
                    )
                else:
                    return fail(
                        f"Failed to delete user: {stderr}",
                        code="user_deletion_failed",
                        extra={"stderr": stderr, "stdout": result.stdout}
                    )

        except subprocess.TimeoutExpired:
            return fail("userdel command timed out.", code="timeout")
        except FileNotFoundError:
            return fail("userdel command not found – is this a Linux system?", code="command_missing")
        except Exception as e:
            return fail(
                f"Exception during user deletion: {str(e)}",
                code="exception",
                extra={"exception": str(e)}
            )


class WebManager:
    """
    Django User Management Utility
    Works with Django's built-in User model.
    All methods return standardized ok/fail responses.
    """

    @staticmethod
    def create_user(username: str, email: str, password: str, is_superuser: bool = False, first_name: str = "", last_name: str = "") -> Dict[str, Any]:
        """
        Create a new Django user (superuser or regular).
        Endpoint: POST /api/users/create/
        """
        if not username or not password:
            return fail("Username and password are required.", "missing_fields")

        if User.objects.filter(username=username).exists():
            return fail(f"User '{username}' already exists.", "user_exists")

        try:
            validate_password(password)
        except ValidationError as e:
            return fail("Password validation failed.", "invalid_password", {"errors": list(e.messages)})

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                )
                if is_superuser:
                    user.is_staff = True
                    user.is_superuser = True
                    user.save()

            return ok({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_superuser": user.is_superuser,
                "created_at": user.date_joined.isoformat()
            }, {"message": "User created successfully."})

        except Exception as e:
            return fail(f"Failed to create user: {str(e)}", "creation_failed")

    @staticmethod
    def delete_user(username: str, delete_from_db: bool = True) -> Dict[str, Any]:
        """
        Delete a Django user by username.
        Endpoint: DELETE /api/users/{username}/
        """
        try:
            user = User.objects.get(username=username)
            user_id = user.id
            user.delete()
            return ok({
                "deleted_user_id": user_id,
                "username": username
            }, {"message": f"User '{username}' deleted successfully."})
        except User.DoesNotExist:
            return fail(f"User '{username}' does not exist.", "user_not_found")
        except Exception as e:
            return fail(f"Failed to delete user: {str(e)}", "deletion_failed")

    @staticmethod
    def change_password(username: str, new_password: str) -> Dict[str, Any]:
        """
        Change password for an existing Django user.
        Endpoint: PATCH /api/users/{username}/change-password/
        """
        if not new_password:
            return fail("New password is required.", "missing_password")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return fail(f"User '{username}' does not exist.", "user_not_found")

        try:
            validate_password(new_password, user=user)
        except ValidationError as e:
            return fail("Password validation failed.", "invalid_password", {"errors": list(e.messages)})

        try:
            user.set_password(new_password)
            user.save()
            return ok({
                "username": username
            }, {"message": "Password updated successfully."})
        except Exception as e:
            return fail(f"Failed to update password: {str(e)}", "password_update_failed")

    @staticmethod
    def list_users() -> Dict[str, Any]:
        """
        List all Django users with full details.
        Endpoint: GET /api/users/
        """
        try:
            users = User.objects.all().order_by('id')
            data = [
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "first_name": u.first_name,
                    "last_name": u.last_name,
                    "is_active": u.is_active,
                    "is_staff": u.is_staff,
                    "is_superuser": u.is_superuser,
                    "last_login": u.last_login.isoformat() if u.last_login else None,
                    "date_joined": u.date_joined.isoformat(),
                }
                for u in users
            ]
            return ok(data, {"count": len(data)})
        except Exception as e:
            return fail(f"Failed to fetch users: {str(e)}", "list_failed")
