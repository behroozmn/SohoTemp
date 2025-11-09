from django.urls import path
from soho_core_api.views_collection import view_disk

urlpatterns = [

    # path('', view_disk.disk),
    path('disks/', view_disk.DiskListView.as_view()),

    # path('wwn/map/', view_disk.DiskWwnView.as_view()),
    # path('free/', view_disk.DiskFreeView.as_view()),
    # path('delete/', view_disk.DiskDeleteView.as_view()),
    path('testok/', view_disk.DiskTestSuccessView.as_view()),
    path('testnotok/', view_disk.DiskTestFailedView.as_view()),
]
