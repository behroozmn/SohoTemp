# soho_core_api/views_collection/view_hardware.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from rest_framework import viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from pylibs.network import NetworkManager
from pylibs.mixins import NetworkValidationMixin
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import action

# Core utilities
from pylibs import (
    get_request_param,
    build_standard_error_response,
    StandardResponse,
    StandardErrorResponse,
    QuerySaveToDB, BodyParameterSaveToDB,
)
from pylibs.mixins import CLICommandError, CPUValidationMixin, MemoryValidationMixin
from pylibs.cpu import CPUManager
from pylibs.memory import MemoryManager

# ========== CPU ==========
CPU_PROPERTY_CHOICES = [
    "all",
    # دریافت تمام فیلدهای اطلاعات CPU به‌صورت یکجا.

    "vendor_id",
    # شناسه سازنده CPU که توسط CPU در زمان بوت گزارش می‌شود. مقادیر رایج عبارتند از:
    # - "GenuineIntel": سی‌پی‌یو اینتل
    # - "AuthenticAMD": سی‌پی‌یو AMD
    # - "ARM Limited": در پردازنده‌های ARM
    # این فیلد به‌عنوان "CPUID Vendor String" شناخته می‌شود و برای تشخیص سازنده سخت‌افزاری ضروری است.

    "model_name",
    # نام کامل مدل سی‌پی‌یو همان‌طور که توسط سازنده ارائه شده است. مثال:
    # "Intel(R) Core(TM) i7-10700 CPU @ 2.90GHz"
    # این نام شامل نسل، سری، فرکانس پایه و نام تجاری است و برای شناسایی دقیق سخت‌افزار استفاده می‌شود.

    "architecture",
    # معماری دستورالعمل (Instruction Set Architecture - ISA) که سیستم‌عامل آن را اجرا می‌کند. مقادیر رایج:
    # - "x86_64": معماری 64 بیتی اینتل/AMD
    # - "aarch64": معماری 64 بیتی ARM
    # - "i686": معماری 32 بیتی x86 قدیمی
    # این فیلد نشان می‌دهد که سیستم‌عامل چه نوع برنامه‌هایی را می‌تواند اجرا کند.

    "cpu_op_mode",
    # حالت‌های عملیاتی (Operation Modes) که CPU از آن‌ها پشتیبانی می‌کند. مثال:
    # - "32-bit, 64-bit": پشتیبانی از هر دو حالت سازگاری
    # - "64-bit": فقط 64 بیتی
    # این فیلد به سیستم‌عامل کمک می‌کند تا متوجه شود چه حالت‌هایی قابل استفاده هستند.

    "byte_order",
    # ترتیب بایت‌ها (Endianness) در حافظه. دو حالت اصلی:
    # - "Little Endian": بایت کم‌ارزش‌تر در آدرس کم‌تر ذخیره می‌شود (معمولاً x86/x64)
    # - "Big Endian": بایت پر‌ارزش‌تر در آدرس کم‌تر ذخیره می‌شود (بعضی سرورهای قدیمی یا ARM ممکن است از این استفاده کنند)
    # این فیلد برای سازگاری باینری و شبکه بسیار مهم است.

    "cpu_count_physical",
    # تعداد هسته‌های فیزیکی واقعی روی تراشه(های) CPU. این شامل Hyper-Threading نمی‌شود.
    # مثال: CPU 8 هسته‌ای فیزیکی با Hyper-Threading → این فیلد = 8

    "cpu_count_logical",
    # تعداد هسته‌های منطقی که سیستم‌عامل می‌بیند (شامل Hyper-Threading). این همان تعداد CPU در دید سیستم‌عامل است.
    # مثال: CPU 8 هسته‌ای فیزیکی با 2 thread در هر هسته → این فیلد = 16

    "threads_per_core",
    # تعداد ریسمان‌های همزمان که هر هسته فیزیکی می‌تواند پردازش کند.
    # در CPUهای اینتل این معمولاً 2 است (Hyper-Threading)
    # در CPUهای AMD جدید (مثل Ryzen) نیز به‌صورت مشابه پیاده‌سازی شده است.

    "cores_per_socket",
    # تعداد هسته‌های فیزیکی در هر سوکت (Socket) CPU. در سرورهای چند-سوکت مهم است.

    "sockets",
    # تعداد سوکت‌های فیزیکی روی مادربورد که CPU در آن‌ها نصب شده است. معمولاً:
    # - دسکتاپ: 1
    # - سرورهای کوچک: 2
    # - سرورهای بزرگ: 4 یا بیشتر

    "flags",
    # لیستی از ویژگی‌ها و قابلیت‌های سخت‌افزاری که CPU از آن‌ها پشتیبانی می‌کند. هر فلگ نشان‌دهنده یک دستورالعمل یا ویژگی سخت‌افزاری است:
    # - fpu: واحد محاسباتی شناور (Floating Point Unit)
    # - vme: Virtual Mode Extension
    # - de: Debugging Extensions
    # - pse: Page Size Extension
    # - tsc: Time Stamp Counter
    # - msr: Model Specific Registers
    # - pae: Physical Address Extension (پشتیبانی از RAM بیش از 4GB در 32-bit)
    # - mce: Machine Check Exception
    # - cx8: CMPXCHG8B instruction
    # - apic: Advanced Programmable Interrupt Controller
    # - sep: SYSENTER/SYSEXIT instructions
    # - mtrr: Memory Type Range Registers
    # - pge: Page Global Enable
    # - mca: Machine Check Architecture
    # - cmov: Conditional Move instructions
    # - pat: Page Attribute Table
    # - pse36: 36-bit Page Size Extension
    # - clflush: CLFLUSH instruction
    # - dts: Debug Store
    # - acpi: ACPI via MSR
    # - mmx: MMX instructions
    # - fxsr: FXSAVE/FXRSTOR instructions
    # - sse: Streaming SIMD Extensions
    # - sse2, sse3, ssse3, sse4_1, sse4_2: نسخه‌های پیشرفته SSE
    # - avx, avx2: Advanced Vector Extensions
    # - aes: AES-NI instruction set
    # - vmx: Intel Virtualization Technology (VT-x)
    # - smx: Safer Mode Extensions (Intel TXT)
    # - ht: Hyper-Threading
    # - nx: NX bit (No-eXecute) — جلوگیری از اجرای کد در حافظه‌ی داده
    # - syscall: SYSCALL/SYSRET instructions
    # - rdtscp: RDTSCP instruction
    # - lm: Long Mode (64-bit)
    # این لیست بر اساس خروجی /proc/cpuinfo یا lscpu هر سیستم متفاوت است و نشان‌دهنده قابلیت‌های دقیق CPU است.

    "hypervisor",
    # آیا سیستم در حال اجرا در یک ماشین مجازی است؟
    # - True: سیستم در یک Hypervisor (مثل KVM, VMware, VirtualBox, Xen) اجرا می‌شود.
    # - False: سیستم روی سخت‌افزار فیزیکی (bare metal) اجرا می‌شود.
    # این فیلد از فلگ "hypervisor" در خروجی lscpu یا فیلد "Hypervisor" در /proc/cpuinfo استخراج می‌شود.

    "virtualization",
    # نوع فناوری مجازی‌سازی سخت‌افزاری که CPU از آن پشتیبانی می‌کند:
    # - "VT-x": فناوری مجازی‌سازی اینتل (Intel Virtualization Technology)
    # - "AMD-V": فناوری مجازی‌سازی AMD
    # - "none": CPU از مجازی‌سازی سخت‌افزاری پشتیبانی نمی‌کند.
    # این فیلد برای ایجاد ماشین‌های مجازی با کارایی بالا ضروری است.

    "usage_percent_total",
    # درصد کلی استفاده از CPU در کل سیستم، محاسبه‌شده از تمام هسته‌ها در یک بازه زمانی کوتاه (معمولاً 100ms).
    # مقداری بین 0.0 تا 100.0 با دقت دو رقم اعشار.
    # این مقدار توسط psutil.cpu_percent(interval=...) گزارش می‌شود.

    "frequency_total",
    # فرکانس لحظه‌ای CPU به‌صورت میانگین یا از هسته‌ی مرجع، به مگاهرتز (MHz).
    # این مقدار می‌تواند بر اساس خودکار متغیر باشد (Turbo Boost, Scaling).
    # از psutil.cpu_freq().current گرفته می‌شود.

    "per_core_usage",
    # لیستی از درصدهای استفاده هر هسته منطقی به‌صورت جداگانه.
    # تعداد عناصر = cpu_count_logical
    # مثال: [12.3, 5.7, 8.1, 22.4, ...]
    # این داده از psutil.cpu_percent(percpu=True) استخراج می‌شود.

    "per_core_frequency",
    # لیستی از فرکانس‌های لحظه‌ای هر هسته به مگاهرتز (MHz).
    # این داده از فیلد "cpu MHz" در /proc/cpuinfo هر هسته استخراج می‌شود.
    # اگر سیستم از این فیلد پشتیبانی نکند، مقدار فرکانس کلی برای همه هسته‌ها تکرار می‌شود.
]

