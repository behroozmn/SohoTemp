# url_pool.py

from django.urls import path
from soho_core_api.views_collection import view_zpool

urlpatterns = [
    # GET → list pools, POST → create (not implemented)
    path("", view_zpool.zPoolListView.as_view(), name="zpool-list"),

    # path("<str:pool_name>/", view_zpool, name="zpool-detail"),

]
