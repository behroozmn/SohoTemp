# soho_core_api/pylibs/__init__.py

from __future__ import annotations
from typing import Any, Dict, Optional, Union, List

from http import HTTPStatus
from rest_framework.response import Response
from django.utils import timezone
from django.conf import settings
from typing import Any, Type, Union
from rest_framework.request import Request
import subprocess
import logging
import json
from drf_spectacular.utils import OpenApiParameter

logger = logging.getLogger(__name__)

from typing import List, Optional, Tuple

# Models
from soho_core_api.models import StandardResponseModel, StandardErrorResponseModel

QuerySaveToDB = [OpenApiParameter(name="save_to_db", type=bool, required=False, enum=["true", "false"], default="false", location="query", description="در صورت True، داده‌ها در دیتابیس ذخیره می‌شوند")]
BodyParameterSaveToDB = {"type": "object",
                         "properties": {"save_to_db": {"type": "boolean",
                                                       "enum": [True, False],  # ← برای drop-down در Swagger
                                                       "default": False,
                                                       "description": "در صورت true، داده‌ها در دیتابیس ذخیره می‌شوند"}}}


class CLICommandError(Exception):
    """استثنا اختصاصی برای خطا در اجرای دستورات خط فرمان .این کلاس تمام اطلاعات مفید خطا را نگه می‌دارد."""

    def __init__(self, command: List[str], returncode: int, stderr: str, stdout: str = "", timeout: bool = False, original_exception: Optional[Exception] = None):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = stdout
        self.timeout = timeout
        self.original_exception = original_exception

        # ساخت پیام خطا به فارسی
        cmd_str = " ".join(command[:4]) + (" ..." if len(command) > 4 else "")
        if timeout:
            message = f"دستور با timeout شکست خورد: {cmd_str}"
        elif returncode != 0:
            message = f"دستور با کد خروجی {returncode} شکست خورد: {stderr.strip() or 'خطای نامشخص'}"
        else:
            message = f"خطای غیرمنتظره در اجرای دستور: {str(original_exception)}"

        super().__init__(message)


class StandardResponse(Response):
    """Standard success response with consistent envelope structure."""

    def __init__(self, data: Any = None, message: str = "", details: Optional[Dict[str, Any]] = None, status: int = 200, request_data: Optional[Dict[str, Any]] = None, save_to_db: bool = False, **kwargs: Any, ) -> None:
        meta: Dict[str, Union[str, int]] = {
            "timestamp": timezone.now().isoformat().replace("+00:00", "Z"),
            "response_status_code": status,
            "response_status_text": _get_status_text(status),
        }

        sanitized_request_data = request_data or {} if settings.DEBUG or request_data is not None else {}

        response_data: Dict[str, Any] = {
            "ok": True,
            "error": None,
            "message": message,
            "data": data,
            "details": details or {},
            "meta": meta,
            "request_data": sanitized_request_data,
        }

        super().__init__(response_data, status=status, **kwargs)

        if save_to_db:
            StandardResponseModel.objects.create(
                message=message,
                data=data if data is not None else {},
                details=details or {},
                meta=meta,
                request_data=sanitized_request_data,
            )