ParamPropertyCPU = OpenApiParameter(name="property", type=str, required=False, enum=CPU_PROPERTY_CHOICES,
                                    description="انتخاب یک فیلد خاص از اطلاعات CPU یا ارسال 'all' برای دریافت همه فیلدها.",
                                    examples=[OpenApiExample("همه فیلدها", value="all", description="دریافت تمام فیلدهای اطلاعات CPU به‌صورت یکجا."),
                                              OpenApiExample("شناسه سازنده", value="vendor_id", description="شناسه سازنده CPU که توسط CPU در زمان بوت گزارش می‌شود.\nمقادیر رایج:\n- GenuineIntel (اینتل)\n- AuthenticAMD (AMD)"),
                                              OpenApiExample("نام کامل مدل «سی پی یو»", value="model_name", description="نام کامل مدل CPU همان‌طور که توسط سازنده ارائه شده است.\nمثال: Intel(R) Core(TM) i7-10700 CPU @ 2.90GHz"),
                                              OpenApiExample("معماری پردازنده", value="architecture", description="معماری دستورالعمل (ISA) که سیستم‌عامل آن را اجرا می‌کند.\nمثال: x86_64, aarch64"),
                                              OpenApiExample("حالت‌های عملیاتی پشتیبانی‌شده", value="cpu_op_mode", description="حالت‌های عملیاتی که CPU از آن‌ها پشتیبانی می‌کند.\nمثال: 32-bit, 64-bit"),
                                              OpenApiExample("ترتیب بایت‌ها در حافظه", value="byte_order", description="ترتیب بایت‌ها (Endianness) در حافظه.\nمعمولاً: Little Endian (در x86/x64)"),
                                              OpenApiExample("تعداد هسته‌های فیزیکی", value="cpu_count_physical", description="تعداد هسته‌های فیزیکی واقعی روی تراشه(های) CPU.\n(بدون Hyper-Threading)"),
                                              OpenApiExample("تعداد هسته‌های منطقی", value="cpu_count_logical", description="تعداد هسته‌های منطقی که سیستم‌عامل می‌بیند.\n(شامل Hyper-Threading)"),
                                              OpenApiExample("thread در هر هسته", value="threads_per_core", description="تعداد ریسمان‌های همزمان که هر هسته فیزیکی می‌تواند پردازش کند.\nمعمولاً: 2 در CPUهای مدرن"),
                                              OpenApiExample("هسته در هر سوکت", value="cores_per_socket", description="تعداد هسته‌های فیزیکی در هر سوکت (Socket) CPU."),
                                              OpenApiExample("تعداد سوکت‌های فیزیکی", value="sockets", description="تعداد سوکت‌های فیزیکی روی مادربورد که CPU در آن‌ها نصب شده است.\nمعمولاً: 1 در دسکتاپ"),
                                              OpenApiExample("لیست قابلیت‌های سخت‌افزاری «سی پی یو»", value="flags", description=("لیستی از ویژگی‌ها و قابلیت‌های سخت‌افزاری که CPU از آن‌ها پشتیبانی می‌کند.\n"
                                                                                                                                  "هر فلگ یک دستورالعمل یا قابلیت خاص را نشان می‌دهد:\n"
                                                                                                                                  "- fpu: واحد محاسبات شناور\n"
                                                                                                                                  "- vme: Virtual Mode Extension\n"
                                                                                                                                  "- de: Debugging Extensions\n"
                                                                                                                                  "- pse: Page Size Extension\n"
                                                                                                                                  "- tsc: Time Stamp Counter\n"
                                                                                                                                  "- msr: Model Specific Registers\n"
                                                                                                                                  "- pae: Physical Address Extension (RAM > 4GB در 32-bit)\n"
                                                                                                                                  "- mce: Machine Check Exception\n"
                                                                                                                                  "- cx8: CMPXCHG8B instruction\n"
                                                                                                                                  "- apic: Advanced Programmable Interrupt Controller\n"
                                                                                                                                  "- sep: SYSENTER/SYSEXIT instructions\n"
                                                                                                                                  "- mtrr: Memory Type Range Registers\n"
                                                                                                                                  "- pge: Page Global Enable\n"
                                                                                                                                  "- mca: Machine Check Architecture\n"
                                                                                                                                  "- cmov: Conditional Move instructions\n"
                                                                                                                                  "- pat: Page Attribute Table\n"
                                                                                                                                  "- pse36: 36-bit Page Size Extension\n"
                                                                                                                                  "- clflush: CLFLUSH instruction\n"
                                                                                                                                  "- dts: Debug Store\n"
                                                                                                                                  "- acpi: ACPI via MSR\n"
                                                                                                                                  "- mmx: MMX instructions\n"
                                                                                                                                  "- fxsr: FXSAVE/FXRSTOR instructions\n"
                                                                                                                                  "- sse/sse2/sse3/...: Streaming SIMD Extensions\n"
                                                                                                                                  "- avx/avx2: Advanced Vector Extensions\n"
                                                                                                                                  "- aes: AES-NI instruction set\n"
                                                                                                                                  "- vmx: Intel Virtualization Technology (VT-x)\n"
                                                                                                                                  "- smx: Safer Mode Extensions (Intel TXT)\n"
                                                                                                                                  "- ht: Hyper-Threading\n"
                                                                                                                                  "- nx: NX bit (No-eXecute — جلوگیری از اجرای کد در حافظه داده)\n"
                                                                                                                                  "- syscall: SYSCALL/SYSRET instructions\n"
                                                                                                                                  "- rdtscp: RDTSCP instruction\n"
                                                                                                                                  "- lm: Long Mode (64-bit)\n"
                                                                                                                                  "این لیست بر اساس سخت‌افزار واقعی سیستم متفاوت است.")),
                                              OpenApiExample("آیا در «وی إم» اجرا می‌شود؟", value="hypervisor", description="آیا سیستم داخل یک ماشین مجازی (VM) اجرا می‌شود؟\n- True: بله (مثلاً در KVM، VMware)\n- False: خیر (روی سخت‌افزار فیزیکی)"),
                                              OpenApiExample("نوع مجازی‌سازی سخت‌افزاری", value="virtualization", description="نوع فناوری مجازی‌سازی سخت‌افزاری:\n- VT-x: اینتل\n- AMD-V: AMD\n- غیرفعال: اگر پشتیبانی نشود"),
                                              OpenApiExample("درصد کلی استفاده از «سی پی یو»", value="usage_percent_total", description="درصد کلی استفاده از CPU در سراسر سیستم (همه هسته‌ها یک‌جا).\nمحاسبه‌شده در یک بازه زمانی کوتاه (مثلاً 100ms)."),
                                              OpenApiExample("فرکانس لحظه‌ای «سی پی یو» (برحسب مگاهرتز)", value="frequency_total", description="فرکانس لحظه‌ای CPU به مگاهرتز (MHz).\nمی‌تواند به دلیل Turbo Boost یا Scaling متغیر باشد."),
                                              OpenApiExample("لیست درصدهای هر هسته", value="per_core_usage", description="لیستی از درصدهای استفاده هر هسته منطقی به‌صورت جداگانه.\nتعداد عناصر = تعداد هسته‌های منطقی."),
                                              OpenApiExample("لیست فرکانس هر هسته (برحسب مگاهرتز)", value="per_core_frequency", description="لیستی از فرکانس‌های لحظه‌ای هر هسته به مگاهرتز (MHz).\nاستخراج‌شده از فیلد «cpu MHz» در /proc/cpuinfo."), ], )


