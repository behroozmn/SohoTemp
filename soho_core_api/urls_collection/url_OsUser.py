# url_pool.py

from django.urls import path
from soho_core_api.views_collection import view_os_User

urlpatterns = [
    path("", view_os_User.UserListView.as_view(), name="osuser-list"),
    path("create/", view_os_User.UserCreateView.as_view(), name="osuser-create"),

]
