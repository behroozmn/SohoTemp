#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import libzfs
from typing import Any, Dict, Optional
import subprocess


def ok(data: Any) -> Dict[str, Any]:
    """Return a success envelope (DRF-ready)."""
    return {"ok": True, "error": None, "data": data, "details": {}}


def fail(message: str, code: str = "samba_error", extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a failure envelope (DRF-ready)."""
    return {"ok": False, "error": {"code": code, "message": message, "extra": extra or {}}, "data": None, "details": {}}

import configparser
import os
import shutil

def add_samba_share(
    share_name,
    path,
    config_path="/etc/samba/smb.conf",
    create_mask="0777",
    directory_mask="0777",
    max_connections=0,
    read_only=False,
    available=True,
    guest_ok=False
):
    """
    Add a new Samba share to smb.conf safely.

    Args:
        share_name (str): Name of the share (e.g., "Dir1")
        path (str): Absolute path to the shared directory
        config_path (str): Path to smb.conf (default: /etc/samba/smb.conf)
        create_mask (str): File creation mask (default: "0777")
        directory_mask (str): Directory creation mask (default: "0777")
        max_connections (int): Max concurrent connections (0 = unlimited)
        read_only (bool): If True, share is read-only
        available (bool): If False, share is hidden
        guest_ok (bool): Allow guest access (no password)

    Raises:
        PermissionError: If not run as root
        ValueError: If path is not absolute or share name is invalid
    """
    # بررسی دسترسی root
    if os.geteuid() != 0:
        raise PermissionError("This function must be run as root (sudo).")

    # اعتبارسنجی ورودی‌ها
    if not os.path.isabs(path):
        raise ValueError("Path must be an absolute path (e.g., /home/user/Dir1).")
    if not share_name or not share_name.strip():
        raise ValueError("Share name cannot be empty.")
    share_name = share_name.strip()

    # ایجاد نسخه پشتیبان
    backup_path = config_path + ".backup"
    if not os.path.exists(backup_path):
        shutil.copy2(config_path, backup_path)

    # خواندن فایل smb.conf
    config = configparser.ConfigParser(strict=False, interpolation=None)
    config.optionxform = str  # حفظ حروف بزرگ/کوچک (مهم برای Samba)
    config.read(config_path)

    # بررسی تکراری بودن
    if share_name in config:
        print(f"[INFO] Share '{share_name}' already exists. Skipping.")
        return False

    # اضافه کردن بخش جدید
    config[share_name] = {
        "path": path,
        "create mask": create_mask,
        "directory mask": directory_mask,
        "max connections": str(max_connections),
        "read only": "Yes" if read_only else "No",
        "available": "Yes" if available else "No",
        "guest ok": "Yes" if guest_ok else "No"
    }

    # نوشتن مجدد فایل
    with open(config_path, "w") as f:
        config.write(f, space_around_delimiters=False)

    print(f"[SUCCESS] Share '{share_name}' added to {config_path}.")
    print("Remember to restart Samba: sudo systemctl restart smbd nmbd")
    return True