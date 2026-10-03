"""Lease-fenced stage outcomes containing no source, prompts or exception messages."""
from inspect import signature
from langchain_core.runnables import RunnableConfig
from django.db import transaction
from django.utils import timezone
from prescriptions.models import PrescriptionWorkflowRun
from .provider_failures import audit_failure_category
from .workflow_state import WorkflowLeaseConflict

STAGES = {"local", "provider", "normalize", "resolve", "validate",
          "complete_extraction", "save_review", "repair_provider", "repair_proposal"}


@transaction.atomic
def _record(run_id, owner, stage, status, *, event_id=None, category=""):
    run = PrescriptionWorkflowRun.objects.select_for_update().get(pk=run_id)
    if str(run.lease_owner) != owner or not run.lease_expires_at or run.lease_expires_at <= timezone.now():
        raise WorkflowLeaseConflict("Stage audit lease expired or changed.")
    events = list(run.versions.get("stage_audit", []))
    if event_id is None:
        event_id = len(events)
        events.append({"stage": stage, "status": status, "started_at": timezone.now().isoformat()})
    else:
        events[event_id] = {**events[event_id], "status": status, "completed_at": timezone.now().isoformat(), "error_category": category}
    run.versions = {**run.versions, "stage_audit": events}
    run.save(update_fields=["versions", "updated_at"])
    return event_id


def audited_stage(stage, node):
    if stage not in STAGES:
        raise ValueError("Unknown audit stage.")
    accepts_config = "config" in signature(node).parameters

    def invoke(state, config: RunnableConfig):
        owner = config["configurable"]["lease_owner"]
        event = _record(state["run_id"], owner, stage, "running")
        try:
            result = node(state, config) if accepts_config else node(state)
        except Exception as exc:
            category = "workflow_conflict" if isinstance(exc, WorkflowLeaseConflict) else audit_failure_category(exc)
            try:
                _record(state["run_id"], owner, stage, "failed", event_id=event, category=category)
            except WorkflowLeaseConflict:
                # A cancelled/reclaimed attempt stays honestly interrupted; stale workers cannot write.
                pass
            raise
        _record(state["run_id"], owner, stage, "succeeded", event_id=event)
        return result
    return invoke