class StandardErrorResponse(Response):

    def __init__(self, error_code: str, error_message: str, exception: Optional[Exception] = None, exception_details: Optional[Any] = None, status: int = 500, request_data: Optional[Dict[str, Any]] = None, save_to_db: bool = False, **kwargs: Any, ) -> None:
        meta = {
            "timestamp": timezone.now().isoformat().replace("+00:00", "Z"),
            "response_status_code": status,
            "response_status_text": _get_status_text(status),
        }

        error_obj = {
            "code": error_code,
            "message": error_message,
            "extra": {},
        }

        # اگر exception داده شده باشد
        if exception is not None:
            error_obj["extra"]["exception_class"] = exception.__class__.__name__

            # هوشمند: اگر exception از نوع CLICommandError باشد

            if isinstance(exception, CLICommandError):
                # استخراج جزئیات CLI به صورت خودکار
                cli_details = {
                    "command": exception.command,
                    "returncode": exception.returncode,
                    "stderr": exception.stderr,
                    "stdout": exception.stdout,
                    "timeout": exception.timeout,
                }
                final_details = cli_details
            else:
                # برای سایر خطاها: فقط پیام و نوع
                final_details = {
                    "message": str(exception),
                }
        else:
            # اگر exception داده نشده باشد، از exception_details استفاده کن (اگر وجود داشت)
            final_details = exception_details if exception_details is not None else {}

        # مدیریت نمایش در debug vs production
        if settings.DEBUG:
            error_obj["extra"]["exception_details"] = final_details
        else:
            # فقط در لاگ ذخیره کن
            try:
                log_str = json.dumps(final_details, ensure_ascii=False, default=str)
            except Exception:
                log_str = str(final_details)

            logger.error(
                "StandardErrorResponse: [%s] %s | Exception: %s | Details: %s",
                error_code,
                error_message,
                exception.__class__.__name__ if exception else "None",
                log_str,
            )
            error_obj["extra"]["exception_details"] = "Internal error details hidden."

        sanitized_request_data = request_data or {} if settings.DEBUG or request_data is not None else {}

        response_data = {
            "ok": False,
            "error": error_obj,
            "data": None,
            "details": {},
            "meta": meta,
            "request_data": sanitized_request_data,
        }

        super().__init__(response_data, status=status, **kwargs)

        if save_to_db:
            StandardErrorResponseModel.objects.create(
                error_code=error_code,
                error_message=error_message,
                error_extra=error_obj["extra"],
                meta=meta,
                request_data=sanitized_request_data,
            )


def _get_status_text(status_code: int) -> str:
    """
    Return the standard HTTP status text for a given status code.

    If the code is not standard, returns 'Unknown'.
    """
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "Unknown"


def get_request_param(request: Union[Request, dict], param_name: str, return_type: Type = str, default: Any = None) -> Any:
    """
    استخراج یک پارامتر از درخواست HTTP (در هر متدی: GET, POST, PUT, PATCH, DELETE و غیره)و تبدیل آن به نوع مشخص‌شده.

    این تابع به‌صورت هوشمند منبع پارامتر را تشخیص می‌دهد:
    - برای درخواست‌های GET: فقط از query_params
    - برای سایر متد‌ها: اول از body (request.data) و سپس از query_params

    پشتیبانی از انواع بازگشتی:
    - `str`: بدون تغییر (رشته تمیزشده)
    - `int`: تبدیل عددی (در صورت معتبر)
    - `float`: تبدیل اعشاری (در صورت معتبر)
    - `bool`: فقط در صورتی True است که مقدار دقیقاً 'true' باشد (حروف کوچک/بزرگ مهم نیست)

    اگر پارامتر وجود نداشته باشد یا تبدیل امکان‌پذیر نباشد، مقدار `default` بازگردانده می‌شود.

    Args:
        request (Request | dict): شیء درخواست Django REST یا یک دیکشنری (برای سازگاری).
        param_name (str): نام پارامتر مورد نظر (مثلاً "save_to_db", "disk_name", "count").
        return_type (Type): نوع داده‌ی خروجی. یکی از: str, int, float, bool.
        default (Any): مقدار پیش‌فرض در صورت عدم وجود یا خطا.

    Returns:
        Any: مقدار تبدیل‌شده یا مقدار پیش‌فرض.

    Examples:
        # GET /api/disk/?save_to_db=true
        save_flag = get_request_param(request, "save_to_db", bool, False)  # → True

        # POST {"count": "5"}
        count = get_request_param(request, "count", int, 1)  # → 5

        # GET /api/disk/?name=sda1
        name = get_request_param(request, "name", str, "default")  # → "sda1"
    """
    # مرحله ۱: خواندن مقدار خام
    raw_value = None
    try:
        if hasattr(request, "method"):
            method = request.method.upper()
            if method == "GET":
                raw_value = request.query_params.get(param_name, None)
            else:
                raw_value = request.data.get(param_name, None)
                if raw_value is None:
                    raw_value = request.query_params.get(param_name, None)
        elif isinstance(request, dict):
            raw_value = request.get(param_name, None)
        else:
            raw_value = None
    except Exception as e:
        logger.warning(f"Error accessing param '{param_name}' from request: {e}")
        return default

    if raw_value is None or raw_value == "":
        return default

    try:
        if return_type == bool:
            if isinstance(raw_value, bool): return raw_value
            if isinstance(raw_value, str): return raw_value.strip().lower() == "true"
            return bool(raw_value)

        elif return_type == int:
            if isinstance(raw_value, int): return raw_value
            if isinstance(raw_value, str): return int(raw_value.strip())
            raise ValueError("Cannot convert to int")

        elif return_type == float:
            if isinstance(raw_value, float): return raw_value
            if isinstance(raw_value, (int, str)): return float(raw_value)
            raise ValueError("Cannot convert to float")

        elif return_type == str:
            if isinstance(raw_value, str): return raw_value.strip()
            return str(raw_value)

        else:
            return raw_value

    except (ValueError, TypeError) as e:
        logger.warning(f"Type conversion failed for param '{param_name}' ({raw_value}) to {return_type}: {e}")
        return default


