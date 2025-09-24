from django.urls import path
from soho_core_api.views_collection import view_network

urlpatterns = [
    path('', view_network.network),
]
