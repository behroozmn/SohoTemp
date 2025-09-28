from django.urls import path
from soho_core_api.views_collection import view_disk

urlpatterns = [

    path('', view_disk.disk),

    path('wwn/map', view_disk.DiskWwnView.as_view()),
]
