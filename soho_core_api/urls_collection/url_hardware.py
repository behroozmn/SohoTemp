# soho_core_api/urls.py
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from soho_core_api.views_collection.view_hardware import CPUInfoViewSet

cpu_router = SimpleRouter()
cpu_router.register(r"cpu", CPUInfoViewSet, basename="cpu-info")

urlpatterns = [path("", include(cpu_router.urls)), ]
