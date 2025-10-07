# url_pool.py

from django.urls import path
from soho_core_api.views_collection import view_zpool

urlpatterns = [
    path("", view_zpool.ZpoolListView.as_view()),

    path("<str:pool_name>/", view_zpool.ZpoolDetailView.as_view()),

    path("disk/<str:pool_name>/", view_zpool.ZpoolDevicesView.as_view()),

    path("create", view_zpool.ZpoolCreaView.as_view()),

    path("delete", view_zpool.ZpoolDeleteView.as_view()),

]
