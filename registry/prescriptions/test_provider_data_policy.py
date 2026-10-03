"""No-network tests of both outbound Gemini data boundaries."""

from hashlib import sha256
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from prescriptions.models import ExtractionRun, LLMInvocation, PrescriptionBatchJob, PrescriptionDocument, PrescriptionPage
from prescriptions.services.batch import create_batch_job
from prescriptions.services.extraction import build_contents, extract_structured_data
from prescriptions.services.processing import process_document
from prescriptions.services.provider_data_policy import ProviderDataPolicyError, require_approved_gemini_input


@override_settings(
    GOOGLE_API_KEY="synthetic-test-key",
    PRESCRIPTION_EXTRACTION_MODEL="explicit-test-model",
    PRESCRIPTION_GEMINI_DATA_POLICY="disabled",
    PRESCRIPTION_GEMINI_DATA_APPROVAL_REFERENCE="",
    PRESCRIPTION_GEMINI_APPROVED_INPUT_SHA256=[],
)
class ProviderDataPolicyTests(TestCase):
    def setUp(self):
        self.document = PrescriptionDocument.objects.create(
            file="prescriptions/synthetic.txt", original_filename="synthetic.txt",
            sha256="a" * 64, status=PrescriptionDocument.Status.READY_FOR_REVIEW,
        )
        self.page = PrescriptionPage.objects.create(
            document=self.document, page_number=1,
            raw_text="Synthetic fixture. Diagnosis: lung carcinoma.",
            cleaned_text="Synthetic fixture. Diagnosis: lung carcinoma.",
        )
        self.input_text = build_contents([self.page])
        self.approval = dict(
            PRESCRIPTION_GEMINI_DATA_POLICY="approved_non_sensitive",
            PRESCRIPTION_GEMINI_DATA_APPROVAL_REFERENCE="synthetic-fixture-review-test",
            PRESCRIPTION_GEMINI_APPROVED_INPUT_SHA256=[sha256(self.input_text.encode()).hexdigest()],
        )

    @patch("google.genai.Client")
    def test_disabled_direct_call_is_skipped_before_client_creation(self, client):
        run = ExtractionRun.objects.create(document=self.document)
        with self.assertRaises(ProviderDataPolicyError):
            extract_structured_data([self.page], extraction_run=run)
        client.assert_not_called()
        invocation = LLMInvocation.objects.get(extraction_run=run)
        self.assertEqual(invocation.status, LLMInvocation.Status.SKIPPED)
        self.assertEqual(invocation.input_text, self.input_text)
        self.assertEqual(invocation.output_text, "")

    @patch("google.genai.Client")
    def test_disabled_batch_creates_no_job_and_never_uploads(self, client):
        with self.assertRaises(ProviderDataPolicyError):
            create_batch_job(document_ids=[self.document.pk], user=None, display_name="Synthetic test")
        client.assert_not_called()
        self.assertFalse(PrescriptionBatchJob.objects.exists())
        self.assertFalse(LLMInvocation.objects.exists())

    def test_only_exact_reviewed_input_is_allowed(self):
        with override_settings(**self.approval):
            require_approved_gemini_input(self.input_text)
            with self.assertRaises(ProviderDataPolicyError):
                require_approved_gemini_input(self.input_text + " Changed OCR or new facts.")

    def test_invalid_policy_missing_reference_and_malformed_hash_fail_closed(self):
        for change in (
            {"PRESCRIPTION_GEMINI_DATA_POLICY": "allow_everything"},
            {"PRESCRIPTION_GEMINI_DATA_APPROVAL_REFERENCE": ""},
            {"PRESCRIPTION_GEMINI_APPROVED_INPUT_SHA256": ["not-a-hash"]},
            {"PRESCRIPTION_GEMINI_APPROVED_INPUT_SHA256": []},
        ):
            with self.subTest(change=change), override_settings(**{**self.approval, **change}):
                with self.assertRaises(ProviderDataPolicyError):
                    require_approved_gemini_input(self.input_text)

    @patch("google.genai.Client")
    def test_approved_synthetic_direct_input_reaches_mock_provider(self, client):
        payload = {"patient": {}, "observations": [{"temporal_context": "unknown", "diagnoses": [{"diagnosis_in_details": {"value": "lung carcinoma", "source_text": "Diagnosis: lung carcinoma.", "page": 1, "confidence": 1}}]}], "unresolved_items": [], "warnings": []}
        client.return_value.models.generate_content.return_value = SimpleNamespace(
            text=json.dumps(payload), usage_metadata=None, response_id="synthetic-response",
        )
        with override_settings(**self.approval):
            data, _, _, _ = extract_structured_data([self.page])
        self.assertEqual(data, payload)
        self.assertEqual(client.return_value.models.generate_content.call_args.kwargs["contents"], self.input_text)

    @patch("google.genai.Client")
    def test_one_unapproved_document_blocks_entire_batch(self, client):
        other = PrescriptionDocument.objects.create(
            file="prescriptions/other.txt", original_filename="other.txt", sha256="b" * 64,
            status=PrescriptionDocument.Status.READY_FOR_REVIEW,
        )
        PrescriptionPage.objects.create(document=other, page_number=1, raw_text="Unreviewed synthetic text.")
        with override_settings(**self.approval), self.assertRaises(ProviderDataPolicyError):
            create_batch_job(document_ids=[self.document.pk, other.pk], user=None, display_name="Synthetic test")
        client.assert_not_called()
        self.assertFalse(PrescriptionBatchJob.objects.exists())
        self.assertFalse(LLMInvocation.objects.exists())

    @patch("google.genai.Client")
    def test_approved_synthetic_batch_reaches_mock_provider(self, client):
        client.return_value.files.upload.return_value = SimpleNamespace(name="synthetic-input-file")
        client.return_value.batches.create.return_value = SimpleNamespace(name="synthetic-batch")
        with override_settings(**self.approval):
            job = create_batch_job(document_ids=[self.document.pk], user=None, display_name="Synthetic test")
        self.assertEqual(job.status, PrescriptionBatchJob.Status.SUBMITTED)
        client.return_value.files.upload.assert_called_once()
        client.return_value.batches.create.assert_called_once()
        self.assertEqual(LLMInvocation.objects.get(batch_item__batch_job=job).input_text, self.input_text)

    @patch("google.genai.Client")
    def test_batch_api_returns_actionable_policy_error(self, client):
        user = get_user_model().objects.create_user(username="synthetic-policy-reviewer")
        self.document.uploaded_by = user
        self.document.save(update_fields=["uploaded_by"])
        api = APIClient()
        api.force_authenticate(user)
        response = api.post("/api/prescriptions/batch-jobs/", {"document_ids": [self.document.pk]}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(str(response.data["code"]), "provider_data_policy")
        client.assert_not_called()
        self.assertFalse(PrescriptionBatchJob.objects.exists())

    @patch("google.genai.Client")
    @patch("prescriptions.services.processing.extract_pages")
    def test_policy_block_retains_local_extraction_and_review_draft(self, extract_pages, client):
        extract_pages.return_value = [(1, self.page.raw_text, {"method": "synthetic-test"}, None, None)]
        run = process_document(self.document)
        client.assert_not_called()
        self.assertEqual(run.status, ExtractionRun.Status.COMPLETED)
        self.assertEqual(run.structured_data["gemini_status"], "policy_blocked")
        self.assertIn("canonical_draft", run.structured_data)
        self.assertEqual(run.structured_data["gemini_extraction"]["unresolved_items"][0]["type"], "provider_data_policy")
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, PrescriptionDocument.Status.READY_FOR_REVIEW)

    @override_settings(PRESCRIPTION_GEMINI_DATA_POLICY="enabled")
    def test_explicit_enabled_policy_does_not_require_non_sensitive_attestation(self):
        require_approved_gemini_input(self.input_text)
        require_approved_gemini_input(self.input_text + " Additional synthetic input.")

    @override_settings(PRESCRIPTION_GEMINI_DATA_POLICY="enabled")
    @patch("google.genai.Client")
    def test_enabled_input_reaches_mock_provider_without_billing_or_hash_gate(self, client):
        payload = {"patient": {}, "observations": [{"temporal_context": "unknown", "diagnoses": [{"diagnosis_in_details": {"value": "lung carcinoma", "source_text": "Diagnosis: lung carcinoma.", "page": 1, "confidence": 1}}]}], "unresolved_items": [], "warnings": []}
        client.return_value.models.generate_content.return_value = SimpleNamespace(text=json.dumps(payload), usage_metadata=None, response_id="synthetic-enabled-response")
        data, _, _, _ = extract_structured_data([self.page])
        self.assertEqual(data, payload)
        client.return_value.models.generate_content.assert_called_once()
        config = client.return_value.models.generate_content.call_args.kwargs["config"]
        self.assertIsNone(config.response_json_schema)
        self.assertEqual(config.response_mime_type, "application/json")
        self.assertIn("Actual form field contract", config.system_instruction)
