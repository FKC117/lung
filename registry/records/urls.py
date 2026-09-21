from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import (
    CancerMarkerResultViewSet,
    ClinicalObservationViewSet,
    ClinicalTNMStagingViewSet,
    DiagnosisViewSet,
    HistopathologyViewSet,
    IHCResultViewSet,
    IRECISTAssessmentViewSet,
    MetastaticSiteRecordViewSet,
    MolecularTestResultViewSet,
    MolecularTestViewSet,
    PathologicalStagingResultViewSet,
    PathologicalResponseAssessmentViewSet,
    PathologicalTNMStagingViewSet,
    PatientAnthropometryViewSet,
    PatientComorbidityViewSet,
    PatientViewSet,
    RECIST11AssessmentViewSet,
    TreatmentAdministrationViewSet,
    TreatmentCourseViewSet,
)

router = DefaultRouter()
router.register("records/patients", PatientViewSet, basename="patient")
router.register("records/observations", ClinicalObservationViewSet, basename="clinical-observation")
router.register("records/anthropometries", PatientAnthropometryViewSet, basename="patient-anthropometry")
router.register("records/comorbidities", PatientComorbidityViewSet, basename="patient-comorbidity")
router.register("records/diagnoses", DiagnosisViewSet, basename="diagnosis")
router.register("records/metastatic-sites", MetastaticSiteRecordViewSet, basename="metastatic-site-record")
router.register("records/histopathologies", HistopathologyViewSet, basename="histopathology")
router.register("records/cancer-marker-results", CancerMarkerResultViewSet, basename="cancer-marker-result")
router.register("records/treatment-courses", TreatmentCourseViewSet, basename="treatment-course")
router.register("records/treatment-administrations", TreatmentAdministrationViewSet, basename="treatment-administration")
router.register("records/recist11-assessments", RECIST11AssessmentViewSet, basename="recist11-assessment")
router.register("records/irecist-assessments", IRECISTAssessmentViewSet, basename="irecist-assessment")
router.register("records/pathological-response-assessments", PathologicalResponseAssessmentViewSet, basename="pathological-response-assessment")
router.register("records/ihc-results", IHCResultViewSet, basename="ihc-result")
router.register("records/pathological-staging-results", PathologicalStagingResultViewSet, basename="pathological-staging-result")
router.register("records/clinical-tnm-stagings", ClinicalTNMStagingViewSet, basename="clinical-tnm-staging")
router.register("records/pathological-tnm-stagings", PathologicalTNMStagingViewSet, basename="pathological-tnm-staging")
router.register("records/molecular-tests", MolecularTestViewSet, basename="molecular-test")
router.register("records/molecular-test-results", MolecularTestResultViewSet, basename="molecular-test-result")

urlpatterns = [path("", include(router.urls))]