class CPUInfoViewSet(viewsets.ViewSet, CPUValidationMixin):
    """دریافت اطلاعات CPU (فقط کلی، بدون پشتیبانی از core_id)."""

    @extend_schema(parameters=[ParamPropertyCPU])
    def list(self, request: Request) -> Response:
        save_to_db = get_request_param(request, "save_to_db", bool, False)  # نادیده گرفته می‌شود
        prop = get_request_param(request, "property", str, None)
        if prop:
            prop = prop.strip().lower()
        request_data = dict(request.query_params)

        try:
            fields = None
            if prop and prop != "all":
                if prop not in CPU_PROPERTY_CHOICES:
                    raise ValueError(f"property نامعتبر. مقادیر مجاز: {', '.join(CPU_PROPERTY_CHOICES)}")
                fields = [prop]
            if fields:
                self.validate_fields(fields)

            data = CPUManager().gather_info(fields=fields)

            return StandardResponse(data=data,
                                    message="اطلاعات CPU با موفقیت دریافت شد.",
                                    request_data=request_data,
                                    save_to_db=False,  # ✅ همیشه False
                                    )

        except ValueError as e:
            return StandardErrorResponse(error_code="invalid_input",
                                         error_message=str(e),
                                         status=400,
                                         request_data=request_data,
                                         save_to_db=False,
                                         )
        except CLICommandError as e:
            return build_standard_error_response(exc=e,
                                                 error_code="lscpu_failed",
                                                 error_message="خطا در اجرای دستور lscpu.",
                                                 request_data=request_data,
                                                 save_to_db=False,
                                                 )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="cpu_fetch_failed",
                error_message="خطا در دریافت اطلاعات CPU.",
                request_data=request_data,
                save_to_db=False,
            )


