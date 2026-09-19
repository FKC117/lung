from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import OptionsCatalogAPIView, SiteSettingsAPIView, register_option_routes

router = DefaultRouter()
register_option_routes(router)

urlpatterns = [
    path("catalog/", OptionsCatalogAPIView.as_view(), name="options-catalog"),
    path("site-settings/", SiteSettingsAPIView.as_view(), name="site-settings"),
    path("", include(router.urls)),
]
