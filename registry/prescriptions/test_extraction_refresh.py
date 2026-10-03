from copy import deepcopy
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from prescriptions.models import PrescriptionDocument, PrescriptionReview, ExtractionRun
from prescriptions.services.draft_schema import empty_draft, empty_observation


class ExtractionRefreshTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="synthetic-refresh")
        self.doc = PrescriptionDocument.objects.create(file="synthetic.pdf", original_filename="synthetic.pdf", sha256="a"*64,
            uploaded_by=self.user, status="ready_for_review")
        self.original = empty_draft(self.doc.pk)
        self.original["observations"] = [empty_observation()]
        self.review = PrescriptionReview.objects.create(document=self.doc, reviewed_data=self.original)
        self.run = ExtractionRun.objects.create(document=self.doc, status="completed", structured_data={"canonical_draft": deepcopy(self.original)})
        self.client = APIClient(); self.client.force_authenticate(self.user)
        self.url = f"/api/prescriptions/documents/{self.doc.pk}/load-latest-extraction/"

    def refresh(self, **overrides):
        return self.client.post(self.url, {"expected_revision": 1, "extraction_run_id": self.run.pk, **overrides}, format="json")

    def test_refresh_audits_original_and_cannot_replay(self):
        raw = deepcopy(self.run.structured_data)
        response = self.refresh()
        self.assertEqual(response.status_code, 200, response.data)
        self.review.refresh_from_db(); self.run.refresh_from_db()
        self.assertEqual(self.review.revision, 2)
        self.assertEqual(self.review.changes.get().previous_value, self.original)
        self.assertEqual(self.run.structured_data, raw)
        self.assertIsNone(self.review.selected_patient_id)
        self.assertIsNone(self.review.published_at)
        self.assertEqual(self.refresh().status_code, 409)

    def test_edited_or_locked_reviews_are_protected(self):
        for field, value in [("notes", "Synthetic reviewer edit"), ("revision", 2), ("status", "approved"), ("status", "rejected")]:
            setattr(self.review, field, value); self.review.save()
            result = self.refresh(expected_revision=self.review.revision)
            self.assertEqual(result.status_code, 400)
            self.review.refresh_from_db()
            self.assertEqual(self.review.reviewed_data, self.original)
            setattr(self.review, field, 1 if field == "revision" else "draft" if field == "status" else ""); self.review.save()

    def test_stale_extraction_and_outsider_are_rejected(self):
        self.assertEqual(self.refresh(extraction_run_id=self.run.pk + 1).status_code, 400)
        outsider = get_user_model().objects.create_user(username="synthetic-outsider")
        self.client.force_authenticate(outsider)
        self.assertEqual(self.refresh().status_code, 404)

    def test_source_cannot_assign_patient(self):
        source = deepcopy(self.original); source["patient"]["match_status"] = "new"
        self.run.structured_data = {"canonical_draft": source}; self.run.save()
        self.assertEqual(self.refresh().status_code, 400)
        self.assertFalse(self.review.changes.exists())
