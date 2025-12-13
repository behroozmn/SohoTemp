# soho_core_api/views/view_cpu.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from drf_spectacular.utils import (extend_schema, OpenApiParameter, OpenApiExample, )
from rest_framework import viewsets
from rest_framework.request import Request
from rest_framework.response import Response

# Core utilities
from pylibs import (get_request_param, build_standard_error_response, StandardResponse, StandardErrorResponse, )
from pylibs.mixins import CLICommandError, CPUValidationMixin
from pylibs.cpu import CPUManager

# ========== لیست فیلدهای مجاز برای property ==========
CPU_PROPERTY_CHOICES = ["all", "vendor_id", "model_name", "architecture", "cpu_op_mode", "byte_order",
                        "cpu_count_physical", "cpu_count_logical", "threads_per_core", "cores_per_socket",
                        "sockets", "flags", "hypervisor", "virtualization",
                        "usage_percent_total", "frequency_total", "per_core_usage", "per_core_frequency",
                        ]

# ========== OpenAPI Parameters ==========
ParamProperty = OpenApiParameter(name="property", type=str, required=False, enum=CPU_PROPERTY_CHOICES,
                                 description='نام یک فیلد خاص یا "all" برای دریافت تمام فیلدها.',
                                 examples=[OpenApiExample("دریافت همه فیلدها", value="all"),
                                           OpenApiExample("نام مدل", value="model_name"),
                                           OpenApiExample("شناسه سازنده", value="vendor_id"),
                                           OpenApiExample("معماری", value="architecture"),
                                           OpenApiExample("تعداد هسته‌های فیزیکی", value="cpu_count_physical"),
                                           OpenApiExample("تعداد هسته‌های منطقی", value="cpu_count_logical"),
                                           OpenApiExample("استفاده کلی CPU (%)", value="usage_percent_total"),
                                           OpenApiExample("فرکانس کل CPU (MHz)", value="frequency_total"),
                                           OpenApiExample("استفاده هر هسته (%)", value="per_core_usage"),
                                           OpenApiExample("فرکانس هر هسته (MHz)", value="per_core_frequency"), ], )


# ========== ViewSet ==========
class CPUInfoViewSet(viewsets.ViewSet, CPUValidationMixin):
    """
    دریافت اطلاعات جامع CPU از سه منبع:
    - `lscpu`: اطلاعات سخت‌افزاری ثابت
    - `/proc/cpuinfo`: اطلاعات تکمیلی هر هسته
    - `psutil`: آمار پویا (درصد استفاده، فرکانس لحظه‌ای)

    این endpoint فقط اطلاعات کلی CPU را برمی‌گرداند و امکان فیلتر کردن فیلدها را فراهم می‌کند.
    """

    @extend_schema(parameters=[ParamProperty])
    def list(self, request: Request) -> Response:
        prop_key = get_request_param(request=request, param_name="property", return_type=str, default=None)
        if prop_key:
            prop_key = prop_key.strip().lower()
        request_data = dict(request.query_params)

        try:
            fields = None
            if prop_key and prop_key != "all":
                if prop_key not in CPU_PROPERTY_CHOICES:
                    raise ValueError(f"مقدار نامعتبر برای property. مقادیر مجاز: {', '.join(CPU_PROPERTY_CHOICES)}")
                fields = [prop_key]

            # اعتبارسنجی فیلدها (اگر fields مشخص شده باشد)
            if fields is not None:
                self.validate_fields(fields)

            manager = CPUManager()
            data = manager.gather_info(fields=fields)  # بدون core_id

            return StandardResponse(data=data, request_data=request_data, save_to_db=False,
                                    message="اطلاعات CPU با موفقیت دریافت شد.", )

        except ValueError as ve:
            return StandardErrorResponse(status=400, request_data=request_data, save_to_db=False,
                                         error_code="invalid_input",
                                         error_message=str(ve), )

        except CLICommandError as ce:
            return build_standard_error_response(exc=ce, request_data=request_data, save_to_db=False,
                                                 error_code="cli_command_failed",
                                                 error_message="خطا در اجرای دستور سیستمی (مثل lscpu).", )

        except Exception as exc:
            return build_standard_error_response(exc=exc, request_data=request_data, save_to_db=False,
                                                 error_code="cpu_info_fetch_failed",
                                                 error_message="خطا در دریافت اطلاعات CPU.", )
