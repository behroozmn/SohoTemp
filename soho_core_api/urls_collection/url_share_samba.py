# soho_core_api/urls.py
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from soho_core_api.views_collection.view_samba import SambaUserViewSet, SambaGroupViewSet, SambaSharepointViewSet

router = SimpleRouter()
router.register(r"users", SambaUserViewSet, basename="samba-user")
router.register(r"groups", SambaGroupViewSet, basename="samba-group")
router.register(r"sharepoints", SambaSharepointViewSet, basename="samba-sharepoint")

urlpatterns = [
    path("", include(router.urls)),
]