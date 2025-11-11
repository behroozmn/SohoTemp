# soho_core_api/urls/url_disk.py

from django.urls import path
from soho_core_api.views_collection import view_disk

urlpatterns = [
    path('', view_disk.DiskListView.as_view(), name='disk-list'),
    path('<str:disk_name>/', view_disk.DiskDetailView.as_view(), name='disk-detail'),
    path('<str:disk_name>/wipe/', view_disk.DiskWipeSignaturesView.as_view(), name='disk-wipe'),
    path('<str:disk_name>/clear-zfs/', view_disk.DiskClearZFSLabelView.as_view(), name='disk-clear-zfs'),
]