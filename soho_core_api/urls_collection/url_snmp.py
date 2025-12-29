# soho_core_api/urls_collection/url_snmp.py
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from soho_core_api.views_collection.view_snmp import SNMPViewSet

router = SimpleRouter()
router.register(r"", SNMPViewSet, basename="snmp")

urlpatterns = [
    path("", include(router.urls)),
]