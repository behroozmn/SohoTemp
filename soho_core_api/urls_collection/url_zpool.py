# url_pool.py

from django.urls import path
from soho_core_api.views_collection import view_zpool

urlpatterns = [
    path("", view_zpool.ZpoolListNameView.as_view(), name="zpool-list"),

    path("details", view_zpool.ZpoolListDetailView.as_view(), name="details"),

]
