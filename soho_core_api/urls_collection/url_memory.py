from django.contrib import admin

from django.urls import path
from soho_core_api.views_collection import view_memory

urlpatterns = [
    path('', view_memory.memory),
]
