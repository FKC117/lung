"""Checkpointed local extraction, enrichment and existing review-only mapping."""
from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace
import json
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from langgraph.graph import StateGraph, START, END
from .stage_audit import audited_stage
from prescriptions.models import ExtractionRun, ExtractionIssue, LLMInvocation, PrescriptionDocument, PrescriptionWorkflowRun
from .checkpoint import DjangoCheckpointSaver, close_worker_connections
from .extraction import build_contents, validate_extraction, GeminiRateLimitError
from .field_contract import contract, extraction_schema
from .mapping_graph import MappingState, artifact_hash, _normalize, _resolve, _validate, _save
from .processing import ensure_page_artifact, page_artifact_version, enrich_extraction
from .text_analysis import analyze_text
from .workflow_state import acquire_workflow_lease, release_workflow_lease, WorkflowLeaseConflict


def _data_partition(document):
    partition = {"document_id": document.pk, "uploaded_by": document.uploaded_by_id,
                 "policy": settings.PRESCRIPTION_GEMINI_DATA_POLICY,
                 "approval_reference": settings.PRESCRIPTION_GEMINI_DATA_APPROVAL_REFERENCE}
    return sha256(json.dumps(partition, sort_keys=True).encode()).hexdigest()


@transaction.atomic
def prepare_extraction_workflow(document, *, task_id):
    if not task_id:
        raise ValueError("A stable task identity is required.")
    document = PrescriptionDocument.objects.select_for_update().get(pk=document.pk)
    existing = document.workflow_runs.filter(versions__task_id=str(task_id), versions__kind="extraction").first()
    if existing:
        return existing
    active = document.workflow_runs.filter(versions__kind="extraction", status__in=["queued", "running", "waiting_provider"]).first()
    if active:
        raise WorkflowLeaseConflict("This document already has an active extraction workflow.")
    extraction = ExtractionRun.objects.create(document=document, schema_version="1")
    workflow = PrescriptionWorkflowRun.objects.create(document=document, document_sha256=document.sha256,
        versions={"kind": "extraction", "task_id": str(task_id), "extraction_run_id": extraction.pk,
                  "schema": contract()["version"], "prompt": settings.PRESCRIPTION_EXTRACTION_PROMPT_VERSION,
                  "model": settings.PRESCRIPTION_EXTRACTION_MODEL, "extractor": page_artifact_version(), "data_partition": _data_partition(document)})
    document.status = PrescriptionDocument.Status.PROCESSING
    document.processing_started_at = timezone.now()
    document.save(update_fields=["status", "processing_started_at"])
    return workflow


def _workflow(state, config, *, lock=False):
    query = PrescriptionWorkflowRun.objects.select_for_update() if lock else PrescriptionWorkflowRun.objects
    workflow = query.select_related("document").get(pk=state["run_id"])
    if str(workflow.lease_owner) != config["configurable"]["lease_owner"] or not workflow.lease_expires_at or workflow.lease_expires_at <= timezone.now():
        raise WorkflowLeaseConflict("Extraction lease expired or changed.")
    if workflow.document_sha256 != workflow.document.sha256:
        raise ValueError("Document changed; create a new extraction workflow.")
    if (workflow.versions["schema"] != contract()["version"] or workflow.versions["prompt"] != settings.PRESCRIPTION_EXTRACTION_PROMPT_VERSION
            or workflow.versions["model"] != settings.PRESCRIPTION_EXTRACTION_MODEL or workflow.versions["extractor"] != page_artifact_version()):
        raise ValueError("Extraction configuration changed; create a new workflow.")
    if workflow.versions.get("data_partition") and workflow.versions["data_partition"] != _data_partition(workflow.document):
        raise ValueError("Document ownership or approved data-policy partition changed; create a new workflow.")
    extraction = ExtractionRun.objects.get(pk=workflow.versions["extraction_run_id"], document=workflow.document)
    return workflow, extraction


@close_worker_connections
def _local(state, config):
    workflow, extraction = _workflow(state, config)
    if not extraction.structured_data.get("workflow_local_complete"):
        pages = ensure_page_artifact(workflow.document)
        result = analyze_text(pages)
        result["source_page_artifact"] = {"document_sha256": workflow.document_sha256, "extractor_version": page_artifact_version(),
            "pages": [{"page_number": page.page_number, "page_id": page.pk, "raw_text": page.raw_text, "cleaned_text": page.cleaned_text} for page in pages]}
        result["workflow_local_complete"] = True
        with transaction.atomic():
            _workflow(state, config, lock=True)
            extraction.structured_data = result
            extraction.save(update_fields=["structured_data"])
    return {"extraction_run_id": extraction.pk}


