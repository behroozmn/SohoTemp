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


class FileManager:
    def __init__(self, config_path: str = "/etc/samba/smb.conf") -> None:
        self.config_path = config_path
    pass
