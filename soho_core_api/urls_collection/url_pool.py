# url_pool.py

from django.urls import path
from soho_core_api.views_collection import view_pool

urlpatterns = [
    # GET → list pools, POST → create (not implemented)
    path("", view_pool.PoolListView.as_view(), name="pool-list"),

    path("<str:pool_name>/", view_pool.PoolDetailView.as_view(), name="pool-detail"),

    path("<str:pool_name>/datasets/", view_pool.PoolDatasetsView.as_view(), name="pool-datasets"),

    path("<str:pool_name>/devices/", view_pool.PoolDevicesView.as_view(), name="pool-devices"),

    path("<str:pool_name>/device-names/", view_pool.PoolDeviceNamesView.as_view(), name="pool-device-names"),

    path("<str:pool_name>/features/", view_pool.PoolFeaturesView.as_view(), name="pool-features"),

    path("<str:pool_name>/capacity/", view_pool.PoolCapacityView.as_view(), name="pool-capacity"),
]
