from django.urls import path
from soho_core_api.views_collection import view_file



urlpatterns = [

    path("set/permissions/", view_file.SetPermissionsView.as_view(), name="dir-set-permissions"),
    path("create/permissions/", view_file.CreateDirectoryView.as_view(), name="dir-create"),
    path("info/permissions/", view_file.GetFileInfoView.as_view(), name="dir-info"),
]