# ========== MEMORY ==========
MEMORY_PROPERTY_CHOICES = [
    "all",
    # دریافت تمام فیلدهای اطلاعات حافظه به‌صورت یکجا.

    "memory_blocks",
    # لیستی از بلوک‌های فیزیکی حافظه که سیستم آن‌ها را شناسایی کرده است. هر بلاک شامل:
    # - range: محدوده آدرس‌های فیزیکی مجازی‌شده، به فرمت "start-end" (مثال: "0-12")
    # - size_bytes: اندازه بلاک به بایت (خالص، بدون پیشوند)
    # - state: وضعیت بلاک — "online" (فعال) یا "offline" (غیرفعال)
    # - removable: آیا بلاک قابل حذف پویا است؟ — "yes" یا "no"
    # - device: دستگاه مرتبط (در صورت وجود، مثل در سرورهای با NVDIMM)
    # این اطلاعات از دستور lsmem گرفته می‌شود و برای سرورهای با قابلیت Hotplug RAM مهم است.

    "total_online_memory_bytes",
    # مجموع حافظه‌ی فیزیکی فعال (on) در سیستم، به بایت.
    # فقط بلوک‌هایی که state=online هستند شمرده می‌شوند.
    # این حافظه در دسترس سیستم‌عامل است.

    "total_offline_memory_bytes",
    # مجموع حافظه‌ی فیزیکی غیرفعال (off) در سیستم، به بایت.
    # بلوک‌هایی که state=offline هستند (مثلاً پس از hot-unplug یا به دلیل خطا).
    # این حافظه در دسترس سیستم‌عامل نیست.
    "total_bytes",
    # کل حافظه RAM نصب‌شده که هسته لینوکس آن را در دسترس دارد (همان MemTotal در /proc/meminfo)، به بایت.
    # این شامل تمام حافظه‌ی فیزیکی است که بوت شده و قابل استفاده است.

    "available_bytes",
    # حافظه‌ی قابل استفاده فعلی بدون نیاز به استفاده از swap.
    # این مقدار = MemFree + Buffers + Cached
    # Buffers: حافظه‌ی مورد استفاده برای I/O بلاک‌ها
    # Cached: حافظه‌ی مورد استفاده برای کش فایل‌سیستم
    # این فیلد بهترین معیار برای "چقدر حافظه آزاد داریم؟" است.

    "used_bytes",
    # حافظه‌ی در حال استفاده = total_bytes - available_bytes (به بایت).
    # این مقدار نشان می‌دهد چقدر از RAM در حال استفاده توسط فرآیندها و هسته است.

    "free_bytes",
    # حافظه‌ی کاملاً آزاد (فقط MemFree از /proc/meminfo)، به بایت.
    # این حافظه هیچ‌گاه توسط هسته برای کش یا بافر استفاده نشده است.
    # توجه: این مقدار معمولاً کوچک است حتی در سیستم‌های بی‌بار — چون لینوکس از حافظه آزاد برای کش استفاده می‌کند.

    "usage_percent",
    # درصد استفاده از حافظه بر اساس فرمول داخلی: (used_bytes / total_bytes) * 100
    # مقداری بین 0.0 تا 100.0 با دقت دو رقم اعشار.
    # این محاسبه مبتنی بر داده‌های /proc/meminfo است.

    "psutil_usage_percent",
    # درصد استفاده از حافظه همان‌طور که توسط کتابخانه psutil گزارش شده است.
    # این مقدار از psutil.virtual_memory().percent گرفته می‌شود.
    # ممکن است با محاسبه داخلی اختلاف جزئی داشته باشد به دلیل روش‌های متفاوت محاسبه.
]

