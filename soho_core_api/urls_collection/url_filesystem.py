# url_pool.py

from django.urls import path
from soho_core_api.views_collection import view_filesystem

urlpatterns = [
    path("", view_filesystem.FilesystemDetailView.as_view(), name="filesystem-detail"),

    path("create/", view_filesystem.FilesystemCreateView.as_view(), name="filesystem-create"),

    path("delete/", view_filesystem.FilesystemDeleteView.as_view(), name="filesystem-delete")
    ]
