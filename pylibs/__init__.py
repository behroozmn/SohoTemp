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

logger = logging.getLogger(__name__)

# Models
from soho_core_api.models_collection.model_standard_response import StandardResponseModel
from soho_core_api.models_collection.model_standard_error_response import StandardErrorResponseModel



def _get_status_text(status_code: int) -> str:
    """
    Return the standard HTTP status text for a given status code.

    If the code is not standard, returns 'Unknown'.
    """
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "Unknown"


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