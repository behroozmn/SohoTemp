# url_pool.py

from django.urls import path
from soho_core_api.views_collection import view_zpool

urlpatterns = [
    path("", view_zpool.ZpoolListNameView.as_view(), name="zpool-list"),

    path("details", view_zpool.ZpoolListDetailView.as_view(), name="details"),

    path("create", view_zpool.ZpoolCreaView.as_view(), name="create"),
    path("delete", view_zpool.ZpoolDeleteView.as_view(), name="delete"),

]
