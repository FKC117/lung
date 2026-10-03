from copy import deepcopy
from django.test import TestCase
from django.core.exceptions import ValidationError
from prescriptions.models import PrescriptionDocument, PrescriptionReview, PrescriptionWorkflowRun, PrescriptionWorkflowCheckpoint
from prescriptions.services.workflow_state import acquire_workflow_lease, WorkflowLeaseConflict
from prescriptions.services.repair_storage import reserve_saved_repair, store_saved_proposal
from prescriptions.services.repair_budget import RepairLimits, RepairBudgetExhausted
from prescriptions.services.repair_contract import prepare_repair_request
from prescriptions import test_repair_contract


class DurableRepairStorageTests(TestCase):
    def setUp(self):
        fixture = test_repair_contract.TargetedRepairContractTests()
        fixture.setUp()
        self.document = PrescriptionDocument.objects.create(file="synthetic.pdf", original_filename="synthetic.pdf", sha256="a" * 64)
        self.draft = deepcopy(fixture.draft)
        self.draft["document_id"] = self.document.pk
        self.review = PrescriptionReview.objects.create(document=self.document, reviewed_data=self.draft, revision=3)
        self.run = PrescriptionWorkflowRun.objects.create(document=self.document, document_sha256=self.document.sha256, versions={"kind": "targeted_repair"})
        self.owner = acquire_workflow_lease(self.run.pk)
        self.request = prepare_repair_request(self.draft, **fixture.args)
        self.payload = fixture.payload

    def reserve(self):
        return reserve_saved_repair(self.run.pk, self.owner, self.review.pk, self.request, limits=RepairLimits(1, 1000, 60), input_bytes=100, max_output_tokens=200)

    def store(self):
        return store_saved_proposal(self.run.pk, self.owner, self.review.pk, self.request["request_sha256"], self.payload)

    def test_reservation_survives_reload_and_proposal_never_changes_review(self):
        self.reserve()
        self.run.refresh_from_db()
        self.assertEqual(self.run.versions["repair_budget"]["attempts_reserved"], 1)
        with self.assertRaises(RepairBudgetExhausted):
            self.reserve()
        self.store()
        self.store()
        self.assertEqual(PrescriptionWorkflowCheckpoint.objects.filter(run=self.run).count(), 2)
        self.review.refresh_from_db()
        self.assertEqual(self.review.reviewed_data, self.draft)
        self.assertEqual(self.review.revision, 3)
        self.assertNotIn("source_sections", str(self.run.versions))

    def test_changed_revision_and_approved_review_reject_proposal(self):
        self.reserve()
        self.review.revision = 4
        self.review.save()
        with self.assertRaises(ValidationError):
            self.store()
        self.review.revision = 3
        self.review.status = "approved"
        self.review.save()
        with self.assertRaises(ValidationError):
            self.store()
        self.assertFalse(PrescriptionWorkflowCheckpoint.objects.filter(namespace="repair-proposal").exists())

    def test_stale_owner_and_stale_source_cannot_reserve(self):
        from uuid import uuid4
        self.owner = uuid4()
        with self.assertRaises(WorkflowLeaseConflict):
            self.reserve()
        self.assertFalse(self.run.checkpoints.exists())

    def test_new_workflow_identity_cannot_reset_document_repair_budget(self):
        self.reserve()
        second = PrescriptionWorkflowRun.objects.create(document=self.document, document_sha256=self.document.sha256, versions={"kind": "targeted_repair"})
        self.run = second
        self.owner = acquire_workflow_lease(second.pk)
        with self.assertRaises(ValidationError):
            self.reserve()
        second.refresh_from_db()
        self.assertNotIn("repair_budget", second.versions)
        self.assertFalse(second.checkpoints.exists())

    def test_late_response_is_discarded_without_changing_saved_review(self):
        from datetime import timedelta
        from django.utils import timezone
        self.reserve()
        self.run.refresh_from_db()
        self.run.versions["repair_budget"]["deadline_at"] = (timezone.now() - timedelta(seconds=1)).isoformat()
        self.run.save()
        with self.assertRaises(ValidationError):
            self.store()
        self.review.refresh_from_db()
        self.assertEqual(self.review.reviewed_data, self.draft)
        self.assertFalse(self.run.checkpoints.filter(namespace="repair-proposal").exists())
