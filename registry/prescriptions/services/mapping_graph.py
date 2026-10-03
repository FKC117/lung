"""Durable mapping of completed extraction artifacts into a review-only draft.

This first graph deliberately has no provider call or publication node. Existing
OCR/Gemini tasks still own extraction until quota/replay integration is verified.
"""
import json
from hashlib import sha256
from typing import TypedDict
from types import SimpleNamespace
from django.db import transaction, connections
from django.utils import timezone
from langgraph.graph import StateGraph, START, END
from .stage_audit import audited_stage
from prescriptions.models import ExtractionRun, PrescriptionDocument, PrescriptionReview, PrescriptionWorkflowRun
from prescriptions.services.checkpoint import DjangoCheckpointSaver
from prescriptions.services.draft_schema import normalize_extraction, validate_draft
from prescriptions.services.draft_evidence import validate_source_evidence
from prescriptions.services.option_resolver import resolve_draft_options, validate_selected_resolutions
from prescriptions.services.readiness import mark_ready_records
from prescriptions.services.workflow_state import PrescriptionWorkflowState, acquire_workflow_lease, release_workflow_lease


def artifact_hash(value):
    return sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


class MappingState(PrescriptionWorkflowState, total=False):
    draft: dict
    review_id: int
    review_preserved: bool


def prepare_mapping_workflow(extraction_run):
    if extraction_run.status != ExtractionRun.Status.COMPLETED:
        raise ValueError("Only a completed extraction can enter mapping.")
    return PrescriptionWorkflowRun.objects.create(
        document=extraction_run.document, document_sha256=extraction_run.document.sha256,
        versions={"schema": "prescription-fields-1", "extraction_run_id": extraction_run.pk,
                  "source_sha256": artifact_hash(extraction_run.structured_data),
                  "prompt": extraction_run.prompt_version, "model": extraction_run.ai_model})


def _source(state):
    run = PrescriptionWorkflowRun.objects.select_related("document").get(pk=state["run_id"])
    extraction = ExtractionRun.objects.get(pk=run.versions["extraction_run_id"], document=run.document)
    if run.document_sha256 != run.document.sha256 or artifact_hash(extraction.structured_data) != run.versions["source_sha256"]:
        raise ValueError("Source artifact changed; create a new mapping workflow.")
    return run, extraction


def _normalize(state):
    try:
        run, extraction = _source(state)
        draft = normalize_extraction(extraction.structured_data, document_id=run.document_id, linked_patient_id=run.document.patient_id)
        return {"draft": draft, "status": "running"}
    finally:
        connections.close_all()


def _resolve(state):
    try:
        return {"draft": resolve_draft_options(state["draft"])}
    finally:
        connections.close_all()


def _validate(state):
    try:
        run, extraction = _source(state)
        draft = state["draft"]
        snapshot = extraction.structured_data.get("source_page_artifact", {})
        pages = [SimpleNamespace(**page) for page in snapshot["pages"]] if snapshot.get("pages") else list(run.document.pages.order_by("page_number"))
        validate_source_evidence(draft, pages)
        validate_draft(draft, document_id=run.document_id, check_database=True)
        validate_selected_resolutions(draft)
        return {"draft": mark_ready_records(draft)}
    finally:
        connections.close_all()


def _save(state, config):
    try:
        with transaction.atomic():
            run, _ = _source(state)
            run = PrescriptionWorkflowRun.objects.select_for_update().get(pk=run.pk)
            if str(run.lease_owner) != config["configurable"].get("lease_owner") or not run.lease_expires_at or run.lease_expires_at <= timezone.now():
                raise ValueError("Workflow lease expired or changed before saving.")
            # Serialize first-review creation with other graph deliveries.
            PrescriptionDocument.objects.select_for_update().get(pk=run.document_id)
            review, created = PrescriptionReview.objects.get_or_create(document_id=run.document_id)
            review = PrescriptionReview.objects.select_for_update().get(pk=review.pk)
            if review.reviewed_data or review.published_at or review.status in {"approved", "rejected"}:
                return {"review_id": review.pk, "review_preserved": True, "status": "needs_review", "reviewer_revision": review.revision}
            review.reviewed_data = state["draft"]
            review.selected_patient_id = state["draft"]["patient"]["patient_id"]
            review.save(update_fields=["reviewed_data", "selected_patient", "updated_at"])
            return {"review_id": review.pk, "review_preserved": False, "status": "needs_review", "reviewer_revision": review.revision}
    finally:
        connections.close_all()


def build_mapping_graph():
    builder = StateGraph(MappingState)
    for name, node in (("normalize", _normalize), ("resolve", _resolve), ("validate", _validate), ("save_review", _save)):
        builder.add_node(name, audited_stage(name, node))
    builder.add_edge(START, "normalize")
    builder.add_edge("normalize", "resolve")
    builder.add_edge("resolve", "validate")
    builder.add_edge("validate", "save_review")
    builder.add_edge("save_review", END)
    return builder.compile(checkpointer=DjangoCheckpointSaver())


def execute_mapping_workflow(run_id):
    if transaction.get_connection().in_atomic_block:
        raise ValueError("Run LangGraph outside an enclosing database transaction.")
    owner = acquire_workflow_lease(run_id)
    try:
        run = PrescriptionWorkflowRun.objects.get(pk=run_id)
        graph = build_mapping_graph()
        config = {"configurable": {"thread_id": str(run.pk), "lease_owner": str(owner)}, "recursion_limit": 8}
        initial = None if DjangoCheckpointSaver().get_tuple(config) else {
            "run_id": str(run.pk), "document_id": run.document_id, "document_sha256": run.document_sha256,
            "schema_version": run.versions["schema"], "extraction_run_id": run.versions["extraction_run_id"],
            "prompt_version": run.versions["prompt"], "model_name": run.versions["model"],
            "extraction_attempts": 0, "repair_attempts": 0, "status": "running"}
        result = graph.invoke(initial, config)
        release_workflow_lease(run.pk, owner, status="needs_review")
        return result
    except Exception:
        release_workflow_lease(run_id, owner, status="failed")
        raise
