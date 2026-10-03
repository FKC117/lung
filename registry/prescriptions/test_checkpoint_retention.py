from datetime import timedelta
from io import StringIO
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone
from prescriptions.models import PrescriptionDocument, PrescriptionWorkflowRun, PrescriptionWorkflowCheckpoint, PrescriptionWorkflowWrite, PrescriptionReview, ExtractionRun
from prescriptions.services.checkpoint_retention import prune_checkpoints


class CheckpointRetentionTests(TestCase):
    def artifact(self, status="cancelled", review_status=None, published=False):
        from uuid import uuid4
        document = PrescriptionDocument.objects.create(file="synthetic.pdf", sha256=uuid4().hex * 2)
        extraction = ExtractionRun.objects.create(document=document, structured_data={"synthetic_evidence": "Preserve"})
        run = PrescriptionWorkflowRun.objects.create(document=document, document_sha256=document.sha256, status=status)
        PrescriptionWorkflowRun.objects.filter(pk=run.pk).update(updated_at=timezone.now() - timedelta(days=45))
        PrescriptionWorkflowCheckpoint.objects.create(run=run, checkpoint_id="synthetic", payload_type="json", payload=b"{}", metadata_type="json", metadata=b"{}")
        PrescriptionWorkflowWrite.objects.create(run=run, checkpoint_id="synthetic", task_id="synthetic", write_index=0, channel="synthetic", payload_type="json", payload=b"{}")
        if review_status:
            PrescriptionReview.objects.create(document=document, status=review_status, reviewed_data={"synthetic_draft": "Preserve"}, published_at=timezone.now() if published else None)
        return run, extraction

    def test_dry_run_then_apply_keeps_run_evidence_and_published_review(self):
        run, extraction = self.artifact(status="needs_review", review_status="approved", published=True)
        result = prune_checkpoints(retention_days=30)
        self.assertEqual(result["workflows"], 1)
        self.assertTrue(run.checkpoints.exists())
        applied = prune_checkpoints(retention_days=30, apply=True)
        self.assertEqual(applied["checkpoints"], 1)
        self.assertEqual(applied["pending_writes"], 1)
        self.assertFalse(run.checkpoints.exists())
        self.assertFalse(run.pending_writes.exists())
        extraction.refresh_from_db()
        self.assertEqual(extraction.structured_data["synthetic_evidence"], "Preserve")
        self.assertTrue(PrescriptionWorkflowRun.objects.filter(pk=run.pk).exists())
        self.assertEqual(run.document.review.reviewed_data["synthetic_draft"], "Preserve")

    def test_running_waiting_paused_recent_and_leased_runs_survive(self):
        from uuid import uuid4
        protected = [self.artifact(status=status)[0] for status in ("running", "waiting_provider", "queued", "needs_review", "ready")]
        protected.append(self.artifact(status="failed", review_status="in_review")[0])
        recent = self.artifact()[0]
        PrescriptionWorkflowRun.objects.filter(pk=recent.pk).update(updated_at=timezone.now())
        protected.append(recent)
        leased = self.artifact()[0]
        PrescriptionWorkflowRun.objects.filter(pk=leased.pk).update(lease_owner=uuid4())
        protected.append(leased)
        self.assertEqual(prune_checkpoints(retention_days=30, apply=True)["workflows"], 0)
        self.assertTrue(all(run.checkpoints.exists() for run in protected))

    def test_command_requires_explicit_retention_and_outputs_counts_only(self):
        run, _ = self.artifact()
        with self.assertRaises(CommandError):
            call_command("prune_prescription_checkpoints", retention_days=0)
        output = StringIO()
        call_command("prune_prescription_checkpoints", retention_days=30, stdout=output)
        self.assertIn('"applied": false', output.getvalue())
        self.assertNotIn("Preserve", output.getvalue())
        self.assertTrue(run.checkpoints.exists())

    def test_immutable_repair_artifacts_survive_operational_cleanup(self):
        run, _ = self.artifact()
        for namespace in ("repair-request", "repair-proposal"):
            PrescriptionWorkflowCheckpoint.objects.create(run=run, namespace=namespace, checkpoint_id="repair", payload_type="json", payload=b"{}", metadata_type="json", metadata=b"{}")
        result = prune_checkpoints(retention_days=30, apply=True)
        self.assertEqual(result["checkpoints"], 1)
        self.assertEqual(run.checkpoints.count(), 2)
