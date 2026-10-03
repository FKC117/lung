import hashlib
import json
from unittest.mock import patch
from types import SimpleNamespace
from django.test import override_settings
from django.test import TestCase
from prescriptions.models import PrescriptionDocument, PrescriptionBatchJob, PrescriptionBatchItem, ExtractionRun, PrescriptionReview, LLMInvocation
from prescriptions.services.batch import import_batch_row, create_batch_job
from prescriptions.services.extraction import build_contents
from prescriptions.evaluation.corpus import cases


class ImmutableBatchImportTests(TestCase):
    def setUp(self):
        self.document = PrescriptionDocument.objects.create(file="synthetic.pdf", original_filename="synthetic.pdf", sha256="1" * 64)
        fixture = cases()[0]
        self.document.pages.create(page_number=1, raw_text=fixture["pages"][0], cleaned_text=fixture["pages"][0])
        self.original = ExtractionRun.objects.create(document=self.document, schema_version="1", status="completed", structured_data={"synthetic_baseline": True}, raw_response="original immutable response")
        self.review = PrescriptionReview.objects.create(document=self.document, reviewed_data={"reviewer_owned": "preserve"})
        self.job = PrescriptionBatchJob.objects.create(display_name="Synthetic batch", model_name="explicit-test-model", prompt_version="synthetic-v1")
        digest = hashlib.sha256(build_contents(list(self.document.pages.all())).encode()).hexdigest()
        self.item = PrescriptionBatchItem.objects.create(batch_job=self.job, document=self.document, request_key="synthetic-key", input_sha256=digest)
        self.row = {"response": {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(fixture["payload"])}]}}]}}

    def test_import_creates_new_evidence_and_replay_creates_nothing(self):
        result = import_batch_row(self.job, self.item.pk, self.row)
        self.assertEqual(result.status, "completed")
        self.assertEqual(ExtractionRun.objects.count(), 2)
        self.original.refresh_from_db()
        self.review.refresh_from_db()
        self.assertEqual(self.original.structured_data, {"synthetic_baseline": True})
        self.assertEqual(self.original.raw_response, "original immutable response")
        self.assertEqual(self.review.reviewed_data, {"reviewer_owned": "preserve"})
        import_batch_row(self.job, self.item.pk, self.row)
        self.assertEqual(ExtractionRun.objects.count(), 2)
        self.item.refresh_from_db()
        self.assertEqual(self.item.attempts, 1)

    def test_changed_input_cannot_be_imported_against_new_pages(self):
        self.document.pages.update(cleaned_text="Changed synthetic input")
        result = import_batch_row(self.job, self.item.pk, self.row)
        self.assertEqual(result.status, "failed")
        self.assertIn("invalid_output", result.error)
        self.assertEqual(ExtractionRun.objects.count(), 1)

    def test_legacy_envelope_digest_uses_immutable_invocation_source_digest(self):
        original_digest = self.item.input_sha256
        self.item.input_sha256 = hashlib.sha256(b"Synthetic legacy request envelope").hexdigest()
        self.item.save(update_fields=["input_sha256"])
        LLMInvocation.objects.create(document=self.document, batch_item=self.item, provider="gemini",
                                     request_kind="batch_generate_content", model_name="explicit-test-model",
                                     input_sha256=original_digest)
        result = import_batch_row(self.job, self.item.pk, self.row)
        self.assertEqual(result.status, "completed")
        self.assertEqual(ExtractionRun.objects.count(), 2)

    @override_settings(GOOGLE_API_KEY="synthetic-key", PRESCRIPTION_EXTRACTION_MODEL="explicit-test-model")
    def test_real_submission_path_and_import_agree_on_source_digest(self):
        self.document.status = PrescriptionDocument.Status.READY_FOR_REVIEW
        self.document.save(update_fields=["status"])
        source = build_contents(list(self.document.pages.all()))
        prepared = {"key": "synthetic-submission", "request": {"contents": [{"role": "user", "parts": [{"text": source}]}]}}
        with patch("prescriptions.services.batch._request_for", return_value=prepared), patch("google.genai.Client") as client:
            client.return_value.files.upload.return_value = SimpleNamespace(name="synthetic-upload")
            client.return_value.batches.create.return_value = SimpleNamespace(name="synthetic-job")
            job = create_batch_job(document_ids=[self.document.pk], user=None, display_name="Synthetic submission")
        item = job.items.get()
        self.assertEqual(item.input_sha256, hashlib.sha256(source.encode()).hexdigest())
        self.assertEqual(import_batch_row(job, item.pk, self.row).status, "completed")
