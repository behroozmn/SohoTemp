import psutil  # برای خواندن آمار سیستم
from typing import Dict, Any, Optional, List  # تایپ‌هینت برای خوانایی بهتر
from django.http import JsonResponse  # برای ساخت پاسخ جی‌سان




class CPU:
    def __init__(self):
        try:
            self._cpu_percent = psutil.cpu_percent()
            self._cpu_times = psutil.cpu_times()._asdict()
            self._cpu_freq = self._get_cpu_frequency()
            self._cpu_cores = self._get_cpu_cores()
        except Exception as e:
            raise RuntimeError(f"Error in getting CPU data: {e}") from e

    def _get_cpu_frequency(self) -> Dict[str, Optional[float]]:
        try:
            return psutil.cpu_freq()._asdict()
        except Exception as e:
            return {"error": str(e)}

    def _get_cpu_cores(self) -> Dict[str, Optional[int]]:
        return {
            "physical": psutil.cpu_count(logical=False),
            "logical": psutil.cpu_count(logical=True)
        }

    def get(self, *fields: str) -> Dict[str, Any]:
        """بازگرداندن فقط فیلدهای تعیین شده"""
        full_data = self.to_dict()
        result = {}

        for field in fields:
            if field in full_data:
                result[field] = full_data[field]
            else:
                result[field] = None

        return result

    def to_dict(self) -> Dict[str, Any]:
        """بازگرداندن تمام اطلاعات سی‌پی‌یو به صورت دیکشنری"""
        return {
            "cpu_percent": self._cpu_percent,
            "cpu_times_second": self._cpu_times,
            "cpu_frequency": self._cpu_freq,
            "cpu_cores": self._cpu_cores
        }

    def to_json_response(self, selected_fields: Optional[List[str]] = None) -> JsonResponse:
        """برگرداندن اطلاعات به صورت JsonResponse (با امکان انتخاب فیلدها)"""
        if selected_fields:
            data = self.get(*selected_fields)
        else:
            data = self.to_dict()

        return JsonResponse(data, safe=False)  # برگرداندن خروجی به صورت جی‌سان