ParamPropertyMemory = OpenApiParameter(name="property", type=str, required=False, enum=MEMORY_PROPERTY_CHOICES,
                                       description="انتخاب یک فیلد خاص از اطلاعات حافظه یا ارسال 'all' برای دریافت همه فیلدها.",
                                       examples=[OpenApiExample("همه فیلدها", value="all", description="دریافت تمام فیلدهای اطلاعات حافظه (RAM) به‌صورت یکجا."),
                                                 OpenApiExample("لیست بلوک‌های فیزیکی حافظه", value="memory_blocks", description=("لیستی از بلوک‌های فیزیکی حافظه که سیستم آن‌ها را شناسایی کرده است.\n"
                                                                                                                                  "هر بلاک شامل فیلدهای زیر است:\n"
                                                                                                                                  "- range: محدوده آدرس‌های فیزیکی (مثال: «0-12»)\n"
                                                                                                                                  "- size_bytes: اندازه بلاک به بایت (عدد خالص)\n"
                                                                                                                                  "- state: وضعیت — «online» (فعال) یا «offline» (غیرفعال)\n"
                                                                                                                                  "- removable: آیا بلاک قابل حذف پویا است؟ («yes» یا «no»)\n"
                                                                                                                                  "- device: دستگاه مرتبط (در صورت وجود، مثلاً برای NVDIMM)")),
                                                 OpenApiExample("کل حافظه فعال (بایت)", value="total_online_memory_bytes", description="مجموع حافظه‌ی فیزیکی فعال (on) در سیستم، به بایت.\n(فقط بلوک‌هایی که state=online هستند)"),
                                                 OpenApiExample("کل حافظه غیرفعال (بایت)", value="total_offline_memory_bytes", description="مجموع حافظه‌ی فیزیکی غیرفعال (off) در سیستم، به بایت.\n(بلوک‌هایی که state=offline هستند)"),
                                                 OpenApiExample("کل «رَم» نصب‌شده (MemTotal به بایت)", value="total_bytes", description="کل حافظه RAM نصب‌شده که هسته لینوکس در دسترس دارد.\n(همان MemTotal در /proc/meminfo) به بایت."),
                                                 OpenApiExample("حافظه قابل استفاده فعلی (بایت)", value="available_bytes", description=("حافظه‌ی قابل استفاده فعلی بدون نیاز به swap.\n"
                                                                                                                                        "محاسبه: MemFree + Buffers + Cached (به بایت).\n"
                                                                                                                                        "این بهترین معیار برای «چقدر حافظه آزاد داریم؟» است.")),
                                                 OpenApiExample("حافظه در حال استفاده (بایت)", value="used_bytes", description="حافظه‌ی در حال استفاده = total_bytes - available_bytes (به بایت)."),
                                                 OpenApiExample("حافظه کاملاً آزاد (MemFree به بایت)", value="free_bytes", description="حافظه‌ی کاملاً آزاد (فقط MemFree از /proc/meminfo) به بایت.\nمعمولاً کوچک است حتی در سیستم‌های بی‌بار."),
                                                 OpenApiExample("درصد استفاده بر اساس محاسبه داخلی", value="usage_percent", description="درصد استفاده از حافظه بر اساس فرمول:\n(used_bytes / total_bytes) * 100\nبا دقت دو رقم اعشار."),
                                                 OpenApiExample("درصد استفاده گزارش‌شده توسط psutil", value="psutil_usage_percent", description="درصد استفاده از حافظه همان‌طور که توسط کتابخانه psutil گزارش شده است.\nمقدار ممکن است با محاسبه داخلی کمی متفاوت باشد."), ], )


