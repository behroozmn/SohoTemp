# soho_core_api/urls/url_disk.py

from django.urls import path
from soho_core_api.views_collection import view_disk

urlpatterns = [
    path('', view_disk.DiskView.as_view(), name='disk'),
    path('<str:disk_name>/', view_disk.DiskView.as_view(), name='disk-detail'),

    path('names/', view_disk.DiskNameListView.as_view(), name='disk-names'),
    path('count/', view_disk.DiskCountView.as_view(), name='disk-count'),
    path('os-disk/', view_disk.OSdiskView.as_view(), name='os-disk'),

    path('<str:disk_name>/partition-count/', view_disk.DiskPartitionCountView.as_view(), name='disk-partition-count'),
    path('<str:disk_name>/partition-names/', view_disk.DiskPartitionNamesView.as_view(), name='disk-partition-names'),
    path('<str:disk_name>/type/', view_disk.DiskTypeView.as_view(), name='disk-type'),
    path('<str:disk_name>/temperature/', view_disk.DiskTemperatureView.as_view(), name='disk-temperature'),
    path('<str:disk_name>/has-os/', view_disk.DiskHasOSView.as_view(), name='disk-has-os'),
    path('<str:disk_name>/has-partitions/', view_disk.DiskHasPartitionsView.as_view(), name='disk-has-partitions'),
    path('<str:disk_name>/total-size/', view_disk.DiskTotalSizeView.as_view(), name='disk-total-size'),

    path('partition/<str:partition_name>/mounted/', view_disk.PartitionIsMountedView.as_view(), name='partition-is-mounted'),
    path('partition/<str:partition_name>/total-size/', view_disk.PartitionTotalSizeView.as_view(), name='partition-total-size'),

    path('<str:disk_name>/wipe/', view_disk.DiskWipeSignaturesView.as_view(), name='disk-wipe'),
    path('<str:disk_name>/clear-zfs/', view_disk.DiskClearZFSLabelView.as_view(), name='disk-clear-zfs'),
]