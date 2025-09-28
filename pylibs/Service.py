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

class ServiceManager:
    def __init__(self) -> None:
        pass

    def _run(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """اجرای دستور systemctl با خطاهای مناسب"""
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False  # ما خودمان وضعیت را بررسی می‌کنیم
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Command timed out")

    def list_services(self) -> Dict[str, Any]:
        """
        لیست تمام سرویس‌های systemd همراه با وضعیت و PID (اگر فعال باشد)
        """
        try:
            # دریافت لیست سرویس‌ها با جزئیات
            result = self._run([
                "systemctl", "list-units", "--type=service",
                "--all", "--no-pager", "--no-legend"
            ])

            if result.returncode != 0:
                return fail(f"Failed to list services: {result.stderr.strip()}")

            services = {}
            for line in result.stdout.strip().splitlines():
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) < 4:
                    continue

                unit = parts[0]
                if not unit.endswith(".service"):
                    continue

                load = parts[1]
                active = parts[2]
                sub = parts[3]

                # دریافت PID (اگر فعال باشد)
                pid = None
                if active == "active":
                    try:
                        pid_result = self._run(["systemctl", "show", unit, "--property=MainPID", "--value"])
                        if pid_result.returncode == 0:
                            pid_str = pid_result.stdout.strip()
                            if pid_str.isdigit():
                                pid = int(pid_str)
                    except Exception:
                        pid = None

                services[unit] = {
                    "unit": unit,
                    "load": load,
                    "active": active,
                    "sub": sub,
                    "pid": pid
                }

            return ok(services, details={"count": len(services)})

        except Exception as e:
            return fail(f"Exception while listing services: {str(e)}", extra={"exception": str(e)})

    def _control_service(self, action: str, service_name: str) -> Dict[str, Any]:
        """اجرای start/stop/restart برای یک سرویس"""
        if not service_name.endswith(".service"):
            service_name += ".service"

        try:
            result = self._run(["systemctl", action, service_name])
            if result.returncode == 0:
                return ok({"action": action, "service": service_name}, details="Success")
            else:
                return fail(
                    f"Failed to {action} {service_name}: {result.stderr.strip()}",
                    code=f"service_{action}_failed",
                    extra={"stdout": result.stdout, "stderr": result.stderr}
                )
        except Exception as e:
            return fail(f"Exception during {action}: {str(e)}", extra={"exception": str(e)})

    def start_service(self, service_name: str) -> Dict[str, Any]:
        return self._control_service("start", service_name)

    def stop_service(self, service_name: str) -> Dict[str, Any]:
        return self._control_service("stop", service_name)

    def restart_service(self, service_name: str) -> Dict[str, Any]:
        return self._control_service("restart", service_name)