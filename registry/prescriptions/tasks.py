import logging

from celery import shared_task

from prescriptions.models import PrescriptionBatchJob, PrescriptionDocument
from prescriptions.services.batch import sync_batch_job
from prescriptions.services.processing import process_document


logger = logging.getLogger("celery.tasks")


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def process_prescription_document(self, document_id):
    """Run OCR and Gemini extraction outside the Django request process."""
    logger.info("Prescription extraction started document_id=%s task_id=%s", document_id, self.request.id)
    try:
        document = PrescriptionDocument.objects.get(pk=document_id)
        run = process_document(document)
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
