# soho_core_api/urls_collection/url_zpool.py

from django.urls import path
from soho_core_api.views_collection import view_zpool

urlpatterns = [
    path('create/', view_zpool.ZpoolCreateView.as_view(), name='zpool-create'),
    path('', view_zpool.ZpoolListView.as_view(), name='zpool'),
    path('<str:pool_name>/', view_zpool.ZpoolDetailView.as_view(), name='zpool-detail'),
    path('<str:pool_name>/devices/', view_zpool.ZpoolDevicesView.as_view(), name='zpool-devices'),
    path('<str:pool_name>/destroy/', view_zpool.ZpoolManageView.as_view(endpoint_type='destroy'), name='zpool-destroy'),
    path('<str:pool_name>/replace/', view_zpool.ZpoolManageView.as_view(endpoint_type='replace'), name='zpool-replace'),
    path('<str:pool_name>/add/', view_zpool.ZpoolManageView.as_view(endpoint_type='add'), name='zpool-add-vdev'),
    path('<str:pool_name>/set-property/', view_zpool.ZpoolManageView.as_view(endpoint_type='set-property'), name='zpool-set-property'),
]