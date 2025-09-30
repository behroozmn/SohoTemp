# url_pool.py

from django.urls import path
from soho_core_api.views_collection import view_os

urlpatterns = [
    path("user/", view_os.UserListView.as_view(), name="osuser-list"),
    path("user/create/", view_os.UserCreateView.as_view(), name="osuser-create"),
    path("power/<str:action>/", view_os.SystemPowerView.as_view(), name="os-power"),

]