@close_worker_connections
def _provider(state, config):
    workflow, extraction = _workflow(state, config)
    if extraction.structured_data.get("workflow_provider_complete"):
        return {}
    pages = [SimpleNamespace(document_id=workflow.document_id, **page) for page in extraction.structured_data["source_page_artifact"]["pages"]]
    recovery = config["configurable"].get("quality_recovery", False)
    prompt = workflow.versions["prompt"] + ("-quality-recovery" if recovery else "")
    source_hash = sha256(build_contents(pages).encode()).hexdigest()
    succeeded = extraction.llm_invocations.filter(status=LLMInvocation.Status.SUCCEEDED, input_sha256=source_hash,
        model_name=workflow.versions["model"], prompt_version=prompt).order_by("-id").first()
    result = deepcopy(extraction.structured_data)
    if succeeded:
        # Recover an audited answer after a crash without another external call.
        result["gemini_extraction"] = validate_extraction(json.loads(succeeded.output_text))
        result["gemini_status"] = "available"
        result.setdefault("warnings", []).extend(str(warning) for warning in result["gemini_extraction"].get("warnings", []))
        extraction.raw_response = succeeded.output_text
        extraction.ai_model = succeeded.model_name
        extraction.prompt_version = succeeded.prompt_version
    elif config["configurable"].get("provider_fallback_reason"):
        reason = config["configurable"]["provider_fallback_reason"]
        result["gemini_extraction"] = {"unresolved_items": [{"type": "provider_budget_exhausted", "reason": reason}]}
        result["gemini_status"] = "unavailable"
        result["gemini_error"] = reason
        result.setdefault("warnings", []).append(reason)
        extraction.prompt_version = "deterministic-text-v1"
    else:
        budget_reason = ""
        if settings.PRESCRIPTION_DOCUMENT_BUDGET_ENABLED:
            from .repair_budget import RepairLimits, reserve_repair_attempt, RepairBudgetExhausted
            from .extraction import SYSTEM_INSTRUCTION, QUALITY_RECOVERY_INSTRUCTION
            limits = RepairLimits(settings.PRESCRIPTION_DOCUMENT_MAX_ATTEMPTS, settings.PRESCRIPTION_DOCUMENT_TOKEN_UNITS, settings.PRESCRIPTION_DOCUMENT_SECONDS)
            instruction = SYSTEM_INSTRUCTION + (QUALITY_RECOVERY_INSTRUCTION if recovery else "")
            request_identity = sha256((source_hash + "\0" + prompt).encode()).hexdigest()
            with transaction.atomic():
                current, _ = _workflow(state, config, lock=True)
                PrescriptionDocument.objects.select_for_update().get(pk=current.document_id)
                other = PrescriptionWorkflowRun.objects.filter(document_id=current.document_id, versions__has_key="document_budget").exclude(pk=current.pk).exists()
                try:
                    if other:
                        raise RepairBudgetExhausted("Document admission already belongs to another workflow.")
                    accounting = reserve_repair_attempt(current.versions.get("document_budget"), limits=limits, request_sha256=request_identity,
                        input_bytes=len((build_contents(pages) + instruction + json.dumps(extraction_schema())).encode()),
                        max_output_tokens=settings.PRESCRIPTION_PROVIDER_MAX_OUTPUT_TOKENS, now=timezone.now())
                    current.versions = {**current.versions, "document_budget": accounting}
                    current.save(update_fields=["versions", "updated_at"])
                except RepairBudgetExhausted:
                    budget_reason = "Document extraction budget exhausted; saved local evidence remains available for review."
        if budget_reason:
            result["gemini_extraction"] = {"unresolved_items": [{"type": "document_budget_exhausted", "reason": budget_reason}]}
            result["gemini_status"] = "unavailable"
            result["gemini_error"] = budget_reason
            result.setdefault("warnings", []).append(budget_reason)
            extraction.prompt_version = "deterministic-text-v1"
        else:
            result = enrich_extraction(extraction, pages, result, retry_invalid_structured_output=not recovery, quality_recovery=recovery)
            if settings.PRESCRIPTION_DOCUMENT_BUDGET_ENABLED:
                from datetime import datetime
                current = PrescriptionWorkflowRun.objects.get(pk=workflow.pk)
                if timezone.now() >= datetime.fromisoformat(current.versions["document_budget"]["deadline_at"]):
                    reason = "Document deadline exhausted; late provider output is retained only in the restricted audit."
                    result = deepcopy(extraction.structured_data)
                    result["gemini_extraction"] = {"unresolved_items": [{"type": "document_budget_exhausted", "reason": reason}]}
                    result["gemini_status"] = "unavailable"
                    result["gemini_error"] = reason
                    result.setdefault("warnings", []).append(reason)
                    extraction.raw_response = ""
                    extraction.ai_model = ""
                    extraction.prompt_version = "deterministic-text-v1"
    result["workflow_provider_complete"] = True
    with transaction.atomic():
        workflow, _ = _workflow(state, config, lock=True)
        extraction.structured_data = result
        extraction.save(update_fields=["structured_data", "raw_response", "ai_model", "prompt_version"])
        workflow.versions["source_sha256"] = artifact_hash(result)
        workflow.save(update_fields=["versions", "updated_at"])
    return {}


