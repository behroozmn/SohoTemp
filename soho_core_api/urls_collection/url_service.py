from django.urls import path
from soho_core_api.views_collection import view_Service

urlpatterns = [
    path("", view_Service.ServiceListView.as_view(), name="service-list"),
]
