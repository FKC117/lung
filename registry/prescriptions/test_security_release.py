from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.contrib.auth import get_user_model
from django.db import connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from records.models import Patient
from records.models import ClinicalObservation
from prescriptions.models import PrescriptionDocument, PrescriptionReview, ExtractionRun
from prescriptions.services.draft_schema import empty_draft, empty_observation
from prescriptions.services.mapping_graph import prepare_mapping_workflow, execute_mapping_workflow
from prescriptions.evaluation.corpus import cases


class ReleaseSecurityTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="synthetic-security-owner")
        self.patient = Patient.objects.create(registration_no="SYNTHETIC-SEC", patient_id="SYNTHETIC-SEC", name="Synthetic fixture")
        self.document = PrescriptionDocument.objects.create(file="synthetic.pdf", sha256="a"*64, uploaded_by=self.user)
        draft = empty_draft(self.document.pk, patient_id=self.patient.pk)
        observation = empty_observation()
        observation["anthropometry"] = {"height_cm": "170", "weight_kg": "70"}
        draft["observations"].append(observation)
        self.review = PrescriptionReview.objects.create(document=self.document, selected_patient=self.patient, reviewed_data=draft)
        self.url = f"/api/prescriptions/documents/{self.document.pk}/"

    def make_client(self, user=None):
        client = APIClient()
        client.force_authenticate(user or self.user)
        return client

    def parallel(self, actions):
        barrier = Barrier(2)
        def worker(action):
            try:
                client = self.make_client()
                barrier.wait(timeout=10)
                return action(client)
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(worker, actions))

    def test_concurrent_save_and_approval_cannot_approve_unsaved_revision(self):
        codes = self.parallel([
            lambda client: client.patch(self.url+"review/", {"notes": "Synthetic edit", "expected_revision": 1}, format="json").status_code,
            lambda client: client.post(self.url+"approve-review/", {"expected_revision": 1}, format="json").status_code])
        self.review.refresh_from_db()
        self.assertIn(codes, ([200, 409], [400, 200]))
        if self.review.status == "approved":
            self.assertEqual(self.review.revision, self.review.approved_revision)
            self.assertEqual(self.review.notes, "")
        else:
            self.assertEqual(self.review.revision, 2)
            self.assertIsNone(self.review.approved_revision)
        self.assertFalse(ClinicalObservation.objects.exists())

    def test_concurrent_publications_create_one_observation(self):
        self.assertEqual(self.make_client().post(self.url+"approve-review/", {"expected_revision": 1}, format="json").status_code, 200)
        codes = self.parallel([lambda client: client.post(self.url+"publish/", {"expected_revision": 1}, format="json").status_code]*2)
        self.assertEqual(codes, [200, 200])
        self.assertEqual(ClinicalObservation.objects.count(), 1)
        self.assertEqual(self.review.publication_observations.count(), 1)

    def test_outsider_cannot_mutate_or_publish_review(self):
        outsider = get_user_model().objects.create_user(username="synthetic-security-outsider")
        client = self.make_client(outsider)
        for action in ("approve-review/", "publish/", "reopen-review/"):
            self.assertEqual(client.post(self.url+action, {"expected_revision": 1}, format="json").status_code, 404)
        self.assertEqual(client.patch(self.url+"review/", {"notes": "unauthorized"}, format="json").status_code, 404)
        self.review.refresh_from_db()
        self.assertEqual(self.review.status, "draft")
        self.assertFalse(ClinicalObservation.objects.exists())

    def test_uploaded_publish_instruction_cannot_assign_patient_or_publish(self):
        fixture = cases()[-1]
        document = PrescriptionDocument.objects.create(file="synthetic-injection.pdf", sha256="b"*64, uploaded_by=self.user)
        document.pages.create(page_number=1, raw_text=fixture["pages"][0], cleaned_text=fixture["pages"][0])
        extraction = ExtractionRun.objects.create(document=document, status="completed", structured_data={"gemini_extraction": fixture["payload"]})
        result = execute_mapping_workflow(prepare_mapping_workflow(extraction).pk)
        review = PrescriptionReview.objects.get(pk=result["review_id"])
        self.assertIsNone(review.selected_patient_id)
        self.assertIsNone(review.published_at)
        self.assertEqual(review.status, "draft")
        self.assertFalse(ClinicalObservation.objects.exists())