@close_worker_connections
def _complete(state, config):
    with transaction.atomic():
        workflow, extraction = _workflow(state, config, lock=True)
        extraction = ExtractionRun.objects.select_for_update().get(pk=extraction.pk)
        if extraction.status != ExtractionRun.Status.COMPLETED:
            result = deepcopy(extraction.structured_data)
            result["canonical_draft"] = state["draft"]
            extraction.structured_data = result
            extraction.status = ExtractionRun.Status.COMPLETED
            extraction.completed_at = timezone.now()
            extraction.error = ""
            extraction.save(update_fields=["structured_data", "status", "completed_at", "error"])
            for warning in result.get("warnings", []):
                ExtractionIssue.objects.create(document=workflow.document, extraction_run=extraction, code="extraction_warning",
                    severity=ExtractionIssue.Severity.WARNING, message=str(warning))
            for issue in result.get("validation", {}).get("issues", []):
                ExtractionIssue.objects.create(document=workflow.document, extraction_run=extraction, code=issue["code"],
                    severity=issue["severity"], message=issue["message"], page_number=issue.get("page"))
            workflow.versions["source_sha256"] = artifact_hash(result)
            workflow.save(update_fields=["versions", "updated_at"])
            document = workflow.document
            document.status = PrescriptionDocument.Status.READY_FOR_REVIEW
            document.page_count = len(result["source_page_artifact"]["pages"])
            document.processed_at = timezone.now()
            document.save(update_fields=["status", "page_count", "processed_at"])
    return {"status": "needs_review"}


def build_extraction_graph():
    builder = StateGraph(MappingState)
    stages = [("local", _local), ("provider", _provider), ("normalize", _normalize), ("resolve", _resolve),
              ("validate", _validate), ("complete_extraction", _complete), ("save_review", _save)]
    previous = START
    for name, node in stages:
        builder.add_node(name, audited_stage(name, node))
        builder.add_edge(previous, name)
        previous = name
    builder.add_edge(previous, END)
    return builder.compile(checkpointer=DjangoCheckpointSaver())


def execute_extraction_workflow(workflow_id, *, quality_recovery=False, provider_fallback_reason=""):
    if transaction.get_connection().in_atomic_block:
        raise ValueError("Execute the graph outside a surrounding database transaction.")
    owner = acquire_workflow_lease(workflow_id, seconds=3600)
    try:
        workflow = PrescriptionWorkflowRun.objects.get(pk=workflow_id)
        config = {"configurable": {"thread_id": str(workflow.pk), "lease_owner": str(owner), "quality_recovery": quality_recovery,
                                  "provider_fallback_reason": provider_fallback_reason}, "recursion_limit": 12}
        _workflow({"run_id": str(workflow.pk)}, config)
        initial = None if DjangoCheckpointSaver().get_tuple(config) else {"run_id": str(workflow.pk), "document_id": workflow.document_id,
            "document_sha256": workflow.document_sha256, "schema_version": workflow.versions["schema"], "extraction_run_id": workflow.versions["extraction_run_id"]}
        result = build_extraction_graph().invoke(initial, config)
        release_workflow_lease(workflow.pk, owner, status="needs_review")
        return ExtractionRun.objects.get(pk=result["extraction_run_id"])
    except Exception as exc:
        # A reclaimed lease must never be overwritten by an older worker.
        if PrescriptionWorkflowRun.objects.filter(pk=workflow_id, lease_owner=owner).exists():
            release_workflow_lease(workflow_id, owner, status="waiting_provider" if isinstance(exc, GeminiRateLimitError) else "failed")
        raise
