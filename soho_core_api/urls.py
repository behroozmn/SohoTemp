"""
URL configuration for soho_core_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin

import soho_core_api.views_collection.view_network
from .views_collection import view_memory, view_disk, view_cpu, view_network
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('rest_framework.urls')),

    # YOUR PATTERNS
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),  # Swagger

    # Optional UI:
    path('api/schema/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),  # Swagger
    path('auth-token/', obtain_auth_token, name='generate_auth_token'),



    path("api/cpu/", include("soho_core_api.urls_collection.url_cpu")),
    path("api/memory/", include("soho_core_api.urls_collection.url_memory")),
    path("api/net/", include("soho_core_api.urls_collection.url_network")),
    path("api/disk/", include("soho_core_api.urls_collection.url_disk")),
    path("api/zpool/", include("soho_core_api.urls_collection.url_zpool")),

]
