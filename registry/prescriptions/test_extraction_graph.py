from unittest.mock import patch
from hashlib import sha256
import json
from django.test import TransactionTestCase, override_settings
from prescriptions.models import PrescriptionDocument, ExtractionRun, PrescriptionReview, LLMInvocation
from prescriptions.evaluation.corpus import cases
from prescriptions.services.extraction import GeminiRateLimitError, build_contents
from prescriptions.services.extraction_graph import prepare_extraction_workflow, execute_extraction_workflow
from records.models import ClinicalObservation


class ExtractionGraphTests(TransactionTestCase):
    def setUp(self):
        self.document = PrescriptionDocument.objects.create(file="synthetic.pdf", original_filename="synthetic.pdf", sha256="a" * 64)
        case = cases()[0]
        self.page = self.document.pages.create(page_number=1, raw_text=case["pages"][0], cleaned_text=case["pages"][0])
        self.answer = (case["payload"], "{}", "synthetic", "synthetic")

    def test_success_and_replay_create_one_draft_without_clinical_writes(self):
        workflow = prepare_extraction_workflow(self.document, task_id="synthetic-task")
        with patch("prescriptions.services.extraction_graph.ensure_page_artifact", return_value=[self.page]) as local, patch("prescriptions.services.processing.extract_structured_data", return_value=self.answer) as provider:
            run = execute_extraction_workflow(workflow.pk)
            execute_extraction_workflow(workflow.pk)
        self.assertEqual(local.call_count, 1)
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(run.status, ExtractionRun.Status.COMPLETED)
        self.assertEqual(ExtractionRun.objects.count(), 1)
        self.assertEqual(PrescriptionReview.objects.count(), 1)
        self.assertFalse(ClinicalObservation.objects.exists())
        self.assertEqual(prepare_extraction_workflow(self.document, task_id="synthetic-task").pk, workflow.pk)

    def test_quota_resume_reuses_local_artifact(self):
        workflow = prepare_extraction_workflow(self.document, task_id="synthetic-quota")
        with patch("prescriptions.services.extraction_graph.ensure_page_artifact", return_value=[self.page]) as local, patch("prescriptions.services.processing.extract_structured_data", side_effect=[GeminiRateLimitError(retry_after_seconds=60), self.answer]) as provider:
            with self.assertRaises(GeminiRateLimitError):
                execute_extraction_workflow(workflow.pk)
            workflow.refresh_from_db()
            self.assertEqual(workflow.status, "waiting_provider")
            run = execute_extraction_workflow(workflow.pk)
        self.assertEqual(local.call_count, 1)
        self.assertEqual(provider.call_count, 2)
        self.assertEqual(run.status, ExtractionRun.Status.COMPLETED)
        self.assertEqual(ExtractionRun.objects.count(), 1)

    def test_exhausted_quota_finishes_exception_draft_without_another_call(self):
        workflow = prepare_extraction_workflow(self.document, task_id="synthetic-exhausted")
        with patch("prescriptions.services.extraction_graph.ensure_page_artifact", return_value=[self.page]) as local, patch("prescriptions.services.processing.extract_structured_data", side_effect=GeminiRateLimitError(retry_after_seconds=60)) as provider:
            with self.assertRaises(GeminiRateLimitError):
                execute_extraction_workflow(workflow.pk)
            run = execute_extraction_workflow(workflow.pk, provider_fallback_reason="Synthetic quota budget exhausted")
        self.assertEqual(local.call_count, 1)
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(run.status, "completed")
        self.assertEqual(run.structured_data["gemini_status"], "unavailable")
        self.assertTrue(PrescriptionReview.objects.exists())
        self.assertFalse(ClinicalObservation.objects.exists())

    @override_settings(PRESCRIPTION_AGENTIC_EXTRACTION_ENABLED=True, PRESCRIPTION_GEMINI_MAX_RETRIES=0)
    def test_celery_quota_exhaustion_returns_saved_exception_draft(self):
        from prescriptions.tasks import process_prescription_document
        with patch("prescriptions.services.extraction_graph.ensure_page_artifact", return_value=[self.page]), patch("prescriptions.services.processing.extract_structured_data", side_effect=GeminiRateLimitError(retry_after_seconds=60)) as provider:
            result = process_prescription_document.apply(args=(self.document.pk,), task_id="synthetic-terminal", throw=True).get()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(provider.call_count, 1)
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, "ready_for_review")
        self.assertTrue(PrescriptionReview.objects.exists())

    def test_mapping_failure_resumes_without_provider_repeat_and_preserves_edits(self):
        workflow = prepare_extraction_workflow(self.document, task_id="synthetic-crash")
        review = PrescriptionReview.objects.create(document=self.document, reviewed_data={"reviewer_owned": "Synthetic edit"})
        with patch("prescriptions.services.extraction_graph.ensure_page_artifact", return_value=[self.page]), patch("prescriptions.services.processing.extract_structured_data", return_value=self.answer) as provider:
            with patch("prescriptions.services.extraction_graph._normalize", side_effect=RuntimeError("Synthetic worker crash")):
                with self.assertRaises(RuntimeError):
                    execute_extraction_workflow(workflow.pk)
            execute_extraction_workflow(workflow.pk)
        self.assertEqual(provider.call_count, 1)
        review.refresh_from_db()
        self.assertEqual(review.reviewed_data, {"reviewer_owned": "Synthetic edit"})

    @override_settings(PRESCRIPTION_AGENTIC_EXTRACTION_ENABLED=True)
    def test_celery_upload_task_uses_stable_workflow_identity(self):
        from prescriptions.tasks import process_prescription_document
        with patch("prescriptions.services.extraction_graph.ensure_page_artifact", return_value=[self.page]), patch("prescriptions.services.processing.extract_structured_data", return_value=self.answer) as provider:
            first = process_prescription_document.apply(args=(self.document.pk,), task_id="synthetic-delivery", throw=True).get()
            second = process_prescription_document.apply(args=(self.document.pk,), task_id="synthetic-delivery", throw=True).get()
        self.assertEqual(first, second)
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(ExtractionRun.objects.count(), 1)

    def test_changed_document_cannot_resume_or_replace_review(self):
        workflow = prepare_extraction_workflow(self.document, task_id="synthetic-source")
        with patch("prescriptions.services.extraction_graph.ensure_page_artifact", return_value=[self.page]), patch("prescriptions.services.processing.extract_structured_data", side_effect=GeminiRateLimitError(retry_after_seconds=60)):
            with self.assertRaises(GeminiRateLimitError):
                execute_extraction_workflow(workflow.pk)
        PrescriptionDocument.objects.filter(pk=self.document.pk).update(sha256="b" * 64)
        with self.assertRaises(RuntimeError):
            execute_extraction_workflow(workflow.pk)
        self.assertFalse(PrescriptionReview.objects.exists())

    @override_settings(PRESCRIPTION_EXTRACTION_MODEL="synthetic-model", PRESCRIPTION_EXTRACTION_PROMPT_VERSION="synthetic-prompt")
    def test_audited_answer_survives_crash_before_provider_artifact_save(self):
        workflow = prepare_extraction_workflow(self.document, task_id="synthetic-audit")
        payload = cases()[0]["payload"]
        def answer(pages, *, extraction_run, quality_recovery):
            raw = json.dumps(payload)
            LLMInvocation.objects.create(document=self.document, extraction_run=extraction_run, status="succeeded",
                model_name="synthetic-model", prompt_version="synthetic-prompt", output_text=raw,
                input_sha256=sha256(build_contents(pages).encode()).hexdigest())
            return payload, raw, "synthetic-prompt", "synthetic-model"
        original_save = ExtractionRun.save
        def fail_provider_save(run, *args, **kwargs):
            if run.structured_data.get("workflow_provider_complete"):
                raise RuntimeError("Synthetic artifact save crash")
            return original_save(run, *args, **kwargs)
        with patch("prescriptions.services.extraction_graph.ensure_page_artifact", return_value=[self.page]), patch("prescriptions.services.processing.extract_structured_data", side_effect=answer) as provider:
            with patch.object(ExtractionRun, "save", fail_provider_save):
                with self.assertRaises(RuntimeError):
                    execute_extraction_workflow(workflow.pk)
            run = execute_extraction_workflow(workflow.pk)
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(run.structured_data["gemini_extraction"]["observations"], payload["observations"])
        self.assertEqual(run.status, "completed")


    @override_settings(PRESCRIPTION_AGENTIC_EXTRACTION_ENABLED=True)
    def test_celery_owns_delayed_quota_retry_without_holding_graph_worker(self):
        from celery.exceptions import Retry
        from prescriptions.tasks import process_prescription_document
        process_prescription_document.push_request(id="synthetic-delayed", retries=0)
        try:
            with patch("prescriptions.services.extraction_graph.ensure_page_artifact", return_value=[self.page]), patch("prescriptions.services.processing.extract_structured_data", side_effect=GeminiRateLimitError(retry_after_seconds=1800)), patch.object(process_prescription_document, "retry", side_effect=Retry()) as retry:
                with self.assertRaises(Retry):
                    process_prescription_document.run(self.document.pk)
            self.assertEqual(retry.call_args.kwargs["countdown"], 1800)
            workflow = self.document.workflow_runs.get()
            self.assertEqual(workflow.status, "waiting_provider")
            self.assertIsNone(workflow.lease_owner)
            self.assertIsNone(workflow.lease_expires_at)
        finally:
            process_prescription_document.pop_request()

    def test_approved_data_partition_changes_cannot_reuse_completed_stages(self):
        workflow = prepare_extraction_workflow(self.document, task_id="synthetic-partition")
        with patch("prescriptions.services.extraction_graph.ensure_page_artifact", return_value=[self.page]), patch("prescriptions.services.processing.extract_structured_data", return_value=self.answer) as provider:
            execute_extraction_workflow(workflow.pk)
            with override_settings(PRESCRIPTION_GEMINI_DATA_APPROVAL_REFERENCE="synthetic-new-review"):
                with self.assertRaisesMessage(ValueError, "partition changed"):
                    execute_extraction_workflow(workflow.pk)
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(ExtractionRun.objects.count(), 1)
        self.assertEqual(PrescriptionReview.objects.count(), 1)

    def test_completed_stage_replay_still_checks_current_model_version(self):
        workflow = prepare_extraction_workflow(self.document, task_id="synthetic-model-version")
        with patch("prescriptions.services.extraction_graph.ensure_page_artifact", return_value=[self.page]), patch("prescriptions.services.processing.extract_structured_data", return_value=self.answer) as provider:
            execute_extraction_workflow(workflow.pk)
            with override_settings(PRESCRIPTION_EXTRACTION_MODEL="synthetic-new-model"):
                with self.assertRaisesMessage(ValueError, "configuration changed"):
                    execute_extraction_workflow(workflow.pk)
        self.assertEqual(provider.call_count, 1)


    @override_settings(PRESCRIPTION_AGENTIC_EXTRACTION_ENABLED=True)
    def test_celery_structured_retry_changes_prompt_and_reuses_local_stage(self):
        from celery.exceptions import Retry
        from prescriptions.tasks import process_prescription_document
        from prescriptions.services.extraction import GeminiStructuredOutputError
        process_prescription_document.push_request(id="synthetic-quality-retry", retries=0)
        try:
            with patch("prescriptions.services.extraction_graph.ensure_page_artifact", return_value=[self.page]) as local, patch("prescriptions.services.processing.extract_structured_data", side_effect=[GeminiStructuredOutputError("Synthetic invalid output"), self.answer]) as provider:
                with patch.object(process_prescription_document, "retry", side_effect=Retry()) as retry:
                    with self.assertRaises(Retry):
                        process_prescription_document.run(self.document.pk)
                self.assertEqual(retry.call_args.kwargs["args"], (self.document.pk, True))
                result = process_prescription_document.run(self.document.pk, True)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(local.call_count, 1)
            self.assertEqual(provider.call_count, 2)
            self.assertTrue(provider.call_args.kwargs["quality_recovery"])
            self.assertEqual(ExtractionRun.objects.count(), 1)
        finally:
            process_prescription_document.pop_request()


