from django.urls import path
from soho_core_api.views_collection import view_zpool

urlpatterns = [
    # POST /api/zfs/pools/ → create (not implemented, but reserved)
    path("", view_zpool.ZPoolCreateView.as_view(), name="zpool-create"),

    # GET /api/zfs/pools/ → list all pools
    path("", view_zpool.ZPoolListView.as_view(), name="zpool-list"),

    # GET, PATCH, DELETE /api/zfs/pools/<name>/
    path("<str:pool_name>/", view_zpool.ZPoolDetailView.as_view(), name="zpool-detail"),

    # GET /api/zfs/pools/<name>/datasets/
    path("<str:pool_name>/datasets/", view_zpool.ZPoolDatasetsView.as_view(), name="zpool-datasets"),

    # GET /api/zfs/pools/<name>/devices/ → detailed vdevs
    path("<str:pool_name>/devices/", view_zpool.ZPoolDevicesView.as_view(), name="zpool-devices"),

    # GET /api/zfs/pools/<name>/device-names/ → only paths
    path("<str:pool_name>/device-names/", view_zpool.ZPoolDeviceNamesView.as_view(), name="zpool-device-names"),

    # GET /api/zfs/pools/<name>/features/
    path("<str:pool_name>/features/", view_zpool.ZPoolFeaturesView.as_view(), name="zpool-features"),

    # GET /api/zfs/pools/<name>/capacity/
    path("<str:pool_name>/capacity/", view_zpool.ZPoolCapacityView.as_view(), name="zpool-capacity"),
]