#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import configparser
from typing import Any, Dict, Optional
import subprocess
import os
import shutil
import pwd
import grp
from datetime import datetime


def ok(data: Any, detail: Any = None) -> Dict[str, Any]:
    """Return a success envelope (DRF-ready)."""
    return {"ok": True, "error": None, "data": data, "details": detail}


def fail(message: str, code: str = "samba_error", extra: str = None) -> Dict[str, Any]:
    """Return a failure envelope (DRF-ready)."""
    return {"ok": False, "error": {"code": code, "message": message, "extra": extra}}


class FileManager:
    def __init__(self, config_path: str = "/etc/samba/smb.conf") -> None:
        self.config_path = config_path

    def set_permissions(
            self,
            path: str,
            mode: str,
            owner: str,
            group: str,
            recursive: bool = True
    ) -> Dict[str, Any]:
        """Set ownership and permissions on an existing path (recursive by default)."""
        if not os.path.exists(path):
            return fail(f"Path does not exist: {path}", code="path_not_found")

        try:
            mode_int = int(mode, 8)
        except ValueError:
            return fail(f"Invalid permission mode: {mode}. Must be octal (e.g., '0755').", code="invalid_mode")

        try:
            uid = pwd.getpwnam(owner).pw_uid
            gid = grp.getgrnam(group).gr_gid
        except KeyError as e:
            return fail(f"User or group not found: {e}", code="user_or_group_not_found")

        try:
            if recursive and os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    os.chown(root, uid, gid)
                    os.chmod(root, mode_int)
                    for d in dirs:
                        os.chown(os.path.join(root, d), uid, gid)
                        os.chmod(os.path.join(root, d), mode_int)
                    for f in files:
                        os.chown(os.path.join(root, f), uid, gid)
                        os.chmod(os.path.join(root, f), mode_int)
            else:
                os.chown(path, uid, gid)
                os.chmod(path, mode_int)

            return ok(
                {"path": path, "mode": mode, "owner": owner, "group": group, "recursive": recursive},
                detail="Permissions and ownership applied successfully."
            )

        except PermissionError:
            return fail("Permission denied. Run as root.", code="permission_denied")
        except Exception as e:
            return fail(f"Error setting permissions: {str(e)}", code="os_error", extra=str(e))

    def create_directory(
            self,
            path: str,
            mode: str,
            owner: str,
            group: str
    ) -> Dict[str, Any]:
        """Create a directory with given permissions, owner, and group. Do nothing if exists."""
        if os.path.exists(path):
            return ok({"path": path}, detail="Path already exists. No action taken.")

        try:
            mode_int = int(mode, 8)
        except ValueError:
            return fail(f"Invalid permission mode: {mode}. Must be octal (e.g., '0755').", code="invalid_mode")

        try:
            uid = pwd.getpwnam(owner).pw_uid
            gid = grp.getgrnam(group).gr_gid
        except KeyError as e:
            return fail(f"User or group not found: {e}", code="user_or_group_not_found")

        try:
            os.makedirs(path, mode=mode_int, exist_ok=True)
            os.chown(path, uid, gid)
            return ok({"path": path, "mode": mode, "owner": owner, "group": group}, detail="Directory created successfully.")
        except PermissionError:
            return fail("Permission denied. Run as root.", code="permission_denied")
        except Exception as e:
            return fail(f"Error creating directory: {str(e)}", code="os_error", extra=str(e))

    def get_file_info(self, path: str) -> Dict[str, Any]:
        """Check if path exists and return permissions, owner, group."""
        if not os.path.exists(path):
            return fail(f"Path does not exist: {path}", code="path_not_found")

        try:
            stat_info = os.stat(path)
            mode = stat_info.st_mode
            uid = stat_info.st_uid
            gid = stat_info.st_gid

            permissions = f"{mode & 0o777:04o}"

            try:
                owner = pwd.getpwuid(uid).pw_name
            except KeyError:
                owner = str(uid)

            try:
                group = grp.getgrgid(gid).gr_name
            except KeyError:
                group = str(gid)

            data = {
                "path": path,
                "permissions": permissions,
                "owner": owner,
                "group": group,
                "is_directory": os.path.isdir(path)
            }

            return ok(data, detail="File info retrieved successfully.")

        except Exception as e:
            return fail(f"Error reading file info: {str(e)}", code="os_error", extra=str(e))
