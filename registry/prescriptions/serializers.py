from rest_framework import serializers

from records.models import Patient
from .models import ExtractionIssue, ExtractionRun, PrescriptionDocument, PrescriptionPage, PrescriptionReview, PrescriptionReviewChange


class PrescriptionPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionPage
        fields = ("id", "page_number", "raw_text", "cleaned_text", "ocr_confidence", "image", "ocr_metadata")
        read_only_fields = fields


class ExtractionIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtractionIssue
        fields = ("id", "code", "severity", "message", "page_number", "details", "created_at")
        read_only_fields = fields


class ExtractionRunSerializer(serializers.ModelSerializer):
    issues = ExtractionIssueSerializer(many=True, read_only=True)
    class Meta:
        model = ExtractionRun
        fields = ("id", "schema_version", "prompt_version", "ai_model", "raw_response", "structured_data", "status", "error", "created_at", "completed_at", "issues")
        read_only_fields = fields


class PrescriptionReviewChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionReviewChange
        fields = ("id", "field_path", "previous_value", "new_value", "changed_by", "changed_at")
        read_only_fields = fields


class PrescriptionReviewSerializer(serializers.ModelSerializer):
    changes = PrescriptionReviewChangeSerializer(many=True, read_only=True)

    class Meta:
        model = PrescriptionReview
        fields = ("id", "selected_patient", "status", "reviewed_data", "notes", "assigned_to", "reviewed_by", "reviewed_at", "published_at", "published_by", "created_at", "updated_at", "changes")
        read_only_fields = ("status", "assigned_to", "reviewed_by", "reviewed_at", "published_at", "published_by", "created_at", "updated_at", "changes")


class PrescriptionReviewUpdateSerializer(serializers.Serializer):
    selected_patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.all(), required=False, allow_null=True)
    reviewed_data = serializers.JSONField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class PrescriptionDocumentSerializer(serializers.ModelSerializer):
    pages = PrescriptionPageSerializer(many=True, read_only=True)
    extraction_runs = ExtractionRunSerializer(many=True, read_only=True)
    issues = ExtractionIssueSerializer(many=True, read_only=True)
    review = PrescriptionReviewSerializer(read_only=True)
    class Meta:
        model = PrescriptionDocument
        fields = ("id", "file", "original_filename", "sha256", "patient", "page_count", "status", "uploaded_by", "created_at", "processing_started_at", "processed_at", "pages", "extraction_runs", "issues", "review")
        read_only_fields = ("original_filename", "sha256", "page_count", "status", "uploaded_by", "created_at", "processing_started_at", "processed_at", "pages", "extraction_runs", "issues")
