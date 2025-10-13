# url_pool.py

from django.urls import path
from soho_core_api.views_collection import view_system_web

urlpatterns = [
    path("users/", view_system_web.WebUserListView.as_view()),
    path("user/create/", view_system_web.WebUserCreateView.as_view()),
    path("user/delete/", view_system_web.WebUserDeleteView.as_view()),
    path("user/pass/change", view_system_web.WebUserChangePasswordView.as_view()),

]
