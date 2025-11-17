from django.urls import path
from soho_core_api.views_collection import view_zpool

urlpatterns = [
    path('create/', view_zpool.ZpoolCreateView.as_view(), name='zpool-create'),

    path('', view_zpool.ZpoolListView.as_view(), name='zpool-list'),

    path('<str:pool_name>/devices/', view_zpool.ZpoolDevicesView.as_view(), name='zpool-devices'),
    path('<str:pool_name>/destroy/', view_zpool.ZpoolDestroyView.as_view(), name='zpool-destroy'),
    path('<str:pool_name>/replace/', view_zpool.ZpoolReplaceDiskView.as_view(), name='zpool-replace'),
    path('<str:pool_name>/add/', view_zpool.ZpoolAddVdevView.as_view(), name='zpool-add-vdev'),
    path('<str:pool_name>/set-property/', view_zpool.ZpoolSetPropertyView.as_view(), name='zpool-set-property'),

    # ❗ در آخر: مسیر عمومی جزئیات (چون گیرنده‌ترین الگو است)
    path('<str:pool_name>/', view_zpool.ZpoolDetailView.as_view(), name='zpool-detail'),
]