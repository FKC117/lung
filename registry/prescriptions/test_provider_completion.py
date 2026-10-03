from types import SimpleNamespace
from django.test import SimpleTestCase
from prescriptions.services.extraction import GeminiStructuredOutputError, validate_provider_completion


class ProviderCompletionTests(SimpleTestCase):
    def test_partial_and_blocked_sdk_and_batch_answers_have_distinct_categories(self):
        for response, category in [
            (SimpleNamespace(candidates=[SimpleNamespace(finish_reason="MAX_TOKENS")]), "truncated"),
            ({"candidates": [{"finishReason": "SAFETY"}]}, "provider_blocked"),
            ({"promptFeedback": {"blockReason": "PROHIBITED_CONTENT"}}, "provider_blocked"),
            ({"candidates": [{"finishReason": "OTHER"}]}, "incomplete"),
        ]:
            with self.subTest(category=category):
                with self.assertRaises(GeminiStructuredOutputError) as caught:
                    validate_provider_completion(response)
                self.assertEqual(caught.exception.category, category)

    def test_stop_response_is_accepted(self):
        validate_provider_completion({"candidates": [{"finishReason": "STOP"}]})
