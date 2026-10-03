from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from prescriptions.tasks import resume_prescription_extraction
from prescriptions.services.extraction import GeminiRateLimitError, GeminiStructuredOutputError


@override_settings(PRESCRIPTION_AGENTIC_EXTRACTION_ENABLED=True,PRESCRIPTION_GEMINI_MAX_RETRIES=2,PRESCRIPTION_GEMINI_OUTPUT_MAX_RETRIES=1)
class ResumeTaskRecoveryTests(SimpleTestCase):
    def test_quota_retry_keeps_original_identity_and_provider_delay(self):
        task=resume_prescription_extraction
        task.push_request(retries=0,id="synthetic-resume")
        try:
            with patch("prescriptions.services.extraction_graph.execute_extraction_workflow",side_effect=GeminiRateLimitError(retry_after_seconds=1800)), patch.object(task,"retry",side_effect=RuntimeError("synthetic retry")) as retry:
                with self.assertRaises(RuntimeError):
                    task.run("synthetic-workflow")
            self.assertEqual(retry.call_args.kwargs["countdown"],1800)
        finally:
            task.pop_request()

    def test_exhaustion_finishes_local_exception_draft_without_recursive_retry(self):
        task=resume_prescription_extraction
        task.push_request(retries=2,id="synthetic-terminal")
        try:
            answer=SimpleNamespace(pk=7,status="completed")
            with patch("prescriptions.services.extraction_graph.execute_extraction_workflow",side_effect=[GeminiRateLimitError(),answer]) as execute, patch.object(task,"retry") as retry:
                result=task.run("synthetic-workflow")
            retry.assert_not_called()
            self.assertEqual(result["status"],"completed")
            self.assertTrue(execute.call_args.kwargs["provider_fallback_reason"])
            self.assertEqual(execute.call_args.args,("synthetic-workflow",))
        finally:
            task.pop_request()

    def test_invalid_output_retry_changes_only_recovery_prompt(self):
        task=resume_prescription_extraction
        task.push_request(retries=0,id="synthetic-quality")
        try:
            with patch("prescriptions.services.extraction_graph.execute_extraction_workflow",side_effect=GeminiStructuredOutputError("synthetic")),patch.object(task,"retry",side_effect=RuntimeError("synthetic retry")) as retry:
                with self.assertRaises(RuntimeError):
                    task.run("synthetic-workflow")
            self.assertEqual(retry.call_args.kwargs["args"],("synthetic-workflow",True))
        finally:
            task.pop_request()
