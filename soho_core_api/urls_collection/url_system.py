# url_pool.py

from django.urls import path
from soho_core_api.views_collection import view_systems

urlpatterns = [
    path("user/", view_systems.UserListView.as_view(), name="osuser-list"),
    path("user/create/", view_systems.UserCreateView.as_view(), name="osuser-create"),
    path("power/<str:action>/", view_systems.OSpowerView.as_view(), name="os-power"),

]
