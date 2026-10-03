from django.test import TransactionTestCase
from prescriptions.models import PrescriptionDocument, ExtractionRun, PrescriptionReview
from prescriptions.evaluation.corpus import cases
from prescriptions.services.mapping_graph import prepare_mapping_workflow, execute_mapping_workflow
from records.models import ClinicalObservation


class MappingGraphTests(TransactionTestCase):
    def test_evidence_validation_uses_original_page_snapshot(self):
        page = self.document.pages.get()
        self.extraction.structured_data["source_page_artifact"] = {"pages": [{"page_number": 1, "raw_text": page.raw_text, "cleaned_text": page.cleaned_text}]}
        self.extraction.save(update_fields=["structured_data"])
        self.document.pages.update(raw_text="Changed synthetic OCR", cleaned_text="Changed synthetic OCR")
        result = execute_mapping_workflow(prepare_mapping_workflow(self.extraction).pk)
        self.assertNotIn("unsupported_evidence", {item["type"] for item in result["draft"]["unresolved_items"]})

    def setUp(self):
        self.document = PrescriptionDocument.objects.create(file="synthetic.pdf", original_filename="synthetic.pdf", sha256="f" * 64)
        case = cases()[0]
        self.document.pages.create(page_number=1, raw_text=case["pages"][0], cleaned_text=case["pages"][0])
        self.extraction = ExtractionRun.objects.create(document=self.document, schema_version="1", status="completed", structured_data={"gemini_extraction": case["payload"]})

    def test_mapping_graph_saves_actual_fields_without_publishing(self):
        run = prepare_mapping_workflow(self.extraction)
        result = execute_mapping_workflow(run.pk)
        review = PrescriptionReview.objects.get(pk=result["review_id"])
        record = review.reviewed_data["observations"][0]["histopathologies"][0]
        for path, expected in cases()[0]["expected"].items():
            self.assertEqual(record["values"][path.split(".")[-1]], expected)
        self.assertTrue(run.checkpoints.exists())
        self.assertFalse(ClinicalObservation.objects.exists())
        self.assertEqual(review.status, "draft")
        execute_mapping_workflow(run.pk)
        self.assertEqual(PrescriptionReview.objects.count(), 1)

    def test_existing_reviewer_data_is_preserved(self):
        review = PrescriptionReview.objects.create(document=self.document, reviewed_data={"reviewer_owned": "Synthetic edit"})
        result = execute_mapping_workflow(prepare_mapping_workflow(self.extraction).pk)
        self.assertTrue(result["review_preserved"])
        review.refresh_from_db()
        self.assertEqual(review.reviewed_data, {"reviewer_owned": "Synthetic edit"})
