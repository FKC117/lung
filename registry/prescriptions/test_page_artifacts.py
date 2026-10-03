from unittest.mock import patch
from django.test import TestCase, override_settings
from prescriptions.models import PrescriptionDocument
from prescriptions.services.processing import ensure_page_artifact, process_document
from prescriptions.services.extraction import GeminiRateLimitError


class LocalArtifactReuseTests(TestCase):
    def setUp(self):
        self.document = PrescriptionDocument.objects.create(file="synthetic.pdf", original_filename="synthetic.pdf", sha256="2" * 64)

    def test_retry_reuses_the_same_page_ids_and_does_not_repeat_ocr(self):
        with patch("prescriptions.services.processing.extract_pages", return_value=[(1, "Synthetic extraction fixture text", {"method": "text"}, None, None)]) as extract:
            first = ensure_page_artifact(self.document)
            second = ensure_page_artifact(self.document)
        self.assertEqual(extract.call_count, 1)
        self.assertEqual(first[0].pk, second[0].pk)

    def test_changed_ocr_configuration_rebuilds_artifact(self):
        with patch("prescriptions.services.processing.extract_pages", return_value=[(1, "Synthetic extraction fixture text", {"method": "text"}, None, None)]) as extract:
            ensure_page_artifact(self.document)
            with override_settings(TESSERACT_LANGUAGES="synthetic-other-language"):
                ensure_page_artifact(self.document)
        self.assertEqual(extract.call_count, 2)

    def test_failed_replacement_keeps_previous_pages(self):
        with patch("prescriptions.services.processing.extract_pages", return_value=[(1, "Original synthetic fixture", {}, None, None)]):
            original = ensure_page_artifact(self.document)[0]
        with override_settings(TESSERACT_LANGUAGES="changed"), patch("prescriptions.services.processing.extract_pages", side_effect=RuntimeError("Synthetic OCR failure")):
            with self.assertRaises(RuntimeError):
                ensure_page_artifact(self.document)
        self.assertEqual(self.document.pages.get().pk, original.pk)

    def test_quota_retry_propagates_and_reuses_local_pages(self):
        answer = ({"patient": {}, "observations": [], "warnings": [], "unresolved_items": []}, "", "synthetic-v1", "synthetic-model")
        with patch("prescriptions.services.processing.extract_pages", return_value=[(1, "Synthetic extraction fixture text", {"method": "text"}, None, None)]) as extract, patch("prescriptions.services.processing.extract_structured_data", side_effect=[GeminiRateLimitError(), answer]):
            with self.assertRaises(GeminiRateLimitError):
                process_document(self.document)
            page_id = self.document.pages.get().pk
            run = process_document(self.document)
        self.assertEqual(run.status, "completed")
        self.assertEqual(extract.call_count, 1)
        self.assertEqual(self.document.pages.get().pk, page_id)
        self.assertEqual(run.structured_data["source_page_artifact"]["pages"][0]["page_id"], page_id)
        self.assertEqual(run.structured_data["source_page_artifact"]["document_sha256"], self.document.sha256)
