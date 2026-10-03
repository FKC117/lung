from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError
from prescriptions.models import PrescriptionDocument, PrescriptionReview
from prescriptions.services.draft_schema import empty_draft
from prescriptions.services.publish import publish_review


class ReviewRevisionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="revision-test")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.document = PrescriptionDocument.objects.create(file="synthetic.pdf", original_filename="synthetic.pdf", sha256="d" * 64, uploaded_by=self.user)
        self.review = PrescriptionReview.objects.create(document=self.document, reviewed_data=empty_draft(self.document.pk))
        self.url = f"/api/prescriptions/documents/{self.document.pk}/"

    def test_stale_save_and_approval_are_rejected(self):
        first = self.client.patch(self.url + "review/", {"notes": "First edit", "expected_revision": 1}, format="json")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["revision"], 2)
        stale = self.client.patch(self.url + "review/", {"notes": "Stale edit", "expected_revision": 1}, format="json")
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(self.client.post(self.url + "approve-review/", {"expected_revision": 1}, format="json").status_code, 409)
        self.review.refresh_from_db()
        self.assertEqual(self.review.notes, "First edit")

    def test_publication_rejects_approval_of_another_revision(self):
        self.review.status = PrescriptionReview.Status.APPROVED
        self.review.approved_revision = 1
        self.review.revision = 2
        self.review.save()
        with self.assertRaises(ValidationError):
            publish_review(self.review, self.user)

    def test_published_review_cannot_be_reopened(self):
        from django.utils import timezone
        self.review.status = PrescriptionReview.Status.APPROVED
        self.review.published_at = timezone.now()
        self.review.save()
        response = self.client.post(self.url + "reopen-review/", {"reason": "Synthetic reason", "expected_revision": 1}, format="json")
        self.assertEqual(response.status_code, 400)


    def test_final_actions_require_an_explicit_saved_revision(self):
        for action in ("approve-review/", "publish/"):
            response = self.client.post(self.url + action, {}, format="json")
            self.assertEqual(response.status_code, 400)
            self.assertIn("expected_revision", response.data)
        self.review.refresh_from_db()
        self.assertEqual(self.review.status, "draft")

    def test_legacy_unbound_approval_requires_reapproval(self):
        self.review.status = PrescriptionReview.Status.APPROVED
        self.review.approved_revision = None
        self.review.save()
        with self.assertRaises(ValidationError):
            publish_review(self.review, self.user)