@override_settings(PRESCRIPTION_DOCUMENT_BUDGET_ENABLED=True, PRESCRIPTION_DOCUMENT_MAX_ATTEMPTS=1, PRESCRIPTION_DOCUMENT_TOKEN_UNITS=100000, PRESCRIPTION_DOCUMENT_SECONDS=60, PRESCRIPTION_PROVIDER_MAX_OUTPUT_TOKENS=200)
class ExtractionDocumentBudgetTests(TransactionTestCase):
    setUp = ExtractionGraphTests.setUp
    def test_oversized_input_yields_saved_exception_draft_without_provider(self):
        workflow = prepare_extraction_workflow(self.document, task_id="synthetic-budget")
        with override_settings(PRESCRIPTION_DOCUMENT_TOKEN_UNITS=1), patch("prescriptions.services.extraction_graph.ensure_page_artifact",return_value=[self.page]), patch("prescriptions.services.processing.extract_structured_data") as provider:
            result = execute_extraction_workflow(workflow.pk)
        provider.assert_not_called()
        self.assertEqual(result.status,"completed")
        self.assertTrue(PrescriptionReview.objects.filter(document=self.document).exists())
        self.assertEqual(result.structured_data["gemini_status"],"unavailable")

    def test_second_ambiguous_attempt_falls_back_without_provider_redispatch(self):
        workflow = prepare_extraction_workflow(self.document, task_id="synthetic-budget-retry")
        with patch("prescriptions.services.extraction_graph.ensure_page_artifact",return_value=[self.page]), patch("prescriptions.services.processing.extract_structured_data",side_effect=GeminiRateLimitError(retry_after_seconds=30)) as provider:
            with self.assertRaises(GeminiRateLimitError):
                execute_extraction_workflow(workflow.pk)
            result = execute_extraction_workflow(workflow.pk)
        self.assertEqual(provider.call_count,1)
        self.assertEqual(result.status,"completed")
        workflow.refresh_from_db()
        self.assertEqual(workflow.versions["document_budget"]["attempts_reserved"],1)

    def test_new_workflow_cannot_reset_document_admission(self):
        first = prepare_extraction_workflow(self.document,task_id="synthetic-first")
        with patch("prescriptions.services.extraction_graph.ensure_page_artifact",return_value=[self.page]), patch("prescriptions.services.processing.extract_structured_data",return_value=self.answer) as provider:
            execute_extraction_workflow(first.pk)
            second = prepare_extraction_workflow(self.document,task_id="synthetic-second")
            result = execute_extraction_workflow(second.pk)
        self.assertEqual(provider.call_count,1)
        self.assertEqual(result.structured_data["gemini_status"],"unavailable")
        self.assertEqual(PrescriptionReview.objects.filter(document=self.document).count(),1)

    def test_late_provider_answer_cannot_prefill_canonical_review(self):
        from datetime import timedelta
        from django.utils import timezone
        from prescriptions.models import PrescriptionWorkflowRun
        workflow = prepare_extraction_workflow(self.document,task_id="synthetic-late")
        def late(*args,**kwargs):
            current = PrescriptionWorkflowRun.objects.get(pk=workflow.pk)
            current.versions["document_budget"]["deadline_at"] = (timezone.now()-timedelta(seconds=1)).isoformat()
            current.save()
            return self.answer
        with patch("prescriptions.services.extraction_graph.ensure_page_artifact",return_value=[self.page]), patch("prescriptions.services.processing.extract_structured_data",side_effect=late):
            result = execute_extraction_workflow(workflow.pk)
        self.assertEqual(result.structured_data["gemini_status"],"unavailable")
        self.assertEqual(result.raw_response,"")
        self.assertTrue(PrescriptionReview.objects.filter(document=self.document).exists())