class MemoryInfoViewSet(viewsets.ViewSet, MemoryValidationMixin):
    """دریافت اطلاعات حافظه (RAM) سیستم."""

    @extend_schema(parameters=[ParamPropertyMemory])
    def list(self, request: Request) -> Response:
        save_to_db = get_request_param(request, "save_to_db", bool, False)  # نادیده گرفته می‌شود
        prop = get_request_param(request, "property", str, None)
        if prop:
            prop = prop.strip().lower()
        request_data = dict(request.query_params)

        try:
            fields = None
            if prop and prop != "all":
                if prop not in MEMORY_PROPERTY_CHOICES:
                    raise ValueError(f"property نامعتبر. مقادیر مجاز: {', '.join(MEMORY_PROPERTY_CHOICES)}")
                fields = [prop]
            if fields:
                self.validate_fields(fields)

            data = MemoryManager().gather_info(fields=fields)

            return StandardResponse(
                data=data,
                message="اطلاعات حافظه با موفقیت دریافت شد.",
                request_data=request_data,
                save_to_db=False,  # ✅ همیشه False
            )

        except ValueError as e:
            return StandardErrorResponse(
                error_code="invalid_input",
                error_message=str(e),
                status=400,
                request_data=request_data,
                save_to_db=False,
            )
        except CLICommandError as e:
            return build_standard_error_response(
                exc=e,
                error_code="lsmem_failed",
                error_message="خطا در اجرای دستور lsmem.",
                request_data=request_data,
                save_to_db=False,
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="memory_fetch_failed",
                error_message="خطا در دریافت اطلاعات حافظه.",
                request_data=request_data,
                save_to_db=False,
            )


