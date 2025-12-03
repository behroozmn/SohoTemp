from django.urls import path
from soho_core_api.views_collection.view_samba import SambaUserView, SambaGroupView, SambaSharepointView

urlpatterns = [
    # ========== User Endpoints ==========
    path("samba/users/", SambaUserView.as_view(), name="samba-user-list"),
    path("samba/users/<str:username>/", SambaUserView.as_view(), name="samba-user-detail"),

    # ========== Group Endpoints ==========
    path("samba/groups/", SambaGroupView.as_view(), name="samba-group-list"),
    path("samba/groups/<str:groupname>/", SambaGroupView.as_view(), name="samba-group-detail"),

    # ========== Sharepoint Endpoints ==========
    path("samba/sharepoints/", SambaSharepointView.as_view(), name="samba-sharepoint-list"),
    path("samba/sharepoints/<str:sharepoint_name>/", SambaSharepointView.as_view(), name="samba-sharepoint-detail"),
]
