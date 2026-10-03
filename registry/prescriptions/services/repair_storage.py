"""Private append-only repair artifacts using existing binary checkpoint storage."""
import json
from datetime import datetime
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from prescriptions.models import PrescriptionWorkflowRun, PrescriptionWorkflowCheckpoint, PrescriptionReview, PrescriptionDocument
from .repair_budget import reserve_repair_attempt
from .repair_contract import validate_repair_proposal, _record
from .workflow_state import WorkflowLeaseConflict


def _locked(run_id, owner, review_id):
    run = PrescriptionWorkflowRun.objects.select_for_update().get(pk=run_id)
    if run.versions.get("kind") != "targeted_repair" or str(run.lease_owner) != str(owner) or not run.lease_expires_at or run.lease_expires_at <= timezone.now() or run.status != "running":
        raise WorkflowLeaseConflict("Repair writer requires its active dedicated workflow lease.")
    PrescriptionDocument.objects.select_for_update().get(pk=run.document_id)
    review = PrescriptionReview.objects.select_for_update().get(pk=review_id)
    if review.document_id != run.document_id or review.document.sha256 != run.document_sha256 or review.published_at or review.status not in {"draft", "in_review"}:
        raise ValidationError({"repair": "Repair cannot change approved, published or unrelated reviews."})
    return run, review


def _append(run, identity, namespace, value):
    payload = json.dumps(value, sort_keys=True).encode()
    row, created = PrescriptionWorkflowCheckpoint.objects.get_or_create(run=run, namespace=namespace, checkpoint_id=identity,
        defaults={"payload_type": "json", "payload": payload, "metadata_type": "json", "metadata": b"{}"})
    if not created and bytes(row.payload) != payload:
        raise ValidationError({"repair": "Immutable repair artifact identity cannot be overwritten."})
    return row


@transaction.atomic
def reserve_saved_repair(run_id, owner, review_id, request, *, limits, input_bytes, max_output_tokens):
    run, review = _locked(run_id, owner, review_id)
    # Validate the original snapshot and current saved revision before admission.
    # Snapshot validation is also enforced when the provider proposal returns.
    import hashlib
    snapshot = {key: value for key, value in request.items() if key != "request_sha256"}
    if hashlib.sha256(json.dumps(snapshot, sort_keys=True, default=str).encode()).hexdigest() != request.get("request_sha256"):
        raise ValidationError({"repair": "Repair snapshot changed."})
    if request["review_revision"] != review.revision or request["document_id"] != run.document_id or request["document_sha256"] != run.document_sha256:
        raise ValidationError({"repair": "Repair source or saved revision changed."})
    _, record = _record(review.reviewed_data, request["collection"], request["record_id"])
    if record["state"] == "edited" or any(record["values"].get(key) != value for key, value in request["original_values"].items()):
        raise ValidationError({"repair": "Reviewer-owned values are protected before dispatch."})
    # The document admission lock is acquired before the review in _locked.
    if PrescriptionWorkflowRun.objects.filter(document_id=run.document_id, versions__kind="targeted_repair", versions__has_key="repair_budget").exclude(pk=run.pk).exists():
        raise ValidationError({"repair": "Resume the document's existing repair workflow; a new identity cannot reset its budget."})
    accounting = reserve_repair_attempt(run.versions.get("repair_budget"), limits=limits, request_sha256=request["request_sha256"], input_bytes=input_bytes, max_output_tokens=max_output_tokens, now=timezone.now())
    _append(run, request["request_sha256"], "repair-request", {"review_id": review.pk, "request": request})
    run.versions = {**run.versions, "repair_budget": accounting}
    run.save(update_fields=["versions", "updated_at"])
    return accounting


@transaction.atomic
def store_saved_proposal(run_id, owner, review_id, request_sha256, payload):
    run, review = _locked(run_id, owner, review_id)
    row = PrescriptionWorkflowCheckpoint.objects.get(run=run, namespace="repair-request", checkpoint_id=request_sha256)
    saved = json.loads(bytes(row.payload))
    if saved["review_id"] != review.pk:
        raise ValidationError({"repair": "Repair reservation belongs to another review."})
    accounting = run.versions.get("repair_budget", {})
    if request_sha256 not in accounting.get("requests", []) or timezone.now() >= datetime.fromisoformat(accounting["deadline_at"]):
        raise ValidationError({"repair": "Repair reservation is missing or its deadline expired; retain the existing draft."})
    proposal = validate_repair_proposal(saved["request"], payload, current_draft=review.reviewed_data, current_revision=review.revision, document_sha256=run.document_sha256)
    _append(run, request_sha256, "repair-proposal", proposal)
    return proposal
