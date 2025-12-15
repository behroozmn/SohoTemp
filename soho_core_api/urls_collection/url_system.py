# soho_core_api/urls.py (نسخه بهینه‌شده)
from django.urls import path, include
from rest_framework.routers import SimpleRouter

from soho_core_api.views_collection.view_service import SystemServiceViewSet
from soho_core_api.views_collection.view_system import CPUInfoViewSet, MemoryInfoViewSet, NetworkInfoViewSet, PowerViewSet, DjangoUserViewSet

router = SimpleRouter()
router.register(r"cpu", CPUInfoViewSet, basename="cpu-info")
router.register(r"memory", MemoryInfoViewSet, basename="memory-info")
router.register(r"network", NetworkInfoViewSet, basename="network")
router.register(r"service", SystemServiceViewSet, basename="system-service")

router.register(r"power", PowerViewSet, basename="power")
router.register(r"ui-user", DjangoUserViewSet, basename="django-user")

urlpatterns = [path("", include(router.urls)), ]
