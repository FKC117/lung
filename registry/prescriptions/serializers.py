from rest_framework import serializers
from rest_framework.reverse import reverse

from records.models import Patient
from .services.draft_schema import validate_draft
from .services.option_resolver import validate_approval_readiness, validate_selected_resolutions
from .models import ExtractionIssue, ExtractionRun, PrescriptionBatchItem, PrescriptionBatchJob, PrescriptionDocument, PrescriptionPage, PrescriptionReview, PrescriptionReviewChange


class PrescriptionPageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    def get_image(self, obj):
        if not obj.image:
            return None
        return reverse(
            "prescription-document-page-image",
            kwargs={"pk": obj.document_id, "page_id": obj.pk},
            request=self.context.get("request"),
        )

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
        # raw_response is retained server-side for audit, but is not duplicated
        # into the routine review API because it can contain patient data.
        fields = ("id", "schema_version", "prompt_version", "ai_model", "structured_data", "status", "error", "created_at", "completed_at", "issues")
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

    def validate_reviewed_data(self, value):
        try:
            validate_draft(
                value,
                document_id=self.context.get("document_id"),
                check_database=True,
            )
            validate_selected_resolutions(value)
            if self.context.get("approval"):
                validate_approval_readiness(value)
        except Exception as exc:
            if hasattr(exc, "message_dict"):
                raise serializers.ValidationError(exc.message_dict) from exc
            if hasattr(exc, "messages"):
                raise serializers.ValidationError(exc.messages) from exc
            raise
        return value


class PrescriptionDocumentSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()
    pages = PrescriptionPageSerializer(many=True, read_only=True)
    extraction_runs = ExtractionRunSerializer(many=True, read_only=True)
    issues = ExtractionIssueSerializer(many=True, read_only=True)
    review = PrescriptionReviewSerializer(read_only=True)

    def get_file(self, obj):
        if not obj.file:
            return None
        return reverse(
            "prescription-document-source-file",
            kwargs={"pk": obj.pk},
            request=self.context.get("request"),
        )

    class Meta:
        model = PrescriptionDocument
        fields = ("id", "file", "original_filename", "sha256", "patient", "page_count", "status", "uploaded_by", "created_at", "processing_started_at", "processed_at", "pages", "extraction_runs", "issues", "review")
        read_only_fields = ("original_filename", "sha256", "page_count", "status", "uploaded_by", "created_at", "processing_started_at", "processed_at", "pages", "extraction_runs", "issues")


class PrescriptionBatchItemSerializer(serializers.ModelSerializer):
    document_name = serializers.CharField(source="document.original_filename", read_only=True)
    class Meta:
        model = PrescriptionBatchItem
        fields = ("id", "document", "document_name", "request_key", "status", "input_sha256", "error", "attempts", "completed_at")
        read_only_fields = fields


class PrescriptionBatchJobSerializer(serializers.ModelSerializer):
    items = PrescriptionBatchItemSerializer(many=True, read_only=True)
    class Meta:
        model = PrescriptionBatchJob
        fields = ("id", "display_name", "provider", "provider_job_name", "model_name", "schema_version", "prompt_version", "status", "submitted_by", "submitted_at", "completed_at", "error", "created_at", "updated_at", "items")
        read_only_fields = fields
