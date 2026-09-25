"""
URL configuration for registry project.

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
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseNotFound
from django.urls import path, include


def private_prescription_media(request, path):
    """Prevent direct media serving; authorized access uses API file actions."""
    return HttpResponseNotFound()


media_prefix = settings.MEDIA_URL.lstrip("/")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("options.urls")),
    path("api/", include("records.urls")),
    path("api/", include("prescriptions.urls")),
    path(f"{media_prefix}prescriptions/<path:path>", private_prescription_media),
    path(f"{media_prefix}prescription_pages/<path:path>", private_prescription_media),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
