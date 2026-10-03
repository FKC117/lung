from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from django.db import connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from unittest.mock import patch
from types import SimpleNamespace
from prescriptions.models import PrescriptionProviderBudget
from prescriptions.services.provider_budget import reserve_provider_budget, ProviderBudgetConfigurationError
from prescriptions.services.extraction import GeminiRateLimitError


@override_settings(PRESCRIPTION_PROVIDER_BUDGET_ENABLED=True, PRESCRIPTION_PROVIDER_BUDGET_SCOPE="synthetic-project",
                   PRESCRIPTION_EXTRACTION_MODEL="synthetic-model", PRESCRIPTION_PROVIDER_BUDGET_WINDOW_SECONDS=60,
                   PRESCRIPTION_PROVIDER_BUDGET_REQUESTS=1, PRESCRIPTION_PROVIDER_BUDGET_TOKEN_UNITS=0, PRESCRIPTION_PROVIDER_BUDGET_DAILY_REQUESTS=0)
class ProviderBudgetTests(TestCase):
    def reserve(self, texts=None):
        return reserve_provider_budget(texts or ["Synthetic source"], system_instruction="Synthetic instruction")

    def test_shared_single_and_batch_admission_cannot_exceed_window(self):
        self.reserve()
        with self.assertRaises(GeminiRateLimitError):
            self.reserve()
        self.assertEqual(PrescriptionProviderBudget.objects.get().requests_reserved, 1)

    def test_direct_provider_client_is_never_called_when_budget_is_exhausted(self):
        from prescriptions.services.extraction import extract_structured_data
        self.reserve()
        with override_settings(GOOGLE_API_KEY="synthetic-key"), patch("prescriptions.services.extraction.require_approved_gemini_input"), patch("google.genai.Client") as client:
            with self.assertRaises(GeminiRateLimitError):
                extract_structured_data([SimpleNamespace(page_number=1, document_id=None, cleaned_text="Synthetic source")])
        client.assert_not_called()

    @override_settings(PRESCRIPTION_PROVIDER_BUDGET_TOKEN_UNITS=10000, PRESCRIPTION_PROVIDER_MAX_OUTPUT_TOKENS=0)
    def test_token_budget_requires_an_output_cap(self):
        with self.assertRaises(ProviderBudgetConfigurationError):
            self.reserve()

    @override_settings(PRESCRIPTION_PROVIDER_BUDGET_TOKEN_UNITS=1000000, PRESCRIPTION_PROVIDER_MAX_OUTPUT_TOKENS=100)
    def test_token_reservation_includes_schema_instruction_and_output_cap(self):
        self.reserve()
        self.assertGreater(PrescriptionProviderBudget.objects.get().token_units_reserved, 100)

    def test_model_budgets_are_separate(self):
        self.reserve()
        with override_settings(PRESCRIPTION_EXTRACTION_MODEL="synthetic-other-model"):
            self.reserve()
        self.assertEqual(PrescriptionProviderBudget.objects.count(), 2)

    @override_settings(GOOGLE_API_KEY="synthetic-key")
    def test_batch_admission_shares_budget_and_creates_no_job_when_denied(self):
        from prescriptions.models import PrescriptionDocument, PrescriptionBatchJob
        from prescriptions.services.batch import create_batch_job
        document = PrescriptionDocument.objects.create(file="synthetic.pdf", original_filename="synthetic.pdf", sha256="3" * 64, status="ready_for_review")
        prepared = {"request": {"contents": [{"parts": [{"text": "Synthetic source"}]}]}}
        self.reserve()
        with patch("prescriptions.services.batch._request_for", return_value=prepared), patch("google.genai.Client") as client:
            with self.assertRaises(GeminiRateLimitError):
                create_batch_job(document_ids=[document.pk], user=None, display_name="Synthetic denied batch")
        client.assert_not_called()
        self.assertFalse(PrescriptionBatchJob.objects.exists())

    def test_local_retry_honors_window_longer_than_provider_backoff_cap(self):
        from prescriptions.services.provider_budget import ProviderBudgetExhausted
        from prescriptions.tasks import _gemini_retry_countdown
        task = SimpleNamespace(request=SimpleNamespace(retries=0))
        self.assertEqual(_gemini_retry_countdown(task, ProviderBudgetExhausted(retry_after_seconds=3600)), 3600)

    def test_oversize_batch_requires_configuration_change_instead_of_endless_retry(self):
        with self.assertRaises(ProviderBudgetConfigurationError):
            self.reserve(["Synthetic one", "Synthetic two"])
        self.assertFalse(PrescriptionProviderBudget.objects.exists())

    def test_expired_window_is_reset(self):
        self.reserve()
        PrescriptionProviderBudget.objects.update(window_started_at=timezone.now() - timedelta(seconds=61))
        self.reserve()
        self.assertEqual(PrescriptionProviderBudget.objects.get().requests_reserved, 1)

    @override_settings(PRESCRIPTION_PROVIDER_BUDGET_SCOPE="")
    def test_missing_scope_fails_closed(self):
        with self.assertRaises(ProviderBudgetConfigurationError):
            self.reserve()


