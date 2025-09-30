from django.urls import path
from soho_core_api.views_collection import view_network

urlpatterns = [
    path('', view_network.network),

# خواندن همه کارت‌های شبکه
    path('nicfile/all', view_network.GetAllNetworkInterfacesView.as_view(), name='network-interfaces-list'),

    # خواندن یک کارت خاص
    path('nicfile/<str:interface_name>/', view_network.GetNetworkInterfaceView.as_view(), name='network-interface-detail'),

    # تغییر IP یک کارت
    path('nicfile/<str:interface_name>/ip/edit/', view_network.UpdateNetworkInterfaceIPView.as_view(), name='network-interface-update-ip'),

]
