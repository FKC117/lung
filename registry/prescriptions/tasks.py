import logging
import random

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from prescriptions.models import ExtractionIssue, PrescriptionBatchJob, PrescriptionDocument
from prescriptions.services.batch import sync_batch_job
from prescriptions.services.extraction import GeminiRateLimitError, GeminiStructuredOutputError
from prescriptions.services.processing import process_document
from prescriptions.services.workflow_state import WorkflowLeaseConflict


logger = logging.getLogger("celery.tasks")


@shared_task(queue=settings.PRESCRIPTION_EXTRACTION_QUEUE)
def map_prescription_workflow(workflow_run_id):
    """Explicit opt-in mapping task; no provider calls or clinical publication."""
    from prescriptions.services.mapping_graph import execute_mapping_workflow
    result = execute_mapping_workflow(workflow_run_id)
    return {"workflow_run_id": str(workflow_run_id), "review_id": result["review_id"], "status": result["status"]}


def _gemini_retry_countdown(task, error):
    if error.retry_after_seconds:
        return error.retry_after_seconds
    base = min(
        settings.PRESCRIPTION_GEMINI_RETRY_BASE_SECONDS * (2 ** task.request.retries),
        settings.PRESCRIPTION_GEMINI_RETRY_MAX_SECONDS,
    )
    return base + random.randint(0, max(1, base // 5))


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
    dont_autoretry_for=(GeminiRateLimitError, GeminiStructuredOutputError, WorkflowLeaseConflict),
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
        if settings.PRESCRIPTION_AGENTIC_EXTRACTION_ENABLED:
            from prescriptions.services.extraction_graph import prepare_extraction_workflow, execute_extraction_workflow
            workflow = prepare_extraction_workflow(document, task_id=self.request.id)
            run = execute_extraction_workflow(workflow.pk, quality_recovery=quality_recovery)
        else:
            run = process_document(
                document,
                retry_invalid_structured_output=not quality_recovery,
                quality_recovery=quality_recovery,
            )
    except GeminiRateLimitError as exc:
        retry_countdown = _gemini_retry_countdown(self, exc)
        if self.request.retries >= settings.PRESCRIPTION_GEMINI_MAX_RETRIES:
            if settings.PRESCRIPTION_AGENTIC_EXTRACTION_ENABLED:
                run = execute_extraction_workflow(workflow.pk, quality_recovery=quality_recovery,
                    provider_fallback_reason="Gemini quota retries exhausted. Saved local evidence is available; provider enrichment remains unresolved.")
                return {"document_id": document_id, "run_id": run.pk, "status": run.status}
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


@shared_task(queue=settings.PRESCRIPTION_EXTRACTION_QUEUE)
def repair_prescription_section(review_id, collection, record_id, field_names, source_sections):
    """Bounded explicit repair task; no recursive retry, review edit or publication."""
    from django.core.exceptions import ValidationError
    from prescriptions.services.repair_graph import prepare_saved_repair, execute_repair_graph
    from prescriptions.services.workflow_state import acquire_workflow_lease, release_workflow_lease
    from prescriptions.services.provider_data_policy import ProviderDataPolicyError
    from prescriptions.services.repair_budget import RepairBudgetExhausted
    if not settings.PRESCRIPTION_REPAIR_ENABLED:
        return {"review_id": review_id, "status": "disabled"}
    run, request = prepare_saved_repair(review_id, collection=collection, record_id=record_id, field_names=field_names, source_sections=source_sections)
    owner = acquire_workflow_lease(run.pk, seconds=3600)
    try:
        execute_repair_graph({"run_id": str(run.pk), "owner": str(owner), "review_id": review_id, "request": request})
    except (ValidationError, ValueError, ProviderDataPolicyError, RepairBudgetExhausted, GeminiRateLimitError):
        release_workflow_lease(run.pk, owner, status="needs_review")
        return {"review_id": review_id, "workflow_run_id": str(run.pk), "status": "exception_draft"}
    except Exception:
        release_workflow_lease(run.pk, owner, status="failed")
        raise
    release_workflow_lease(run.pk, owner, status="needs_review")
    return {"review_id": review_id, "workflow_run_id": str(run.pk), "status": "proposal_available"}


@shared_task(bind=True, queue=settings.PRESCRIPTION_EXTRACTION_QUEUE)
def resume_prescription_extraction(self, workflow_run_id, quality_recovery=False):
    """Resume the saved identity; Celery remains the sole delayed retry owner."""
    from prescriptions.services.extraction_graph import execute_extraction_workflow
    if not settings.PRESCRIPTION_AGENTIC_EXTRACTION_ENABLED:
        raise ValueError("Agentic extraction is disabled.")
    try:
        run=execute_extraction_workflow(workflow_run_id, quality_recovery=quality_recovery)
    except GeminiRateLimitError as exc:
        if self.request.retries >= settings.PRESCRIPTION_GEMINI_MAX_RETRIES:
            run=execute_extraction_workflow(workflow_run_id, quality_recovery=quality_recovery,
                provider_fallback_reason="Resumed provider retries exhausted; saved local evidence remains available for review.")
        else:
            raise self.retry(exc=exc, countdown=_gemini_retry_countdown(self,exc), max_retries=settings.PRESCRIPTION_GEMINI_MAX_RETRIES)
    except GeminiStructuredOutputError as exc:
        if self.request.retries >= settings.PRESCRIPTION_GEMINI_OUTPUT_MAX_RETRIES:
            run=execute_extraction_workflow(workflow_run_id, quality_recovery=True,
                provider_fallback_reason="Resumed structured-output retries exhausted; saved local evidence remains available for review.")
        else:
            raise self.retry(exc=exc,args=(workflow_run_id,True), countdown=settings.PRESCRIPTION_GEMINI_OUTPUT_RETRY_SECONDS,max_retries=settings.PRESCRIPTION_GEMINI_OUTPUT_MAX_RETRIES)
    return {"workflow_run_id":str(workflow_run_id),"extraction_run_id":run.pk,"status":run.status}
