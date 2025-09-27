# url_pool.py

from django.urls import path
from soho_core_api.views_collection import view_volume

urlpatterns = [
    path("", view_volume.VolumeDetailView.as_view(), name="volume-detail"),

    path("create", view_volume.VolumeCreateView.as_view(), name="volume-create"),

    path("delete", view_volume.VolumeDeleteView.as_view(), name="volume-delete")
    ]
