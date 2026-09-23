import hashlib

from django.conf import settings
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class PrescriptionDocument(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PROCESSING = "processing", "Processing"
        READY_FOR_REVIEW = "ready_for_review", "Ready for review"
        FAILED = "failed", "Failed"

    file = models.FileField(upload_to="prescriptions/%Y/%m/%d")
    original_filename = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=64, unique=True, editable=False)
    patient = models.ForeignKey(
        "records.Patient", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="prescription_documents",
    )
    page_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.UPLOADED, db_index=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    @staticmethod
    def checksum(uploaded_file):
        digest = hashlib.sha256()
        for chunk in uploaded_file.chunks():
            digest.update(chunk)
        uploaded_file.seek(0)
        return digest.hexdigest()

    def __str__(self):
        return self.original_filename


class PrescriptionPage(models.Model):
    document = models.ForeignKey(PrescriptionDocument, on_delete=models.CASCADE, related_name="pages")
    page_number = models.PositiveIntegerField()
    raw_text = models.TextField(blank=True)
    cleaned_text = models.TextField(blank=True)
    ocr_confidence = models.FloatField(null=True, blank=True)
    image = models.ImageField(upload_to="prescription_pages/%Y/%m/%d", null=True, blank=True)
    ocr_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("page_number",)
        constraints = [models.UniqueConstraint(fields=["document", "page_number"], name="unique_prescription_document_page")]


class ExtractionRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    document = models.ForeignKey(PrescriptionDocument, on_delete=models.CASCADE, related_name="extraction_runs")
    schema_version = models.CharField(max_length=32, default="1.0")
    prompt_version = models.CharField(max_length=64, default="unconfigured")
    ai_model = models.CharField(max_length=128, blank=True)
    raw_response = models.TextField(blank=True)
    structured_data = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)


class ExtractionIssue(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"

    document = models.ForeignKey(PrescriptionDocument, on_delete=models.CASCADE, related_name="issues")
    extraction_run = models.ForeignKey(ExtractionRun, on_delete=models.CASCADE, related_name="issues", null=True, blank=True)
    code = models.CharField(max_length=64)
    severity = models.CharField(max_length=16, choices=Severity.choices, default=Severity.WARNING)
    message = models.TextField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)


class PrescriptionDrugAlias(models.Model):
    """A human-approved spelling or brand alias; never populated from extraction output."""
    alias = models.CharField(max_length=191, unique=True)
    drug = models.ForeignKey("options.TreatmentDrug", on_delete=models.PROTECT, related_name="prescription_aliases")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("alias",)

    def __str__(self):
        return f"{self.alias} → {self.drug}"


class PrescriptionReview(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In review"
        APPROVED = "approved", "Approved for publishing"
        REJECTED = "rejected", "Rejected"

    document = models.OneToOneField(PrescriptionDocument, on_delete=models.CASCADE, related_name="review")
    selected_patient = models.ForeignKey("records.Patient", on_delete=models.SET_NULL, null=True, blank=True, related_name="prescription_reviews")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True)
    reviewed_data = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_prescription_reviews")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="completed_prescription_reviews")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="published_prescription_reviews")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)


class PrescriptionReviewChange(models.Model):
    review = models.ForeignKey(PrescriptionReview, on_delete=models.CASCADE, related_name="changes")
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    field_path = models.CharField(max_length=255)
    previous_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-changed_at", "-id")

class RecordProvenance(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    record = GenericForeignKey("content_type", "object_id")
    document = models.ForeignKey(PrescriptionDocument, on_delete=models.PROTECT, related_name="published_provenance")
    extraction_run = models.ForeignKey(ExtractionRun, on_delete=models.PROTECT, null=True, blank=True)
    source_text = models.TextField(blank=True)
    source_page = models.PositiveIntegerField(null=True, blank=True)
    field_path = models.CharField(max_length=255, blank=True)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["content_type", "object_id"])]
