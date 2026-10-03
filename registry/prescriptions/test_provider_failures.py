from datetime import datetime, timezone
from types import SimpleNamespace
from django.test import TestCase
from prescriptions.services.provider_failures import classify_provider_failure


class ProviderFailureTests(TestCase):
    def error(self, code, value=None):
        return SimpleNamespace(code=code, response=SimpleNamespace(headers={"Retry-After": value}))

    def test_categories_are_sanitized_and_permanent_failures_do_not_retry(self):
        for code, category, retryable in ((401,"authentication",False),(403,"authentication",False),(400,"configuration",False),(404,"configuration",False),(429,"quota",True),(503,"transient_service",True),(999,"unknown",False)):
            with self.subTest(code=code):
                outcome = classify_provider_failure(self.error(code))
                self.assertEqual((outcome.category,outcome.retryable),(category,retryable))

    def test_retry_guidance_supports_seconds_and_http_date_without_shortening(self):
        self.assertEqual(classify_provider_failure(self.error(429,"1800")).retry_after_seconds,1800)
        self.assertEqual(classify_provider_failure(self.error(503,"1.1")).retry_after_seconds,2)
        now = datetime(2020,1,1,tzinfo=timezone.utc)
        self.assertEqual(classify_provider_failure(self.error(429,"Wed, 01 Jan 2020 00:30:00 GMT"),now=now).retry_after_seconds,1800)
        self.assertIsNone(classify_provider_failure(self.error(429,"invalid")).retry_after_seconds)

    def test_daily_exhaustion_requires_explicit_structured_quota_identity(self):
        error = self.error(429,"3600")
        error.details = [{"violations": [{"quotaId": "RequestsPerDayPerProject"}]}]
        result = classify_provider_failure(error)
        self.assertEqual((result.category,result.retryable),("daily_exhaustion",False))
        self.assertEqual(result.retry_after_seconds,3600)
        error.details = [{"violations": [{"quotaId": "RequestsPerMinutePerProject"}]}]
        self.assertEqual(classify_provider_failure(error).category,"quota")

    def test_permanent_failures_preserve_exception_draft_without_retry(self):
        from unittest.mock import patch
        from prescriptions.services.processing import enrich_extraction
        from prescriptions.services.extraction import GeminiPermanentProviderError, GeminiTransientServiceError
        for category in ("authentication", "configuration", "daily_exhaustion"):
            with patch("prescriptions.services.processing.extract_structured_data", side_effect=GeminiPermanentProviderError(category)):
                result = enrich_extraction(SimpleNamespace(), [], {"warnings": []})
            self.assertEqual(result["gemini_extraction"]["unresolved_items"][0]["type"], "provider_" + category)
            self.assertEqual(result["gemini_status"], "unavailable")
        with patch("prescriptions.services.processing.extract_structured_data", side_effect=GeminiTransientServiceError(retry_after_seconds=1800)), self.assertRaises(GeminiTransientServiceError):
            enrich_extraction(SimpleNamespace(), [], {"warnings": []})

    def test_guided_retries_keep_delay_and_unguided_retries_add_jitter(self):
        from unittest.mock import patch
        from prescriptions.tasks import _gemini_retry_countdown
        from prescriptions.services.extraction import GeminiRateLimitError
        task = SimpleNamespace(request=SimpleNamespace(retries=0))
        self.assertEqual(_gemini_retry_countdown(task, GeminiRateLimitError(retry_after_seconds=1800)),1800)
        with patch("prescriptions.tasks.random.randint",return_value=3):
            from django.conf import settings
            self.assertEqual(_gemini_retry_countdown(task,GeminiRateLimitError()),min(settings.PRESCRIPTION_GEMINI_RETRY_BASE_SECONDS,settings.PRESCRIPTION_GEMINI_RETRY_MAX_SECONDS)+3)

    def test_direct_provider_boundary_emits_only_sanitized_typed_errors(self):
        from unittest.mock import patch
        from hashlib import sha256
        from django.test import override_settings
        from prescriptions.services.extraction import extract_structured_data, build_contents, GeminiPermanentProviderError, GeminiTransientServiceError, GeminiRateLimitError
        pages = [SimpleNamespace(page_number=1,cleaned_text="SYNTHETIC FIXTURE ONLY",raw_text="",document_id=None)]
        digest = sha256(build_contents(pages).encode()).hexdigest()
        class SyntheticError(RuntimeError):
            pass
        with override_settings(GOOGLE_API_KEY="synthetic",PRESCRIPTION_EXTRACTION_MODEL="synthetic",PRESCRIPTION_GEMINI_DATA_POLICY="approved_non_sensitive",PRESCRIPTION_GEMINI_DATA_APPROVAL_REFERENCE="synthetic",PRESCRIPTION_GEMINI_APPROVED_INPUT_SHA256=[digest],PRESCRIPTION_PROVIDER_BUDGET_ENABLED=False):
            for code, expected in ((401,GeminiPermanentProviderError),(400,GeminiPermanentProviderError),(503,GeminiTransientServiceError),(429,GeminiRateLimitError)):
                error = SyntheticError("private provider message must not escape")
                error.code = code
                with self.subTest(code=code), patch("google.genai.Client") as client:
                    client.return_value.models.generate_content.side_effect = error
                    with self.assertRaises(expected) as caught:
                        extract_structured_data(pages)
                    self.assertNotIn("private provider",str(caught.exception))

    def test_audit_category_rejects_arbitrary_private_attributes(self):
        from prescriptions.services.provider_failures import audit_failure_category
        from prescriptions.services.extraction import GeminiStructuredOutputError
        self.assertEqual(audit_failure_category(GeminiStructuredOutputError("private", category="truncated")), "truncated")
        error = RuntimeError("private patient content")
        error.category = "private patient content"
        self.assertEqual(audit_failure_category(error), "unknown")
        self.assertEqual(audit_failure_category(ValueError("private malformed output")), "invalid_output")
        error.code = 503
        self.assertEqual(audit_failure_category(error), "transient_service")
