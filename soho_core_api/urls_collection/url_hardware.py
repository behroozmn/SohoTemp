# soho_core_api/urls.py
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from soho_core_api.views_collection.view_hardware import CPUInfoViewSet, MemoryInfoViewSet

# ایجاد روتر برای سخت‌افزار
hardware_router = SimpleRouter()

hardware_router.register(r"cpu", CPUInfoViewSet, basename="cpu-info")
hardware_router.register(r"memory", MemoryInfoViewSet, basename="memory-info")

urlpatterns = [path("", include(hardware_router.urls)), ]
