import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from prescriptions.models import ExtractionIssue, PrescriptionBatchJob, PrescriptionDocument
from prescriptions.services.batch import sync_batch_job
from prescriptions.services.extraction import GeminiRateLimitError, GeminiStructuredOutputError
from prescriptions.services.processing import process_document


logger = logging.getLogger("celery.tasks")


def _gemini_retry_countdown(task, error):
    if error.retry_after_seconds:
        return min(error.retry_after_seconds, settings.PRESCRIPTION_GEMINI_RETRY_MAX_SECONDS)
    return min(
        settings.PRESCRIPTION_GEMINI_RETRY_BASE_SECONDS * (2 ** task.request.retries),
        settings.PRESCRIPTION_GEMINI_RETRY_MAX_SECONDS,
    )


def _mark_quota_retries_exhausted(document_id):
    document = PrescriptionDocument.objects.get(pk=document_id)
    document.status = PrescriptionDocument.Status.FAILED
    document.processed_at = timezone.now()
    document.save(update_fields=["status", "processed_at"])
    ExtractionIssue.objects.create(
        document=document,
        code="gemini_rate_limit",
        severity=ExtractionIssue.Severity.ERROR,
        message="Gemini quota remained exhausted after all scheduled retries. Retry this document after quota is available.",
    )


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    dont_autoretry_for=(GeminiRateLimitError, GeminiStructuredOutputError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    queue=settings.PRESCRIPTION_EXTRACTION_QUEUE,
    rate_limit=settings.PRESCRIPTION_GEMINI_RATE_LIMIT,
)
def process_prescription_document(self, document_id, quality_recovery=False):
    """Run OCR and Gemini extraction outside the Django request process."""
    logger.info("Prescription extraction started document_id=%s task_id=%s", document_id, self.request.id)
    try:
        document = PrescriptionDocument.objects.get(pk=document_id)
        run = process_document(
            document,
            retry_invalid_structured_output=not quality_recovery,
            quality_recovery=quality_recovery,
        )
    except GeminiRateLimitError as exc:
        retry_countdown = _gemini_retry_countdown(self, exc)
        if self.request.retries >= settings.PRESCRIPTION_GEMINI_MAX_RETRIES:
            _mark_quota_retries_exhausted(document_id)
            logger.error(
                "Gemini quota retries exhausted document_id=%s task_id=%s attempts=%s",
                document_id,
                self.request.id,
                self.request.retries + 1,
            )
            raise
        logger.warning(
            "Gemini quota reached document_id=%s task_id=%s retry_in_seconds=%s attempt=%s",
            document_id,
            self.request.id,
            retry_countdown,
            self.request.retries + 1,
        )
        raise self.retry(
            exc=exc,
            countdown=retry_countdown,
            max_retries=settings.PRESCRIPTION_GEMINI_MAX_RETRIES,
        )
    except GeminiStructuredOutputError as exc:
        # A structurally bad or demographics-only answer needs a different
        # prompt, not the same deterministic request again.
        logger.warning(
            "Gemini structured output invalid document_id=%s task_id=%s retry_in_seconds=%s attempt=%s",
            document_id,
            self.request.id,
            settings.PRESCRIPTION_GEMINI_OUTPUT_RETRY_SECONDS,
            self.request.retries + 1,
        )
        raise self.retry(
            exc=exc,
            args=(document_id, True),
            countdown=settings.PRESCRIPTION_GEMINI_OUTPUT_RETRY_SECONDS,
            max_retries=settings.PRESCRIPTION_GEMINI_OUTPUT_MAX_RETRIES,
        )
    except Exception:
        logger.exception("Prescription extraction failed document_id=%s task_id=%s", document_id, self.request.id)
        raise
    logger.info(
        "Prescription extraction finished document_id=%s run_id=%s status=%s task_id=%s",
        document.pk,
        run.pk,
        run.status,
        self.request.id,
    )
    return {"document_id": document.pk, "run_id": run.pk, "status": run.status}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def sync_prescription_batch_job(self, batch_job_id):
    """Poll one Gemini Batch job and import review-only results when complete."""
    logger.info("Prescription batch sync started batch_job_id=%s task_id=%s", batch_job_id, self.request.id)
    try:
        job = PrescriptionBatchJob.objects.get(pk=batch_job_id)
        job = sync_batch_job(job)
    except Exception:
        logger.exception("Prescription batch sync failed batch_job_id=%s task_id=%s", batch_job_id, self.request.id)
        raise
    logger.info(
        "Prescription batch sync finished batch_job_id=%s status=%s task_id=%s",
        job.pk,
        job.status,
        self.request.id,
    )
    return {"batch_job_id": job.pk, "status": job.status}
