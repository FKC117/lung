"""Authenticated CRUD API for registry patient records."""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import CancerMarkerResult, ClinicalObservation, ClinicalTNMStaging, Diagnosis, DiseaseProgressionRecord, Histopathology, IHCResult, IRECISTAssessment, MetastaticSiteRecord, MolecularTest, MolecularTestResult, PathologicalResponseAssessment, PathologicalStagingResult, PathologicalTNMStaging, Patient, PatientAnthropometry, PatientComorbidity, RadiotherapyCourse, RECIST11Assessment, SurgeryRecord, SurvivalFollowUp, TreatmentAdministration, TreatmentCourse
from .serializers import RadiotherapyCourseSerializer, TreatmentAdministrationSerializer, TreatmentCourseSerializer, build_assessment_serializer, build_outcome_serializer, build_record_serializer
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


class CancerMarkerResultViewSet(RecordModelViewSet):
    queryset = CancerMarkerResult.objects.select_related("observation__patient", "marker").all()
    serializer_class = build_record_serializer(CancerMarkerResult)


class TreatmentCourseViewSet(RecordModelViewSet):
    queryset = TreatmentCourse.objects.select_related("observation__patient", "modality", "line_of_treatment", "protocol").all()
    serializer_class = TreatmentCourseSerializer


class TreatmentAdministrationViewSet(RecordModelViewSet):
    queryset = TreatmentAdministration.objects.select_related("treatment_course", "observation__patient", "drug").all()
    serializer_class = TreatmentAdministrationSerializer


class SurgeryRecordViewSet(RecordModelViewSet):
    queryset = SurgeryRecord.objects.select_related(
        "observation__patient", "modality", "laterality"
    ).all()
    serializer_class = build_record_serializer(SurgeryRecord)


class RadiotherapyCourseViewSet(RecordModelViewSet):
    queryset = RadiotherapyCourse.objects.select_related(
        "observation__patient", "site", "intent", "modality"
    ).all()
    serializer_class = RadiotherapyCourseSerializer


class RECIST11AssessmentViewSet(RecordModelViewSet):
    queryset = RECIST11Assessment.objects.select_related("observation__patient", "treatment_course", "target_lesion", "non_target_lesion", "new_lesion", "overall_response", "estimation_method").all()
    serializer_class = build_assessment_serializer(RECIST11Assessment)


class IRECISTAssessmentViewSet(RecordModelViewSet):
    queryset = IRECISTAssessment.objects.select_related("observation__patient", "treatment_course", "target_lesion", "non_target_lesion", "new_lesion", "overall_response", "estimation_method").all()
    serializer_class = build_assessment_serializer(IRECISTAssessment)


class PathologicalResponseAssessmentViewSet(RecordModelViewSet):
    queryset = PathologicalResponseAssessment.objects.select_related("observation__patient", "treatment_course", "response_category", "tumor_regression_grade", "estimation_method").all()
    serializer_class = build_assessment_serializer(PathologicalResponseAssessment)


class DiseaseProgressionRecordViewSet(RecordModelViewSet):
    queryset = DiseaseProgressionRecord.objects.select_related("observation__patient", "treatment_course", "status", "estimation_method").prefetch_related("progression_sites").all()
    serializer_class = build_outcome_serializer(DiseaseProgressionRecord)


class SurvivalFollowUpViewSet(RecordModelViewSet):
    queryset = SurvivalFollowUp.objects.select_related("observation__patient", "status").all()
    serializer_class = build_outcome_serializer(SurvivalFollowUp)


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

    def _ensure_mutable(self, molecular_test):
        if molecular_test.status == MolecularTest.Status.COMPLETED:
            raise ValidationError("A finalized molecular test cannot be modified.")

    @staticmethod
    def _reject_direct_completion(serializer):
        if serializer.validated_data.get("status") == MolecularTest.Status.COMPLETED:
            raise ValidationError("Use the finalize endpoint to complete a molecular test.")

    def perform_create(self, serializer):
        self._reject_direct_completion(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self._ensure_mutable(self.get_object())
        self._reject_direct_completion(serializer)
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_mutable(instance)
        instance.delete()

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

    @staticmethod
    def _ensure_test_mutable(molecular_test):
        if molecular_test.status == MolecularTest.Status.COMPLETED:
            raise ValidationError("Results for a finalized molecular test cannot be modified.")

    def perform_create(self, serializer):
        self._ensure_test_mutable(serializer.validated_data["molecular_test"])
        serializer.save()

    def perform_update(self, serializer):
        self._ensure_test_mutable(self.get_object().molecular_test)
        self._ensure_test_mutable(serializer.validated_data.get("molecular_test", self.get_object().molecular_test))
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_test_mutable(instance.molecular_test)
        instance.delete()
