# soho_core_api/urls.py (نسخه بهینه‌شده)
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from soho_core_api.views_collection.view_hardware import CPUInfoViewSet, MemoryInfoViewSet, NetworkInfoViewSet

router = SimpleRouter()
router.register(r"cpu", CPUInfoViewSet, basename="cpu-info")
router.register(r"memory", MemoryInfoViewSet, basename="memory-info")
router.register(r"network", NetworkInfoViewSet, basename="network")

urlpatterns = [
    path("", include(router.urls)),
]