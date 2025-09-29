#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import configparser
from typing import Any, Dict, Optional
import subprocess
import os
import shutil
from datetime import datetime


def ok(data: Any, detail: Any = None) -> Dict[str, Any]:
    """Return a success envelope (DRF-ready)."""
    return {"ok": True, "error": None, "data": data, "details": detail}


def fail(message: str, code: str = "samba_error", extra: str = None) -> Dict[str, Any]:
    """Return a failure envelope (DRF-ready)."""
    return {"ok": False, "error": {"code": code, "message": message, "extra": extra}}


class SambaManager:
    def __init__(self, config_path: str = "/etc/samba/smb.conf") -> None:
        self.config_path = config_path

    def add_samba_share_block(self, share_name, path,
                              create_mask="0777", directory_mask="0777",
                              valid_users=None,
                              available=True, browseable=True,
                              read_only=False, guest_ok=False, inherit_permissions=False,
                              max_connections="0"):
        # --- ثبت زمان ---
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        # --- بررسی دسترسی ---
        if os.geteuid() != 0:
            return fail("This function must be run as root (sudo)", extra="نیاز به دسترسی روت دارد")

        if not os.path.isabs(path):
            return fail("Path must be an absolute path.", extra="نام فایل را باید کامل وارد نمایید")

        # Normalize lists to space-separated strings
        def list_to_str(lst):
            if lst is None:
                return ""
            if isinstance(lst, str):
                return lst.strip()
            return " ".join(str(u).strip() for u in lst if u)

        valid_users_str = list_to_str(valid_users)

        # Build the share block exactly as requested
        share_block = f"""#Begin: {share_name}
[{share_name}]
path = {path}
create mask = {create_mask}
directory mask = {directory_mask}
max connections = {max_connections}
read only = {'Yes' if read_only else 'No'}
available = {'Yes' if available else 'No'}
guest ok = {'Yes' if guest_ok else 'No'}
browseable = {'Yes' if browseable else 'No'}
inherit permissions = {'Yes' if inherit_permissions else 'No'}
valid users = {valid_users_str}
#End: {share_name} - CreatedTime: {timestamp}
"""

        # --- ایجاد نسخه پشتیبان با تاریخ ---
        backup_path = f"{self.config_path}.backup_{timestamp}"
        shutil.copy2(self.config_path, backup_path)
        # ------------------------------------

        # Read current config
        with open(self.config_path, "r") as f:
            content = f.read()

        # Check if share already exists (by #Begin marker)
        begin_marker = f"{share_name}"
        if begin_marker in content:
            return fail("Share '{share_name}' already exists. Skipping.")

        # Append the new block at the end
        with open(self.config_path, "a") as f:
            f.write("\n" + share_block)

        print("Remember to restart Samba: sudo systemctl restart smbd nmbd")
        return ok({"info": f"[SUCCESS] Share {share_name} added to {self.config_path} with markers."})

    def remove_samba_share_block(self, share_name):
        """
        Returns:
            True  -> if block was found and removed
            False -> if block not found
        """
        if os.geteuid() != 0:
            raise PermissionError("This function must be run as root (sudo).")

        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        # ایجاد backup با تاریخ و زمان
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = f"{self.config_path}.backup_{timestamp}"
        shutil.copy2(self.config_path, backup_path)
        print(f"[INFO] Backup saved as: {backup_path}")

        begin_marker = f"#Begin: {share_name}"
        end_marker_prefix = f"#End: {share_name}"

        with open(self.config_path, "r") as f:
            lines = f.readlines()

        new_lines = []
        skip = False
        block_found = False

        for line in lines:
            if line.strip() == begin_marker:
                skip = True
                block_found = True
                continue  # خط #Begin را هم ننویس
            elif skip and line.startswith(end_marker_prefix):
                skip = False
                continue  # خط #End را هم ننویس
            elif not skip:
                new_lines.append(line)

        # اگر بلوک پیدا نشد
        if not block_found:
            return fail(f"[INFO] Share block '{share_name}' not found in {self.config_path}.")

        # نوشتن فایل جدید
        with open(self.config_path, "w") as f:
            f.writelines(new_lines)

        print(f"[SUCCESS] Share block '{share_name}' removed from {self.config_path}.")

        return ok({"info": f"[SUCCESS] Share {share_name} Remove from {self.config_path} with markers."})

    def list_shares(self) -> Dict[str, Any]:
        """
        Parse smb.conf and return all shares with their configurations.
        Returns a DRF-ready response dict using `ok()` or `fail()`.
        """
        if not os.path.exists(self.config_path):
            return fail(f"Samba config file not found: {self.config_path}", "file_not_found")

        try:
            config = configparser.ConfigParser(
                strict=False,
                interpolation=None,
                comment_prefixes=('#', ';'),
                inline_comment_prefixes=('#', ';')
            )
            # Preserve case (important for Samba keys like 'valid users')
            config.optionxform = str
            config.read(self.config_path)

            shares = {}
            for section in config.sections():
                # Skip global section (usually named 'global')
                if section.lower() == 'global':
                    continue
                # Convert section to dict
                shares[section] = dict(config[section])

            return ok(shares, detail=f"Found {len(shares)} share(s) in {self.config_path}")

        except Exception as e:
            return fail(f"Failed to parse smb.conf: {str(e)}", "parse_error", extra=str(e))

    def create_samba_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        Create a Samba user and set password non-interactively.
        Equivalent to: echo -e "pass\npass" | smbpasswd -a -s username
        Does NOT enable the user (you must call enable_samba_user separately).
        """
        if os.geteuid() != 0:
            return fail("This function must be run as root (sudo)", extra="نیاز به دسترسی روت دارد")

        if not username or not isinstance(username, str):
            return fail("Username must be a non-empty string.")

        if not password or not isinstance(password, str):
            return fail("Password must be a non-empty string.")

        if not username.replace("_", "").replace("-", "").replace(".", "").isalnum():
            return fail("Invalid username: only letters, digits, ., -, _ allowed.")

        try:
            passwd_input = f"{password}\n{password}\n"
            result = subprocess.run(
                ["smbpasswd", "-a", "-s", username],
                input=passwd_input,
                text=True,
                capture_output=True,
                timeout=10
            )

            if result.returncode == 0:
                return ok({"username": username}, detail="Samba user created successfully (password set).")
            else:
                stderr = result.stderr.strip()
                if "user exists" in stderr.lower():
                    return fail(f"Samba user '{username}' already exists.", code="user_exists", extra=stderr)
                else:
                    return fail(f"Failed to create Samba user: {stderr}", code="smbpasswd_error", extra=stderr)

        except subprocess.TimeoutExpired:
            return fail("smbpasswd command timed out.", code="timeout")
        except FileNotFoundError:
            return fail("smbpasswd command not found. Is Samba installed?", code="command_missing")
        except Exception as e:
            return fail(f"Exception during Samba user creation: {str(e)}", code="exception", extra=str(e))

    def enable_samba_user(self, username: str) -> Dict[str, Any]:
        """
        Enable an existing Samba user.
        Equivalent to: smbpasswd -e username
        """
        if os.geteuid() != 0:
            return fail("This function must be run as root (sudo)", extra="نیاز به دسترسی روت دارد")

        if not username or not isinstance(username, str):
            return fail("Username must be a non-empty string.")

        try:
            result = subprocess.run(
                ["smbpasswd", "-e", username],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                return ok(
                    {"username": username},
                    detail="Samba user enabled successfully."
                )
            else:
                stderr = result.stderr.strip()
                if "not found" in stderr.lower() or "does not exist" in stderr.lower():
                    return fail(f"Samba user '{username}' does not exist.", code="user_not_found", extra=stderr)
                else:
                    return fail(
                        f"Failed to enable Samba user: {stderr}",
                        code="enable_error",
                        extra=stderr
                    )

        except subprocess.TimeoutExpired:
            return fail("smbpasswd enable command timed out.", code="timeout")
        except FileNotFoundError:
            return fail("smbpasswd command not found. Is Samba installed?", code="command_missing")
        except Exception as e:
            return fail(f"Exception during Samba user enable: {str(e)}", code="exception", extra=str(e))
