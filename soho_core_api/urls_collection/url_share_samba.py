# soho_core_api/urls.py
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from soho_core_api.views_collection.view_samba import SambaUserViewSet, SambaGroupViewSet, SambaSharepointViewSet

router = SimpleRouter()
router.register(r"samba/users", SambaUserViewSet, basename="samba-user")
router.register(r"samba/groups", SambaGroupViewSet, basename="samba-group")
router.register(r"samba/sharepoints", SambaSharepointViewSet, basename="samba-sharepoint")

urlpatterns = [
    path("api/", include(router.urls)),
]