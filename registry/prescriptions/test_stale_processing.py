from copy import deepcopy
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from prescriptions.models import PrescriptionDocument, ExtractionRun, PrescriptionReview, PrescriptionWorkflowRun
from prescriptions.services.draft_schema import empty_draft, empty_observation
from prescriptions.services.stale_processing import reconcile_stale_processing


class StaleProcessingTests(TestCase):
    def setUp(self):
        self.doc = PrescriptionDocument.objects.create(file="synthetic.txt", original_filename="synthetic.txt", sha256="a"*64,
            status="processing", processing_started_at=timezone.now()-timedelta(hours=2))
        self.pending = ExtractionRun.objects.create(document=self.doc, status="pending", structured_data={"preserved": True})
        ExtractionRun.objects.filter(pk=self.pending.pk).update(created_at=timezone.now()-timedelta(hours=2))
        draft = empty_draft(self.doc.pk); draft["observations"]=[empty_observation()]
        self.latest = ExtractionRun.objects.create(document=self.doc, status="completed", structured_data={"canonical_draft": draft})
        self.review = PrescriptionReview.objects.create(document=self.doc, reviewed_data=deepcopy(draft))

    def test_dry_run_and_apply_preserve_evidence_and_review(self):
        before = deepcopy(self.review.reviewed_data)
        self.assertFalse(reconcile_stale_processing(self.doc.pk)["applied"])
        self.pending.refresh_from_db(); self.assertEqual(self.pending.status, "pending")
        reconcile_stale_processing(self.doc.pk, apply=True)
        self.doc.refresh_from_db(); self.pending.refresh_from_db(); self.review.refresh_from_db()
        self.assertEqual(self.doc.status, "ready_for_review")
        self.assertEqual(self.pending.status, "failed")
        self.assertEqual(self.pending.structured_data, {"preserved": True})
        self.assertEqual(self.review.reviewed_data, before)
        self.assertEqual(self.review.revision, 1)
        self.assertFalse(self.review.changes.exists())

    def test_runnable_workflow_and_recent_processing_are_protected(self):
        workflow = PrescriptionWorkflowRun.objects.create(document=self.doc, document_sha256=self.doc.sha256, status="queued")
        with self.assertRaises(ValueError): reconcile_stale_processing(self.doc.pk, apply=True)
        workflow.status="failed"; workflow.save()
        self.doc.processing_started_at=timezone.now(); self.doc.save()
        with self.assertRaises(ValueError): reconcile_stale_processing(self.doc.pk, apply=True)

    def test_newer_pending_extraction_cannot_be_hidden(self):
        ExtractionRun.objects.create(document=self.doc, status="pending")
        with self.assertRaises(ValueError): reconcile_stale_processing(self.doc.pk, apply=True)
        self.doc.refresh_from_db(); self.assertEqual(self.doc.status, "processing")
