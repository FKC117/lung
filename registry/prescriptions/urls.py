from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import PrescriptionBatchJobViewSet, PrescriptionDocumentViewSet

router = DefaultRouter()
router.register("prescriptions/documents", PrescriptionDocumentViewSet, basename="prescription-document")
router.register("prescriptions/batch-jobs", PrescriptionBatchJobViewSet, basename="prescription-batch-job")

urlpatterns = [path("", include(router.urls))]
