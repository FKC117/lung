from rest_framework import serializers

from .models import ExtractionIssue, ExtractionRun, PrescriptionDocument, PrescriptionPage


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


class PrescriptionDocumentSerializer(serializers.ModelSerializer):
    pages = PrescriptionPageSerializer(many=True, read_only=True)
    extraction_runs = ExtractionRunSerializer(many=True, read_only=True)
    issues = ExtractionIssueSerializer(many=True, read_only=True)
    class Meta:
        model = PrescriptionDocument
        fields = ("id", "file", "original_filename", "sha256", "patient", "page_count", "status", "uploaded_by", "created_at", "processing_started_at", "processed_at", "pages", "extraction_runs", "issues")
        read_only_fields = ("original_filename", "sha256", "page_count", "status", "uploaded_by", "created_at", "processing_started_at", "processed_at", "pages", "extraction_runs", "issues")
