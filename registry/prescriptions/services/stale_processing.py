"""Explicit operator reconciliation; no provider dispatch or clinical writes."""
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from prescriptions.models import PrescriptionDocument, ExtractionRun
from .intake_draft import build_intake_draft


@transaction.atomic
def reconcile_stale_processing(document_id, *, apply=False, minimum_age_seconds=3600):
    if minimum_age_seconds < 3600:
        raise ValueError("Reconciliation requires at least a one-hour stale threshold.")
    document = PrescriptionDocument.objects.select_for_update().get(pk=document_id)
    cutoff = timezone.now() - timedelta(seconds=minimum_age_seconds)
    if document.status != "processing" or not document.processing_started_at or document.processing_started_at > cutoff:
        raise ValueError("The document is not an old processing request.")
    if document.workflow_runs.exclude(status__in=["failed", "cancelled", "needs_review", "ready"]).exists():
        raise ValueError("A runnable workflow still owns this document; inspect or resume it instead.")
    latest = document.extraction_runs.filter(status="completed").first()
    pending = list(document.extraction_runs.select_for_update().filter(status="pending"))
    if not latest or any(run.created_at > latest.created_at or run.created_at > cutoff for run in pending):
        raise ValueError("A newer completed extraction is required before reconciling unfinished evidence.")
    # Verify the recovered source remains usable, without modifying its original data.
    source = latest.structured_data
    try:
        build_intake_draft(source.get("canonical_draft", source), document_id=document.pk, pages=list(document.pages.all()))
    except (ValidationError, ValueError, TypeError) as exc:
        raise ValueError("The recovered source cannot form a valid review draft.") from exc
    if apply:
        for run in pending:
            run.status = ExtractionRun.Status.FAILED
            run.error = "Interrupted extraction reconciled by an operator; a newer completed extraction is available."
            run.completed_at = timezone.now()
            run.save(update_fields=["status", "error", "completed_at"])
        document.status = PrescriptionDocument.Status.READY_FOR_REVIEW
        document.processing_started_at = None
        document.processed_at = timezone.now()
        document.save(update_fields=["status", "processing_started_at", "processed_at"])
    return {"document_id": document.pk, "completed_extraction_run_id": latest.pk,
            "interrupted_run_ids": [run.pk for run in pending], "applied": apply}
