# url_pool.py

from django.urls import path
from soho_core_api.views_collection import view_OsUser

urlpatterns = [
    path("", view_OsUser.UserListView.as_view(), name="osuser-list"),
    path("create/", view_OsUser.UserCreateView.as_view(), name="osuser-create"),

]