def run_cli_command(command: List[str], *, timeout: int = 60, check: bool = True, capture_output: bool = True, use_sudo: bool = False, log_on_error: bool = True, log_on_success: bool = False, input: Optional[str] = None) -> Tuple[str, str]:
    """اجرای یک دستور خط فرمان (CLI) با مدیریت جامع خطا.

    Args:
        command (List[str]): لیست آرگومان‌های دستور (مثال: ["zpool", "list"])
        timeout (int): مهلت اجرا به ثانیه (پیش‌فرض: 60)
        check (bool): اگر True باشد و کد خروجی != 0 باشد، خطا raise می‌شود (پیش‌فرض: True)
        capture_output (bool): آیا stdout و stderr ذخیره شود؟ (پیش‌فرض: True)
        use_sudo (bool): آیا دستور با sudo اجرا شود؟ (پیش‌فرض: False)
        log_on_error (bool): آیا خطا لاگ شود؟ (پیش‌فرض: True)
        log_on_success (bool): آیا موفقیت لاگ شود؟ (پیش‌فرض: False)
        input (Optional[str]): رشته ورودی که به stdin دستور فرستاده می‌شود (مثلاً برای رمز عبور)

    Returns:
        Tuple[str, str]: (stdout, stderr)

    Raises:
        CLICommandError: در صورت هرگونه خطا در اجرا
    """
    if use_sudo:
        full_cmd = ["/usr/bin/sudo"] + command
    else:
        full_cmd = command

    cmd_str = " ".join(full_cmd[:4]) + (" ..." if len(full_cmd) > 4 else "")
    if log_on_success:
        logger.debug(f"اجرای دستور: {cmd_str}")
    print(full_cmd)
    try:
        # اگر input داده شده باشد، stdin باید باز باشد
        stdin = subprocess.PIPE if input is not None else None

        result = subprocess.run(full_cmd, input=input, stdin=stdin, capture_output=capture_output, text=True, timeout=timeout, check=check, )
        stdout = result.stdout.strip() if result.stdout else ""
        stderr = result.stderr.strip() if result.stderr else ""

        if log_on_success and (stdout or stderr):
            logger.debug(f"دستور موفق: {cmd_str} | stdout: {stdout[:100]}...")

        return stdout, stderr

    except subprocess.TimeoutExpired as e:
        stderr = e.stderr.strip() if e.stderr else ""
        stdout = e.stdout.strip() if e.stdout else ""
        error = CLICommandError(command=full_cmd, returncode=-1, stderr=stderr, stdout=stdout, timeout=True, original_exception=e)
        if log_on_error:
            logger.error(f"دستور با timeout شکست خورد: {cmd_str} | stderr: {stderr}")
        raise error

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else str(e)
        stdout = e.stdout.strip() if e.stdout else ""
        error = CLICommandError(command=full_cmd, returncode=e.returncode, stderr=stderr, stdout=stdout, timeout=False, original_exception=e)
        if log_on_error:
            logger.error(f"دستور شکست خورد (کد {e.returncode}): {cmd_str} | stderr: {stderr}")
        raise error

    except (OSError, ValueError, FileNotFoundError) as e:
        error = CLICommandError(command=full_cmd, returncode=-1, stderr=str(e), stdout="", timeout=False, original_exception=e)
        if log_on_error:
            logger.error(f"خطای سیستمی در اجرای دستور: {cmd_str} | خطا: {e}")
        raise error

    except Exception as e:
        error = CLICommandError(command=full_cmd, returncode=-1, stderr=str(e), stdout="", timeout=False, original_exception=e)
        if log_on_error:
            logger.error(f"خطای غیرمنتظره در اجرای دستور: {cmd_str} | خطا: {e}")
        raise error


