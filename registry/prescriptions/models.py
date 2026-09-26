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


class PrescriptionBatchJob(models.Model):
    """An auditable provider batch; documents are never published by a batch."""
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    display_name = models.CharField(max_length=160)
    provider = models.CharField(max_length=32, default="gemini")
    provider_job_name = models.CharField(max_length=255, blank=True, db_index=True)
    model_name = models.CharField(max_length=128)
    schema_version = models.CharField(max_length=32, default="2.0")
    prompt_version = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="submitted_prescription_batches")
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)


class PrescriptionBatchItem(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    batch_job = models.ForeignKey(PrescriptionBatchJob, on_delete=models.CASCADE, related_name="items")
    document = models.ForeignKey(PrescriptionDocument, on_delete=models.PROTECT, related_name="batch_items")
    request_key = models.CharField(max_length=128)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED, db_index=True)
    input_sha256 = models.CharField(max_length=64)
    raw_response = models.TextField(blank=True)
    error = models.TextField(blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("id",)
        constraints = [
            models.UniqueConstraint(fields=["batch_job", "document"], name="unique_prescription_batch_document"),
            models.UniqueConstraint(fields=["batch_job", "request_key"], name="unique_prescription_batch_request_key"),
        ]


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


class PrescriptionPublicationObservation(models.Model):
    """Durable idempotency key for one reviewed draft observation."""
    review = models.ForeignKey(PrescriptionReview, on_delete=models.CASCADE, related_name="publication_observations")
    draft_observation_temp_id = models.CharField(max_length=128)
    observation = models.OneToOneField("records.ClinicalObservation", on_delete=models.PROTECT, related_name="prescription_publication_mapping")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["review", "draft_observation_temp_id"], name="unique_review_draft_observation")]

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
