from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import (
    ClinicalObservationViewSet,
    DiagnosisViewSet,
    HistopathologyViewSet,
    MetastaticSiteRecordViewSet,
    PatientAnthropometryViewSet,
    PatientComorbidityViewSet,
    PatientViewSet,
)

router = DefaultRouter()
router.register("records/patients", PatientViewSet, basename="patient")
router.register("records/observations", ClinicalObservationViewSet, basename="clinical-observation")
router.register("records/anthropometries", PatientAnthropometryViewSet, basename="patient-anthropometry")
router.register("records/comorbidities", PatientComorbidityViewSet, basename="patient-comorbidity")
router.register("records/diagnoses", DiagnosisViewSet, basename="diagnosis")
router.register("records/metastatic-sites", MetastaticSiteRecordViewSet, basename="metastatic-site-record")
router.register("records/histopathologies", HistopathologyViewSet, basename="histopathology")

urlpatterns = [path("", include(router.urls))]