@override_settings(PRESCRIPTION_PROVIDER_BUDGET_ENABLED=True, PRESCRIPTION_PROVIDER_BUDGET_SCOPE="synthetic-concurrent-project",
                   PRESCRIPTION_EXTRACTION_MODEL="synthetic-model", PRESCRIPTION_PROVIDER_BUDGET_WINDOW_SECONDS=60,
                   PRESCRIPTION_PROVIDER_BUDGET_REQUESTS=1, PRESCRIPTION_PROVIDER_BUDGET_TOKEN_UNITS=0, PRESCRIPTION_PROVIDER_BUDGET_DAILY_REQUESTS=0)
class ProviderBudgetConcurrencyTests(TransactionTestCase):
    def test_concurrent_workers_admit_only_one_request(self):
        def worker(_):
            try:
                reserve_provider_budget(["Synthetic source"], system_instruction="Synthetic instruction")
                return True
            except GeminiRateLimitError:
                return False
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(worker, range(2)))
        self.assertEqual(sum(result), 1)


@override_settings(PRESCRIPTION_PROVIDER_BUDGET_ENABLED=True, PRESCRIPTION_PROVIDER_BUDGET_SCOPE="synthetic-daily",
    PRESCRIPTION_EXTRACTION_MODEL="synthetic-model", PRESCRIPTION_PROVIDER_BUDGET_WINDOW_SECONDS=60,
    PRESCRIPTION_PROVIDER_BUDGET_REQUESTS=15, PRESCRIPTION_PROVIDER_BUDGET_TOKEN_UNITS=0,
    PRESCRIPTION_PROVIDER_BUDGET_DAILY_REQUESTS=2, PRESCRIPTION_PROVIDER_BUDGET_DAILY_TIMEZONE="America/Los_Angeles")
class DailyProviderBudgetTests(TestCase):
    def reserve(self, texts=None):
        reserve_provider_budget(texts or ["Synthetic source"], system_instruction="Synthetic instruction")

    def test_daily_exhaustion_rolls_back_minute_reservation(self):
        self.reserve(["Synthetic one", "Synthetic two"])
        before = list(PrescriptionProviderBudget.objects.order_by("scope_key").values_list("requests_reserved", flat=True))
        with self.assertRaises(GeminiRateLimitError) as raised:
            self.reserve()
        self.assertGreater(raised.exception.retry_after_seconds, 60)
        self.assertEqual(list(PrescriptionProviderBudget.objects.order_by("scope_key").values_list("requests_reserved", flat=True)), before)

    def test_reset_follows_pacific_midnight(self):
        from datetime import datetime, timezone as dt_timezone
        with patch("prescriptions.services.provider_budget.timezone.now", return_value=datetime(2026, 10, 3, 6, 59, tzinfo=dt_timezone.utc)):
            self.reserve(["Synthetic one", "Synthetic two"])
        with patch("prescriptions.services.provider_budget.timezone.now", return_value=datetime(2026, 10, 3, 7, 0, tzinfo=dt_timezone.utc)):
            self.reserve()
        self.assertTrue(all(row.requests_reserved == 1 for row in PrescriptionProviderBudget.objects.all()))

    def test_new_daily_counter_conservatively_accounts_existing_audits(self):
        from prescriptions.models import LLMInvocation, PrescriptionDocument
        doc = PrescriptionDocument.objects.create(file="synthetic.txt", original_filename="synthetic.txt", sha256="a"*64)
        LLMInvocation.objects.create(document=doc, model_name="synthetic-model", status="failed", input_text="Synthetic", system_instruction="Synthetic", prompt_version="test", provider="gemini")
        self.reserve()
        with self.assertRaises(GeminiRateLimitError):
            self.reserve()

    @override_settings(PRESCRIPTION_PROVIDER_BUDGET_DAILY_TIMEZONE="invalid/timezone")
    def test_invalid_reset_zone_rolls_back_all_reservations(self):
        with self.assertRaises(ProviderBudgetConfigurationError):
            self.reserve()
        self.assertFalse(PrescriptionProviderBudget.objects.exists())
