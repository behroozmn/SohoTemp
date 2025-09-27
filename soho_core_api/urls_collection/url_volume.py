# url_pool.py

from django.urls import path
from soho_core_api.views_collection import view_volume

urlpatterns = [
    path("", view_volume.VolumeDetailView.as_view(), name="volume-detail")
    ]
