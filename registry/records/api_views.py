"""Authenticated CRUD API for registry patient records."""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import ClinicalObservation, ClinicalTNMStaging, Diagnosis, Histopathology, IHCResult, MetastaticSiteRecord, MolecularTest, MolecularTestResult, PathologicalStagingResult, PathologicalTNMStaging, Patient, PatientAnthropometry, PatientComorbidity
from .serializers import build_record_serializer
from .services.molecular import finalize_molecular_test


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

    @action(detail=True, methods=["post"])
    def finalize(self, request, pk=None):
        """Validate and finalize a molecular test through the domain service."""
        molecular_test = self.get_object()

        try:
            result = finalize_molecular_test(molecular_test.pk)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)

        return Response(
            {
                "test": self.get_serializer(result["test"]).data,
                "created_negatives": result["created_negatives"],
                "already_completed": result["already_completed"],
            },
            status=status.HTTP_200_OK,
        )


class MolecularTestResultViewSet(RecordModelViewSet):
    queryset = MolecularTestResult.objects.select_related("molecular_test__observation__patient", "panel_target", "gene", "exon", "alteration_type", "result", "partner_gene", "clinical_significance").all()
    serializer_class = build_record_serializer(MolecularTestResult)
