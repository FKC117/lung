"""Authenticated CRUD API for registry patient records."""

from rest_framework import permissions, viewsets
from rest_framework.pagination import PageNumberPagination

from .models import ClinicalObservation, ClinicalTNMStaging, Diagnosis, Histopathology, IHCResult, MetastaticSiteRecord, MolecularTest, MolecularTestResult, PathologicalStagingResult, PathologicalTNMStaging, Patient, PatientAnthropometry, PatientComorbidity
from .serializers import build_record_serializer


class RecordPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class RecordModelViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = RecordPagination


class PatientViewSet(RecordModelViewSet):
    queryset = Patient.objects.select_related("sex", "district", "thana", "type_of_patient").all()
    serializer_class = build_record_serializer(Patient)


class ClinicalObservationViewSet(RecordModelViewSet):
    queryset = ClinicalObservation.objects.select_related("patient", "doctor", "center", "published_by").all()
    serializer_class = build_record_serializer(ClinicalObservation)


class PatientAnthropometryViewSet(RecordModelViewSet):
    queryset = PatientAnthropometry.objects.select_related("observation__patient").all()
    serializer_class = build_record_serializer(PatientAnthropometry)


class PatientComorbidityViewSet(RecordModelViewSet):
    queryset = PatientComorbidity.objects.select_related("observation__patient", "comorbidity").all()
    serializer_class = build_record_serializer(PatientComorbidity)


class DiagnosisViewSet(RecordModelViewSet):
    queryset = Diagnosis.objects.select_related("observation__patient", "disease_group", "disease_subgroup", "primary_site", "laterality").all()
    serializer_class = build_record_serializer(Diagnosis)


class MetastaticSiteRecordViewSet(RecordModelViewSet):
    queryset = MetastaticSiteRecord.objects.select_related("diagnosis__observation__patient", "site").all()
    serializer_class = build_record_serializer(MetastaticSiteRecord)


class HistopathologyViewSet(RecordModelViewSet):
    queryset = Histopathology.objects.select_related("observation__patient", "histopathology_details", "histopathology_type", "histopathology_site", "histopathology_grade").all()
    serializer_class = build_record_serializer(Histopathology)


class IHCResultViewSet(RecordModelViewSet):
    queryset = IHCResult.objects.select_related("observation__patient", "marker", "result").all()
    serializer_class = build_record_serializer(IHCResult)


class PathologicalStagingResultViewSet(RecordModelViewSet):
    queryset = PathologicalStagingResult.objects.select_related("observation__patient", "feature", "result").all()
    serializer_class = build_record_serializer(PathologicalStagingResult)


class ClinicalTNMStagingViewSet(RecordModelViewSet):
    queryset = ClinicalTNMStaging.objects.select_related("observation__patient", "t", "n", "m", "stage").all()
    serializer_class = build_record_serializer(ClinicalTNMStaging)


class PathologicalTNMStagingViewSet(RecordModelViewSet):
    queryset = PathologicalTNMStaging.objects.select_related("observation__patient", "t", "n", "m", "stage").all()
    serializer_class = build_record_serializer(PathologicalTNMStaging)


class MolecularTestViewSet(RecordModelViewSet):
    queryset = MolecularTest.objects.select_related("observation__patient", "panel_version", "method", "specimen").all()
    serializer_class = build_record_serializer(MolecularTest)


class MolecularTestResultViewSet(RecordModelViewSet):
    queryset = MolecularTestResult.objects.select_related("molecular_test__observation__patient", "panel_target", "gene", "exon", "alteration_type", "result", "partner_gene", "clinical_significance").all()
    serializer_class = build_record_serializer(MolecularTestResult)
