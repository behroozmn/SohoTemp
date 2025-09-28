from django.urls import path
from soho_core_api.views_collection import view_share_samba

urlpatterns = [

    path('', view_share_samba.SambaListView.as_view()),

    path('create', view_share_samba.SambaCreateView.as_view()),
]
