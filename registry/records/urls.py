from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import (
    ClinicalObservationViewSet,
    ClinicalTNMStagingViewSet,
    DiagnosisViewSet,
    HistopathologyViewSet,
    IHCResultViewSet,
    MetastaticSiteRecordViewSet,
    MolecularTestResultViewSet,
    MolecularTestViewSet,
    PathologicalStagingResultViewSet,
    PathologicalTNMStagingViewSet,
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
router.register("records/ihc-results", IHCResultViewSet, basename="ihc-result")
router.register("records/pathological-staging-results", PathologicalStagingResultViewSet, basename="pathological-staging-result")
router.register("records/clinical-tnm-stagings", ClinicalTNMStagingViewSet, basename="clinical-tnm-staging")
router.register("records/pathological-tnm-stagings", PathologicalTNMStagingViewSet, basename="pathological-tnm-staging")
router.register("records/molecular-tests", MolecularTestViewSet, basename="molecular-test")
router.register("records/molecular-test-results", MolecularTestResultViewSet, basename="molecular-test-result")

urlpatterns = [path("", include(router.urls))]
