from django.urls import path
from soho_core_api.views_collection.view_filesystem import FilesystemListView, FilesystemDetailView

urlpatterns = [
    path("filesystems/", FilesystemListView.as_view(), name="filesystem-list"),
    path("filesystems/<str:pool_name>/<str:fs_name>/", FilesystemDetailView.as_view(), name="filesystem-detail"),
]
