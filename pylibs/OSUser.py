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

class UserManager:
    def __init__(self, config_path: str = "/etc/passwd") -> None:
        self.config_path = config_path

    def list_users(self, include_system: bool = False) -> Dict[str, Any]:
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