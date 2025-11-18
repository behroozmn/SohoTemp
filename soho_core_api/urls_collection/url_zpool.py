# soho_core_api/urls_collection/url_zpool.py
from django.urls import path
from soho_core_api.views_collection import view_zpool

urlpatterns = [
    path('create/', view_zpool.ZpoolActionView.as_view(), name='zpool-create'),
    path('', view_zpool.ZpoolInfoView.as_view(), name='zpool'),
    path('<str:pool_name>/', view_zpool.ZpoolInfoView.as_view(), name='zpool-detail'),
    path('<str:pool_name>/devices/', view_zpool.ZpoolInfoView.as_view(), {'action': 'devices'}, name='zpool-devices'),
    path('<str:pool_name>/destroy/', view_zpool.ZpoolActionView.as_view(), {'action': 'destroy'}, name='zpool-destroy'),
    path('<str:pool_name>/replace/', view_zpool.ZpoolActionView.as_view(), {'action': 'replace'}, name='zpool-replace'),
    path('<str:pool_name>/add/', view_zpool.ZpoolActionView.as_view(), {'action': 'add'}, name='zpool-add-vdev'),
    path('<str:pool_name>/set-property/', view_zpool.ZpoolActionView.as_view(), {'action': 'set-property'}, name='zpool-set-property'),
]