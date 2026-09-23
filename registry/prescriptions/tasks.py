from celery import shared_task

from prescriptions.models import PrescriptionBatchJob, PrescriptionDocument
from prescriptions.services.batch import sync_batch_job
from prescriptions.services.processing import process_document


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def process_prescription_document(self, document_id):
    """Run OCR and Gemini extraction outside the Django request process."""
    document = PrescriptionDocument.objects.get(pk=document_id)
    run = process_document(document)
    return {"document_id": document.pk, "run_id": run.pk, "status": run.status}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def sync_prescription_batch_job(self, batch_job_id):
    """Poll one Gemini Batch job and import review-only results when complete."""
    job = PrescriptionBatchJob.objects.get(pk=batch_job_id)
    job = sync_batch_job(job)
    return {"batch_job_id": job.pk, "status": job.status}