# ========== NETWORK ==========
ParamNicName = OpenApiParameter(name="nic_name", type=str, required=True, location="path", description="نام کارت شبکه (مانند eth0, enp3s0)", )

ParamPropertyNetwork = OpenApiParameter(name="property", type=str, required=False,
                                        enum=["all", "bandwidth", "traffic_summary", "hardware", "general"],
                                        description="انتخاب بخش خاصی از اطلاعات کارت شبکه یا 'all' برای دریافت همه.",
                                        examples=[OpenApiExample("همه بخش‌ها", value="all"),
                                                  OpenApiExample("پهنای باند", value="bandwidth"),
                                                  OpenApiExample("خلاصه ترافیک", value="traffic_summary"),
                                                  OpenApiExample("اطلاعات سخت‌افزاری", value="hardware"),
                                                  OpenApiExample("اطلاعات عمومی", value="general"), ], )

BodyNetworkConfig = {"type": "object",
                     "properties": {"mode": {"type": "string", "enum": ["dhcp", "static"], "description": "حالت آدرس‌دهی شبکه: «dhcp» برای دریافت خودکار آدرس، «static» برای تنظیم دستی."},
                                    "ip": {"type": "string", "description": "آدرس IP ثابت (فقط در حالت «static» معتبر است)."},
                                    "netmask": {"type": "string", "description": "ماسک شبکه (فقط در حالت «static» معتبر است)."},
                                    "gateway": {"type": "string", "description": "آدرس دروازه پیش‌فرض (فقط در حالت «static» معتبر است)."},
                                    "dns": {"type": "array", "items": {"type": "string"}, "description": "لیست سرورهای DNS (مثال: [\"8.8.8.8\", \"1.1.1.1\"])."},
                                    "mtu": {"type": "integer", "description": "اندازه MTU (Maximum Transmission Unit) برای اینترفیس (اختیاری، پیش‌فرض سیستم استفاده می‌شود)."},
                                    **BodyParameterSaveToDB["properties"]},
                     "required": ["mode"]}


