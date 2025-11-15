"""
Standardized API response wrappers for consistent JSON structure.

This module provides two main response classes:
- `StandardResponse`: for successful API responses
- `StandardErrorResponse`: for error responses (manual or handled)

Both classes ensure a uniform envelope structure across all endpoints,
making frontend integration predictable and debugging easier.
"""

from __future__ import annotations
from typing import Any, Dict, Optional, Union
from http import HTTPStatus
from rest_framework.response import Response
from django.utils import timezone
from django.conf import settings
import logging
from typing import Any, Type, Union
from rest_framework.request import Request

logger = logging.getLogger(__name__)

# Models
from soho_core_api.models import StandardResponseModel
from soho_core_api.models import StandardErrorResponseModel


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
                # اول از body (POST/PUT/PATCH/DELETE)
                raw_value = request.data.get(param_name, None)
                # اگر در body نبود، از query_params بگیر (پشتیبانی از ?param=... در POST)
                if raw_value is None:
                    raw_value = request.query_params.get(param_name, None)
        elif isinstance(request, dict):
            raw_value = request.get(param_name, None)
        else:
            raw_value = None
    except Exception as e:
        logger.warning(f"Error accessing param '{param_name}' from request: {e}")
        return default

    # اگر مقداری وجود نداشت
    if raw_value is None or raw_value == "":
        return default

    # مرحله ۲: تبدیل به نوع مورد نظر
    try:
        if return_type == bool:
            if isinstance(raw_value, bool):
                return raw_value
            if isinstance(raw_value, str):
                return raw_value.strip().lower() == "true"
            return bool(raw_value)

        elif return_type == int:
            if isinstance(raw_value, int):
                return raw_value
            if isinstance(raw_value, str):
                return int(raw_value.strip())
            raise ValueError("Cannot convert to int")

        elif return_type == float:
            if isinstance(raw_value, float):
                return raw_value
            if isinstance(raw_value, (int, str)):
                return float(raw_value)
            raise ValueError("Cannot convert to float")

        elif return_type == str:
            if isinstance(raw_value, str):
                return raw_value.strip()
            return str(raw_value)

        else:
            # اگر نوع پشتیبانی‌نشده باشد، همان مقدار خام را برگردان
            return raw_value

    except (ValueError, TypeError) as e:
        logger.warning(f"Type conversion failed for param '{param_name}' ({raw_value}) to {return_type}: {e}")
        return default


class StandardResponse(Response):
    """Standard success response with consistent envelope structure."""

    def __init__(self,
                 data: Any = None,
                 message: str = "",
                 details: Optional[Dict[str, Any]] = None,
                 status: int = 200,
                 request_data: Optional[Dict[str, Any]] = None,
                 save_to_db: bool = False,
                 **kwargs: Any,
                 ) -> None:
        meta: Dict[str, Union[str, int]] = {
            "timestamp": timezone.now().isoformat().replace("+00:00", "Z"),
            "response_status_code": status,
            "response_status_text": _get_status_text(status),
        }

        sanitized_request_data: Dict[str, Any] = (request_data or {} if settings.DEBUG or request_data is not None else {})

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
    """Standard error response with structured error details."""

    def __init__(self,
                 error_code: str,
                 error_message: str,
                 exception: Optional[Exception] = None,
                 exception_details: Optional[Union[str, Exception]] = None,
                 status: int = 500,
                 request_data: Optional[Dict[str, Any]] = None,
                 save_to_db: bool = False,
                 **kwargs: Any,
                 ) -> None:
        meta: Dict[str, Union[str, int]] = {
            "timestamp": timezone.now().isoformat().replace("+00:00", "Z"),
            "response_status_code": status,
            "response_status_text": _get_status_text(status),
        }

        # Build error object
        error_obj: Dict[str, Any] = {
            "code": error_code,
            "message": error_message,
            "extra": {},
        }

        # Add exception class name if available
        if exception is not None:
            error_obj["extra"]["exception"] = exception.__class__.__name__

        # Handle exception details with security in mind
        if exception_details is not None:
            details_str = str(exception_details)
            if settings.DEBUG:
                error_obj["extra"]["exception_details"] = details_str
            else:
                logger.error(
                    "StandardErrorResponse: [%s] %s | Exception: %s | Details: %s",
                    error_code,
                    error_message,
                    exception.__class__.__name__ if exception else "None",
                    details_str,
                )
                error_obj["extra"]["exception_details"] = "Internal error details hidden."

        sanitized_request_data: Dict[str, Any] = (request_data or {} if settings.DEBUG or request_data is not None else {})

        response_data: Dict[str, Any] = {
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
