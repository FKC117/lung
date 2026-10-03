from django.test import TransactionTestCase
from prescriptions.models import PrescriptionDocument, PrescriptionWorkflowRun
from prescriptions.services.stage_audit import audited_stage
from prescriptions.services.workflow_state import acquire_workflow_lease
from prescriptions.services.workflow_recovery import cancel_workflow


class StageAuditTests(TransactionTestCase):
    def setUp(self):
        document = PrescriptionDocument.objects.create(file="synthetic.pdf", sha256="a" * 64)
        self.run = PrescriptionWorkflowRun.objects.create(document=document, document_sha256=document.sha256)
        owner = acquire_workflow_lease(self.run.pk)
        self.state = {"run_id": str(self.run.pk), "private_source": "synthetic private content"}
        self.config = {"configurable": {"lease_owner": str(owner)}}

    def test_success_and_replay_have_separate_durable_outcomes(self):
        node = audited_stage("normalize", lambda state: {"draft": "private draft"})
        for _ in range(2):
            self.assertEqual(node(self.state, self.config), {"draft": "private draft"})
        self.run.refresh_from_db()
        events = self.run.versions["stage_audit"]
        self.assertEqual(len(events), 2)
        self.assertTrue(all(event["status"] == "succeeded" for event in events))
        self.assertNotIn("private", str(events))

    def test_failure_category_never_records_exception_content(self):
        def fail(state, config):
            raise ValueError("synthetic private malformed content")
        with self.assertRaises(ValueError):
            audited_stage("validate", fail)(self.state, self.config)
        self.run.refresh_from_db()
        event = self.run.versions["stage_audit"][0]
        self.assertEqual(event["error_category"], "invalid_output")
        self.assertEqual(event["status"], "failed")
        self.assertNotIn("private", str(event))

    def test_cancelled_worker_cannot_finish_its_audit(self):
        def cancelled(state):
            cancel_workflow(self.run.pk)
            raise RuntimeError("private late failure")
        with self.assertRaises(RuntimeError):
            audited_stage("provider", cancelled)(self.state, self.config)
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, "cancelled")
        self.assertEqual(self.run.versions["stage_audit"][0]["status"], "running")
