"""Bounded orchestration state and leases, independent of clinical persistence."""
from datetime import timedelta
from typing import Literal, TypedDict
from uuid import uuid4
from django.db import transaction
from django.utils import timezone
from prescriptions.models import PrescriptionWorkflowRun


WorkflowStatus = Literal["queued", "running", "waiting_provider", "needs_review", "ready", "failed", "cancelled"]


class PrescriptionWorkflowState(TypedDict, total=False):
    run_id: str
    document_id: int
    document_sha256: str
    schema_version: str
    prompt_version: str
    model_name: str
    extraction_run_id: int
    page_artifact_ids: list[int]
    catalog_fingerprints: dict[str, str]
    reviewer_revision: int
    issue_dispositions: list[dict]
    stage_results: dict[str, dict]
    extraction_attempts: int
    repair_attempts: int
    input_tokens: int
    output_tokens: int
    started_at: str
    deadline_at: str
    status: WorkflowStatus


class WorkflowLeaseConflict(RuntimeError):
    pass


@transaction.atomic
def acquire_workflow_lease(run_id, *, seconds=300):
    if not 1 <= seconds <= 3600:
        raise ValueError("Workflow lease duration must be between 1 and 3600 seconds.")
    run = PrescriptionWorkflowRun.objects.select_for_update().select_related("document").get(pk=run_id)
    now = timezone.now()
    if run.status in {"cancelled", "ready"}:
        raise WorkflowLeaseConflict("This workflow is no longer executable.")
    if run.document_sha256 != run.document.sha256:
        raise WorkflowLeaseConflict("Document revision changed; create a new workflow run.")
    if run.lease_owner and run.lease_expires_at and run.lease_expires_at > now:
        raise WorkflowLeaseConflict("Another worker owns this workflow.")
    owner = uuid4()
    run.lease_owner = owner
    run.lease_expires_at = now + timedelta(seconds=seconds)
    run.status = "running"
    run.save(update_fields=["lease_owner", "lease_expires_at", "status", "updated_at"])
    return owner


@transaction.atomic
def release_workflow_lease(run_id, owner, *, status="needs_review"):
    if status not in {"waiting_provider", "needs_review", "ready", "failed", "cancelled"}:
        raise ValueError("Invalid workflow completion status.")
    run = PrescriptionWorkflowRun.objects.select_for_update().get(pk=run_id)
    if run.lease_owner != owner:
        raise WorkflowLeaseConflict("Workflow lease ownership changed.")
    run.lease_owner = None
    run.lease_expires_at = None
    run.status = status
    run.save(update_fields=["lease_owner", "lease_expires_at", "status", "updated_at"])
