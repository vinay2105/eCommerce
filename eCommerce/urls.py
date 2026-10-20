"""
URL configuration for eCommerce project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
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
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONOpenAPIRenderer
from rest_framework.schemas import get_schema_view

from apps.common.views import live, ready

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/live/", live, name="health-live"),
    path("health/ready/", ready, name="health-ready"),
    path("api/v1/auth/", include("apps.users.urls")),
    path("api/v1/", include("apps.catalog.urls")),
    path(
        "api/schema/",
        get_schema_view(
            title="ShopForge API",
            version="1.0.0",
            public=True,
            permission_classes=[AllowAny],
            renderer_classes=[JSONOpenAPIRenderer],
        ),
        name="api-schema",
    ),
    path(
        "api/docs/",
        TemplateView.as_view(template_name="api_docs.html"),
        name="api-docs",
    ),
]
