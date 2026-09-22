from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import PrescriptionDocumentViewSet

router = DefaultRouter()
router.register("prescriptions/documents", PrescriptionDocumentViewSet, basename="prescription-document")

urlpatterns = [path("", include(router.urls))]
