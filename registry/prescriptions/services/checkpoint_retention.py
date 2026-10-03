"""Explicit operational checkpoint cleanup; preserve evidence and active reviews."""
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from prescriptions.models import PrescriptionWorkflowRun, PrescriptionReview


def prune_checkpoints(*, retention_days, apply=False):
    if isinstance(retention_days, bool) or not isinstance(retention_days, int) or retention_days < 1:
        raise ValueError("Configure a positive checkpoint retention period in days.")
    cutoff = timezone.now() - timedelta(days=retention_days)
    totals = {"workflows": 0, "checkpoints": 0, "pending_writes": 0, "applied": apply}
    candidates = PrescriptionWorkflowRun.objects.filter(updated_at__lt=cutoff, status__in=["ready", "needs_review", "failed", "cancelled"], lease_owner__isnull=True).values_list("pk", flat=True)
    for identity in candidates.iterator():
        with transaction.atomic():
            run = PrescriptionWorkflowRun.objects.select_for_update().get(pk=identity)
            if run.updated_at >= cutoff or run.lease_owner or run.status not in {"ready", "needs_review", "failed", "cancelled"}:
                continue
            # Serialize against approval/edit and preserve paused review checkpoints.
            review = PrescriptionReview.objects.select_for_update().filter(document_id=run.document_id).first()
            if review and not review.published_at and review.status != PrescriptionReview.Status.REJECTED:
                continue
            if not review and run.status in {"ready", "needs_review"}:
                continue
            operational = run.checkpoints.exclude(namespace__in=["repair-request", "repair-proposal"])
            checkpoints, writes = operational.count(), run.pending_writes.count()
            if not checkpoints and not writes:
                continue
            totals["workflows"] += 1
            totals["checkpoints"] += checkpoints
            totals["pending_writes"] += writes
            if apply:
                operational.delete()
                run.pending_writes.all().delete()
    return totals
