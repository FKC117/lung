from copy import deepcopy
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from prescriptions.models import PrescriptionDocument, PrescriptionReview, PrescriptionWorkflowRun
from prescriptions.services.repair_storage import _append
from prescriptions.services.repair_contract import prepare_repair_request, validate_repair_proposal
from prescriptions import test_repair_contract


class SavedProposalApiTests(TestCase):
    def setUp(self):
        fixture = test_repair_contract.TargetedRepairContractTests()
        fixture.setUp()
        self.user = get_user_model().objects.create_user(username="synthetic-proposal-owner")
        self.document = PrescriptionDocument.objects.create(file="synthetic.pdf", sha256="a"*64, uploaded_by=self.user)
        self.draft = deepcopy(fixture.draft)
        self.draft["document_id"] = self.document.pk
        self.review = PrescriptionReview.objects.create(document=self.document, reviewed_data=self.draft, revision=3)
        self.run = PrescriptionWorkflowRun.objects.create(document=self.document, document_sha256=self.document.sha256, versions={"kind": "targeted_repair"})
        self.request = prepare_repair_request(self.draft, **fixture.args)
        self.proposal = validate_repair_proposal(self.request, fixture.payload, current_draft=self.draft, current_revision=3, document_sha256=self.document.sha256)
        _append(self.run, self.request["request_sha256"], "repair-request", {"review_id": self.review.pk, "request": self.request})
        _append(self.run, self.request["request_sha256"], "repair-proposal", self.proposal)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = f"/api/prescriptions/documents/{self.document.pk}/repair-proposals/"

    def test_saved_proposal_is_visible_without_mutation_or_private_prompt(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["proposals"][0]["patches"]["biopsy_date"]["value"], "2020-01-02")
        self.assertNotIn("original_values", response.data["proposals"][0])
        self.review.refresh_from_db()
        self.assertEqual(self.review.reviewed_data, self.draft)
        self.assertEqual(self.review.revision, 3)

    def test_stale_and_approved_proposals_are_not_exposed(self):
        self.review.revision = 4
        self.review.save()
        self.assertEqual(self.client.get(self.url).data["proposals"], [])
        self.review.revision = 3
        self.review.status = "approved"
        self.review.save()
        self.assertEqual(self.client.get(self.url).data["proposals"], [])

    def test_outsider_cannot_read_source_proposals(self):
        outsider = get_user_model().objects.create_user(username="synthetic-proposal-outsider")
        self.client.force_authenticate(outsider)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_changed_source_cannot_reuse_saved_proposal(self):
        self.document.sha256 = "b"*64
        self.document.save()
        self.assertEqual(self.client.get(self.url).data["proposals"], [])

    def test_adopted_value_saves_through_shared_review_api_preserving_originals(self):
        adopted = deepcopy(self.draft)
        record = adopted["observations"][0]["histopathologies"][0]
        original = deepcopy(record["extracted_values"])
        record["values"]["biopsy_date"] = "2020-01-02"
        record["state"] = "edited"
        response = self.client.patch(f"/api/prescriptions/documents/{self.document.pk}/review/", {"expected_revision": 3, "reviewed_data": adopted}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.review.refresh_from_db()
        saved = self.review.reviewed_data["observations"][0]["histopathologies"][0]
        self.assertEqual(saved["values"]["biopsy_date"], "2020-01-02")
        self.assertEqual(saved["extracted_values"], original)
        self.assertEqual(self.review.revision, 4)
        self.assertEqual(self.review.status, "in_review")
        self.assertEqual(self.client.get(self.url).data["proposals"], [])
