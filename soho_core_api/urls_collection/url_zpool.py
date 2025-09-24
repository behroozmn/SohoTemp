# url_zpool.py

from django.urls import path
from soho_core_api.views_collection import view_zpool

urlpatterns = [
    # GET → list pools, POST → create (not implemented)
    path("", view_zpool.ZPoolListView.as_view(), name="zpool-list"),
    # بقیه endpointها
    path("<str:pool_name>/", view_zpool.ZPoolDetailView.as_view(), name="zpool-detail"),

    path("<str:pool_name>/datasets/", view_zpool.ZPoolDatasetsView.as_view(), name="zpool-datasets"),

    path("<str:pool_name>/devices/", view_zpool.ZPoolDevicesView.as_view(), name="zpool-devices"),

    path("<str:pool_name>/device-names/", view_zpool.ZPoolDeviceNamesView.as_view(), name="zpool-device-names"),

    path("<str:pool_name>/features/", view_zpool.ZPoolFeaturesView.as_view(), name="zpool-features"),

    path("<str:pool_name>/capacity/", view_zpool.ZPoolCapacityView.as_view(), name="zpool-capacity"),
]
