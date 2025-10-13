# url_pool.py

from django.urls import path
from soho_core_api.views_collection import view_system_os

urlpatterns = [
    path("user/", view_system_os.UserListView.as_view(), name="osuser-list"),
    path("user/create/", view_system_os.UserCreateView.as_view(), name="osuser-create"),

    path("user/delete/<str:username>/", view_system_os.UserDeleteView.as_view()),

    path("power/<str:action>/", view_system_os.OSpowerView.as_view(), name="os-power"),

]
