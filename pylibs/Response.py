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
from rest_framework.response import Response
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class StandardResponse(Response):
    """
    Standardized success response wrapper.

    Use this class to return consistent successful responses from your DRF views.

    Args:
        data (Any, optional): The main payload (e.g., list, dict, string). Defaults to None.
        message (str, optional): A human-readable success message. Defaults to "".
        details (Optional[Dict[str, Any]], optional): Additional metadata about the response.
            Defaults to None.
        status (int, optional): HTTP status code. Defaults to 200.
        request_data (Optional[Dict[str, Any]], optional): Original request data for debugging.
            Defaults to None.
        **kwargs: Additional keyword arguments passed to DRF's Response.

    Example:
        return StandardResponse(
            data=["john", "mary"],
            message="Users retrieved successfully",
            details={"count": 2},
            request_data=dict(request.query_params)
        )
    """

    def __init__(self, data: Any = None, message: str = "", details: Optional[Dict[str, Any]] = None, status: int = 200, request_data: Optional[Dict[str, Any]] = None, **kwargs: Any, ) -> None:
        meta: Dict[str, Union[str, int]] = {
            "timestamp": timezone.now().isoformat().replace("+00:00", "Z"),
            "response_status_code": status,
        }

        # Sanitize request_data: only include in DEBUG mode or if explicitly provided
        sanitized_request_data: Dict[str, Any] = (
            request_data or {} if settings.DEBUG or request_data is not None else {}
        )

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


class StandardErrorResponse(Response):
    """
    Standardized error response wrapper.

    Use this to return structured error responses manually from views.
    For automatic handling of uncaught exceptions (like 404, 500), pair this
    with a custom exception handler (see DRF's EXCEPTION_HANDLER setting).

    Args:
        error_code (str): A machine-readable error identifier (e.g., "invalid_input").
        error_message (str): A human-readable error description.
        exception (Optional[Exception], optional): The original exception object.
            Used to extract type name. Defaults to None.
        exception_details (Optional[Union[str, Exception]], optional): Detailed error info.
            Only shown in DEBUG mode for security. Defaults to None.
        status (int, optional): HTTP status code (e.g., 400, 403, 500). Defaults to 500.
        request_data (Optional[Dict[str, Any]], optional): Original request data for debugging.
            Only included in DEBUG mode. Defaults to None.
        **kwargs: Additional keyword arguments passed to DRF's Response.

    Example:
        return StandardErrorResponse(
            error_code="file_read_error",
            error_message="Could not read user list",
            exception=e,
            exception_details=e,
            status=500,
            request_data=dict(request.query_params)
        )
    """

    def __init__(self, error_code: str, error_message: str, exception: Optional[Exception] = None, exception_details: Optional[Union[str, Exception]] = None, status: int = 500, request_data: Optional[Dict[str, Any]] = None, **kwargs: Any, ) -> None:
        meta: Dict[str, Union[str, int]] = {
            "timestamp": timezone.now().isoformat().replace("+00:00", "Z"),
            "response_status_code": status,
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
                # Log full error in production but hide from client
                logger.error(
                    "StandardErrorResponse: [%s] %s | Exception: %s | Details: %s",
                    error_code,
                    error_message,
                    exception.__class__.__name__ if exception else "None",
                    details_str,
                )
                error_obj["extra"]["exception_details"] = "Internal error details hidden."

        # Sanitize request_data
        sanitized_request_data: Dict[str, Any] = (
            request_data or {} if settings.DEBUG or request_data is not None else {}
        )

        response_data: Dict[str, Any] = {
            "ok": False,
            "error": error_obj,
            "data": None,
            "details": {},
            "meta": meta,
            "request_data": sanitized_request_data,
        }

        super().__init__(response_data, status=status, **kwargs)
