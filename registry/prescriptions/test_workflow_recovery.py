from django.test import TransactionTestCase
from prescriptions.models import PrescriptionDocument, PrescriptionWorkflowRun, ExtractionRun
from prescriptions.services.workflow_recovery import cancel_workflow, workflow_status
from prescriptions.services.workflow_state import acquire_workflow_lease, WorkflowLeaseConflict


class WorkflowRecoveryTests(TransactionTestCase):
    def test_provider_retry_after_is_not_shortened(self):
        from types import SimpleNamespace
        from prescriptions.tasks import _gemini_retry_countdown
        from prescriptions.services.extraction import GeminiRateLimitError
        self.assertEqual(_gemini_retry_countdown(SimpleNamespace(request=SimpleNamespace(retries=0)),
            GeminiRateLimitError(retry_after_seconds=3600)), 3600)

    def test_cancellation_revokes_lease_and_retains_pending_evidence(self):
        document = PrescriptionDocument.objects.create(file="synthetic.pdf", sha256="c" * 64, status="processing")
        extraction = ExtractionRun.objects.create(document=document, structured_data={"synthetic_evidence": "retained"})
        run = PrescriptionWorkflowRun.objects.create(document=document, document_sha256=document.sha256, versions={"extraction_run_id": extraction.pk})
        acquire_workflow_lease(run.pk)
        cancel_workflow(run.pk)
        cancel_workflow(run.pk)
        with self.assertRaises(WorkflowLeaseConflict):
            acquire_workflow_lease(run.pk)
        extraction.refresh_from_db()
        document.refresh_from_db()
        self.assertEqual(extraction.structured_data, {"synthetic_evidence": "retained"})
        self.assertEqual(extraction.status, "failed")
        self.assertEqual(document.status, "failed")
        self.assertFalse(workflow_status(run.pk)["lease_active"])
        from io import StringIO
        from django.core.management import call_command
        output = StringIO()
        call_command("prescription_workflow", "status", str(run.pk), stdout=output)
        self.assertIn('"status": "cancelled"', output.getvalue())
        self.assertNotIn("synthetic_evidence", output.getvalue())

    def test_completed_extraction_and_review_cannot_be_cancelled(self):
        document = PrescriptionDocument.objects.create(file="synthetic.pdf", sha256="d" * 64)
        extraction = ExtractionRun.objects.create(document=document, status="completed", structured_data={"immutable": True})
        run = PrescriptionWorkflowRun.objects.create(document=document, document_sha256=document.sha256, status="needs_review", versions={"extraction_run_id": extraction.pk})
        with self.assertRaises(WorkflowLeaseConflict):
            cancel_workflow(run.pk)
        extraction.refresh_from_db()
        self.assertEqual(extraction.structured_data, {"immutable": True})
        self.assertEqual(extraction.status, "completed")

    def test_status_reports_only_whitelisted_stage_and_budget_metadata(self):
        document=PrescriptionDocument.objects.create(file="synthetic.pdf",sha256="e"*64)
        extraction=ExtractionRun.objects.create(document=document,structured_data={"workflow_local_complete":True,"private_source":"Synthetic private source"})
        run=PrescriptionWorkflowRun.objects.create(document=document,document_sha256=document.sha256,versions={"extraction_run_id":extraction.pk,"document_budget":{"attempts_reserved":1,"token_units_reserved":200,"deadline_at":"2020-01-01T00:01:00+00:00","requests":["private identity"]},"private_prompt":"Synthetic private prompt"})
        result=workflow_status(run.pk)
        self.assertTrue(result["stage_status"]["local_complete"])
        self.assertEqual(result["budgets"]["document_budget"]["attempts_reserved"],1)
        self.assertNotIn("private",str(result))

    def test_failed_resume_preserves_identity_and_cannot_skip_quota_wait(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from django.test import override_settings
        from prescriptions.services.workflow_recovery import queue_failed_extraction_resume
        document=PrescriptionDocument.objects.create(file="synthetic.pdf",sha256="f"*64)
        run=PrescriptionWorkflowRun.objects.create(document=document,document_sha256=document.sha256,status="failed",versions={"kind":"extraction"})
        with override_settings(PRESCRIPTION_AGENTIC_EXTRACTION_ENABLED=True), patch("prescriptions.tasks.resume_prescription_extraction.delay",return_value=SimpleNamespace(id="synthetic-task")) as queue:
            self.assertEqual(queue_failed_extraction_resume(run.pk),"synthetic-task")
            queue.assert_called_once_with(str(run.pk))
            run.status="waiting_provider"
            run.save()
            with self.assertRaises(WorkflowLeaseConflict):
                queue_failed_extraction_resume(run.pk)
        self.assertEqual(PrescriptionWorkflowRun.objects.count(),1)
