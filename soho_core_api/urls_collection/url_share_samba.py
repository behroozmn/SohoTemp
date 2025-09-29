from django.urls import path
from soho_core_api.views_collection import view_share_samba

urlpatterns = [

    path('', view_share_samba.SambaListView.as_view()),

    path('create/', view_share_samba.SambaCreateView.as_view()),
    path('delete/', view_share_samba.SambaDeleteView.as_view()),
    path('user/add/', view_share_samba.SambaUserCreateView.as_view()),
    path('user/enable/', view_share_samba.SambaUserEnableView.as_view()),
]
