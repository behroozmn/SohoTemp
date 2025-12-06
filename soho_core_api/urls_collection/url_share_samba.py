from django.urls import path
from soho_core_api.views_collection.view_samba import SambaUserView, SambaGroupView, SambaSharepointView

urlpatterns = [
    # ========== User Endpoints ==========
    path("users/", SambaUserView.as_view(), name="samba-user-list"),
    path("users/<str:username>/", SambaUserView.as_view(), name="samba-user-detail"),

    # ========== Group Endpoints ==========
    path("groups/", SambaGroupView.as_view(), name="samba-group-list"),
    path("groups/<str:groupname>/", SambaGroupView.as_view(), name="samba-group-detail"),

    # ========== Sharepoint Endpoints ==========
    path("sharepoints/", SambaSharepointView.as_view(), name="samba-sharepoint-list"),
    path("sharepoints/<str:sharepoint_name>/", SambaSharepointView.as_view(), name="samba-sharepoint-detail"),
]
