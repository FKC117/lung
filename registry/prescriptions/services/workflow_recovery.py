"""Operator recovery without changing extracted evidence or clinical records."""
from django.db import transaction
from django.utils import timezone
from prescriptions.models import PrescriptionWorkflowRun, PrescriptionDocument, ExtractionRun, LLMInvocation
from .workflow_state import WorkflowLeaseConflict


@transaction.atomic
def cancel_workflow(run_id):
    run = PrescriptionWorkflowRun.objects.select_for_update().get(pk=run_id)
    if run.status == "cancelled":
        return run
    if run.status in {"needs_review", "ready"}:
        raise WorkflowLeaseConflict("Completed review workflows cannot be cancelled.")
    # Revoke ownership before a provider response or checkpoint can commit.
    run.status = "cancelled"
    run.lease_owner = None
    run.lease_expires_at = None
    run.save(update_fields=["status", "lease_owner", "lease_expires_at", "updated_at"])
    PrescriptionDocument.objects.filter(pk=run.document_id, status=PrescriptionDocument.Status.PROCESSING).update(
        status=PrescriptionDocument.Status.FAILED, processed_at=timezone.now())
    # Pending evidence is retained; completed extraction is immutable.
    ExtractionRun.objects.filter(pk=run.versions.get("extraction_run_id"), status=ExtractionRun.Status.PENDING).update(
        status=ExtractionRun.Status.FAILED, completed_at=timezone.now(), error="Workflow cancelled by an operator.")
    return run


def workflow_status(run_id):
    run = PrescriptionWorkflowRun.objects.get(pk=run_id)
    budgets = {}
    for name in ("document_budget", "repair_budget"):
        accounting = run.versions.get(name)
        if isinstance(accounting, dict):
            budgets[name] = {key: accounting[key] for key in ("attempts_reserved", "token_units_reserved", "deadline_at") if key in accounting}
    extraction = ExtractionRun.objects.filter(pk=run.versions.get("extraction_run_id")).first()
    stages = {"local_complete": bool(extraction and extraction.structured_data.get("workflow_local_complete")),
              "provider_complete": bool(extraction and extraction.structured_data.get("workflow_provider_complete")),
              "extraction_complete": bool(extraction and extraction.status == "completed"),
              "repair_proposal_available": run.checkpoints.filter(namespace="repair-proposal").exists()}
    audit = {}
    ids = list(run.versions.get("repair_invocations", {}).values())
    invocations = LLMInvocation.objects.filter(pk__in=ids) if run.versions.get("kind") == "targeted_repair" else LLMInvocation.objects.filter(extraction_run_id=run.versions.get("extraction_run_id")) if run.versions.get("extraction_run_id") else LLMInvocation.objects.none()
    for status in invocations.values_list("status", flat=True):
        audit[status] = audit.get(status, 0) + 1
    return {"workflow_id": str(run.pk), "document_id": run.document_id, "status": run.status,
            "lease_active": bool(run.lease_owner and run.lease_expires_at and run.lease_expires_at > timezone.now()),
            "lease_expires_at": run.lease_expires_at.isoformat() if run.lease_expires_at else None,
            "extraction_run_id": run.versions.get("extraction_run_id"), "checkpoint_count": run.checkpoints.count(), "stage_status": stages, "provider_attempts": audit, "budgets": budgets}


@transaction.atomic
def queue_failed_extraction_resume(run_id):
    from django.conf import settings
    run=PrescriptionWorkflowRun.objects.select_for_update().select_related("document").get(pk=run_id)
    if not settings.PRESCRIPTION_AGENTIC_EXTRACTION_ENABLED or run.versions.get("kind") != "extraction":
        raise WorkflowLeaseConflict("Resume requires an enabled existing extraction workflow.")
    if run.status != "failed" or (run.lease_owner and run.lease_expires_at and run.lease_expires_at > timezone.now()):
        raise WorkflowLeaseConflict("Only an unleased failed workflow can be resumed; scheduled quota waits remain owned by Celery.")
    if run.document_sha256 != run.document.sha256:
        raise WorkflowLeaseConflict("The document source changed; this identity cannot resume.")
    from prescriptions.tasks import resume_prescription_extraction
    run.status="queued"
    run.save(update_fields=["status","updated_at"])
    result=resume_prescription_extraction.delay(str(run.pk))
    return str(result.id)
