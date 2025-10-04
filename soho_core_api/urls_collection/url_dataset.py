# url_pool.py

from django.urls import path
from soho_core_api.views_collection import view_dataset

urlpatterns = [
    path("", view_dataset.DatasetDetailView.as_view(), name="volume-detail"),

    path("create", view_dataset.DatasetCreateView.as_view(), name="volume-create"),

    path("delete", view_dataset.DatasetDeleteView.as_view(), name="volume-delete")
    ]