def build_standard_error_response(exc: Exception, error_code: str, error_message: str, request_data: Dict[str, Any], save_to_db: bool = False, default_status: int = 500) -> Response:
    """ساخت هوشمند StandardErrorResponse بر اساس نوع استثنا.تمام جزئیات مربوط به هر نوع خطا استخراج و در exception_details قرار می‌گیرد."""
    status = default_status
    exception_details = {}

    # --- 1. CLICommandError (خطاهای دستور خط فرمان ZFS) ---
    if isinstance(exc, CLICommandError):
        status = 400 if exc.returncode == 1 else 500
        exception_details = {
            "command": exc.command,
            "returncode": exc.returncode,
            "stderr": exc.stderr,
            "stdout": exc.stdout,
            "timeout": exc.timeout,
        }

    # --- 2. ValueError, TypeError (خطاهای اعتبارسنجی و منطقی) ---
    elif isinstance(exc, (ValueError, TypeError)):
        status = 400
        exception_details = {"message": str(exc), }

    # --- 3. FileNotFoundError, OSError, IOError (خطاهای سیستم فایل و دسترسی) ---
    elif isinstance(exc, (FileNotFoundError, OSError)):
        status = 400 if isinstance(exc, FileNotFoundError) else 500
        details = {"message": str(exc)}
        if hasattr(exc, 'filename') and exc.filename:
            details["filename"] = exc.filename
        if hasattr(exc, 'errno') and exc.errno:
            details["errno"] = exc.errno
        exception_details = details

    # --- 4. ImportError (خطاهای ماژول/واردات) ---
    elif isinstance(exc, ImportError):
        status = 500
        exception_details = {
            "message": str(exc),
            "name": getattr(exc, 'name', None),
            "path": getattr(exc, 'path', None),
        }

    # --- 5. RuntimeError (خطاهای زمان اجرا) ---
    elif isinstance(exc, RuntimeError):
        status = 400 if "invalid" in str(exc).lower() or "not found" in str(exc).lower() else 500
        exception_details = {"message": str(exc), }

    # --- 6. سایر استثناها (خطاهای غیرمنتظره) ---
    else:
        status = 500
        exception_details = {
            "message": str(exc),
            "class": exc.__class__.__name__,
        }

    # ارسال به StandardErrorResponse
    return StandardErrorResponse(
        error_code=error_code,
        error_message=error_message,
        exception=exc,
        exception_details=exception_details,
        status=status,
        request_data=request_data,
        save_to_db=save_to_db
    )
