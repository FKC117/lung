from copy import deepcopy
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from prescriptions.models import PrescriptionDocument, PrescriptionReview, ExtractionRun
from prescriptions.services.field_contract import contract, fields
from prescriptions.services.intake_draft import build_intake_draft


class AllSectionReviewPersistenceTests(TestCase):
    def test_every_section_and_supported_field_survives_authenticated_save_reload(self):
        user = get_user_model().objects.create_user(username="all-section-synthetic")
        document = PrescriptionDocument.objects.create(file="synthetic.pdf",original_filename="synthetic.pdf",sha256="f"*64,uploaded_by=user)
        observation = {}
        for collection in contract()["collections"]:
            record = {}
            for key, definition in fields(collection).items():
                if definition.get("readOnly"):
                    continue
                kind = definition.get("type")
                value = "Synthetic " + key
                if definition.get("choices"):
                    value = definition["choices"][0]["value"]
                elif kind == "number":
                    value = 1
                elif kind == "boolean":
                    value = True
                elif kind == "date":
                    value = "2020-01-02"
                elif kind == "datetime-local":
                    value = "2020-01-02T10:00"
                if definition.get("multiple"):
                    value = [value]
                record[key] = {"value":value,"page":1,"source_text":"SYNTHETIC FIXTURE ONLY " + str(value)}
            observation[collection] = [record]
        draft = build_intake_draft({"gemini_extraction":{"observations":[observation]}},document_id=document.pk,resolve_options=False)
        original = deepcopy(draft)
        review = PrescriptionReview.objects.create(document=document,reviewed_data=draft)
        client = APIClient()
        client.force_authenticate(user)
        response = client.patch(f"/api/prescriptions/documents/{document.pk}/review/",{"reviewed_data":draft,"expected_revision":1},format="json")
        self.assertEqual(response.status_code,200,response.data)
        review.refresh_from_db()
        fetched = client.get(f"/api/prescriptions/documents/{document.pk}/")
        self.assertEqual(fetched.status_code,200)
        self.assertEqual(fetched.data["review"]["reviewed_data"],review.reviewed_data)
        for collection in contract()["collections"]:
            with self.subTest(collection=collection):
                saved = review.reviewed_data["observations"][0][collection][0]
                before = original["observations"][0][collection][0]
                self.assertEqual(saved["values"],before["values"])
                self.assertEqual(saved["extracted_values"],before["extracted_values"])
                self.assertEqual(saved["resolutions"],before["resolutions"])
        self.assertEqual(review.reviewed_data["source_facts"],original["source_facts"])
        self.assertFalse(ExtractionRun.objects.exists())
        # Saving the identical draft is idempotent and preserves its revision.
        self.assertEqual(review.revision,1)