class NetworkInfoViewSet(viewsets.ViewSet, NetworkValidationMixin):
    """مدیریت و دریافت اطلاعات کارت‌های شبکه."""

    lookup_field = "nic_name"

    @extend_schema(responses={200: inline_serializer("NICList", {"data": serializers.JSONField()})})
    def list(self, request: Request) -> Response:
        """دریافت لیست تمام کارت‌های شبکه."""
        try:
            data = NetworkManager().list_nics()
            return StandardResponse(data=data, request_data=dict(request.query_params), save_to_db=False,
                                    message="لیست کارت‌های شبکه با موفقیت دریافت شد.", )
        except Exception as e:
            return build_standard_error_response(exc=e, request_data=dict(request.query_params), save_to_db=False,
                                                 error_code="nic_list_failed",
                                                 error_message="خطا در دریافت لیست کارت‌های شبکه.", )

    @extend_schema(parameters=[ParamNicName, ParamPropertyNetwork], responses={200: inline_serializer("NICProperty", {"data": serializers.JSONField()})})
    def retrieve(self, request: Request, nic_name: str) -> Response:
        """
        دریافت تمام یا بخش خاصی از اطلاعات یک کارت شبکه.
        با استفاده از پارامتر `property` می‌توانید فقط یکی از بخش‌های زیر را دریافت کنید:
        - bandwidth
        - traffic_summary
        - hardware
        - general
        """
        request_data = dict(request.query_params)
        prop = get_request_param(request, "property", str, "all")
        if prop:
            prop = prop.strip().lower()

        # اعتبارسنجی نام NIC
        err = self.validate_nic_exists(nic_name, save_to_db=False, request_data=request_data)
        if err:
            return err

        # لیست مجاز propertyها
        valid_props = {"all", "bandwidth", "traffic_summary", "hardware", "general"}
        if prop not in valid_props:
            return StandardErrorResponse(status=400, request_data=request_data, save_to_db=False,
                                         error_code="invalid_property",
                                         error_message=f"property نامعتبر است. مقادیر مجاز: {', '.join(valid_props)}", )

        try:
            manager = NetworkManager()

            # انتخاب داده بر اساس property
            if prop == "all":
                data = {"bandwidth": manager.get_bandwidth(nic_name),
                        "traffic_summary": manager.get_traffic_summary(nic_name),
                        "hardware": manager.get_hardware_info(nic_name),
                        "general": manager.get_general_info(nic_name), }
            elif prop == "bandwidth":
                data = manager.get_bandwidth(nic_name)
            elif prop == "traffic_summary":
                data = manager.get_traffic_summary(nic_name)
            elif prop == "hardware":
                data = manager.get_hardware_info(nic_name)
            elif prop == "general":
                data = manager.get_general_info(nic_name)
            else:
                # این حالت نباید رخ دهد (چون بالاتر چک شده)
                data = {}

            return StandardResponse(data=data, request_data=request_data, save_to_db=False,
                                    message=f"اطلاعات '{prop}' برای کارت '{nic_name}' با موفقیت دریافت شد.", )

        except Exception as e:
            return build_standard_error_response(exc=e, request_data=request_data, save_to_db=False,
                                                 error_code="nic_retrieve_failed",
                                                 error_message="خطا در دریافت اطلاعات کارت شبکه.", )

    @extend_schema(request=BodyNetworkConfig,
                   parameters=[ParamNicName],
                   examples=[OpenApiExample(name="پیکربندی دستی (static)",
                                            value={"mode": "static",
                                                   "ip": "172.16.16.190",
                                                   "netmask": "255.255.255.0",
                                                   "gateway": "172.16.16.1",
                                                   "dns": ["172.16.16.1", "8.8.8.8"],
                                                   "mtu": 1500, },
                                            description="مثالی از پیکربندی کامل یک کارت شبکه با آدرس ثابت.", ),
                             OpenApiExample(name="پیکربندی خودکار (dhcp)",
                                            value={"mode": "dhcp", "mtu": 1500},
                                            description="مثالی از پیکربندی DHCP با تغییر MTU (بقیه فیلدها نادیده گرفته می‌شوند).", ), ],
                   responses={200: StandardResponse})
    @action(detail=True, methods=["post"], url_path="configure")
    def configure(self, request: Request, nic_name: str) -> Response:
        """پیکربندی کارت شبکه از طریق فایل /etc/network/interfaces.d/"""
        request_data = dict(request.data)
        err = self.validate_nic_exists(nic_name, save_to_db=False, request_data=request_data)
        if err:
            return err
        err = self.validate_network_config(request.data, save_to_db=False, request_data=request_data)
        if err:
            return err
        try:
            NetworkManager().configure_interface_file(nic_name, request.data)
            NetworkManager().restart_interface(nic_name)
            return StandardResponse(
                message=f"کارت شبکه '{nic_name}' با موفقیت پیکربندی و راه‌اندازی مجدد شد.",
                request_data=request_data,
                save_to_db=False,
            )
        except Exception as e:
            return build_standard_error_response(
                exc=e,
                error_code="nic_configure_failed",
                error_message="خطا در پیکربندی کارت شبکه.",
                request_data=request_data,
                save_to_db=False,
            )
