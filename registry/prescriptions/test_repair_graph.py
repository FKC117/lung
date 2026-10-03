import json
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import patch
from django.test import TransactionTestCase, override_settings
from prescriptions import test_repair_storage
from prescriptions.models import PrescriptionWorkflowRun, PrescriptionReview, LLMInvocation
from prescriptions.services.repair_graph import execute_repair_graph, outbound_contents, prepare_saved_repair
from prescriptions.services.extraction_graph import _data_partition
from prescriptions.services.provider_data_policy import ProviderDataPolicyError


@override_settings(PRESCRIPTION_REPAIR_ENABLED=True, GOOGLE_API_KEY="synthetic-key", PRESCRIPTION_EXTRACTION_MODEL="synthetic-model", PRESCRIPTION_REPAIR_MAX_ATTEMPTS=1, PRESCRIPTION_REPAIR_TOKEN_UNITS=20000, PRESCRIPTION_REPAIR_SECONDS=60, PRESCRIPTION_PROVIDER_MAX_OUTPUT_TOKENS=200, PRESCRIPTION_PROVIDER_BUDGET_ENABLED=False, PRESCRIPTION_GEMINI_DATA_POLICY="approved_non_sensitive", PRESCRIPTION_GEMINI_DATA_APPROVAL_REFERENCE="synthetic-test")
class TargetedRepairGraphTests(TransactionTestCase):
    def setUp(self):
        fixture = test_repair_storage.DurableRepairStorageTests()
        fixture.setUp()
        self.fixture = fixture
        fixture.run.refresh_from_db()
        fixture.run.versions = {**fixture.run.versions, "model": "synthetic-model", "data_partition": _data_partition(fixture.document)}
        fixture.run.save()
        self.state = {"run_id": str(fixture.run.pk), "owner": str(fixture.owner), "review_id": fixture.review.pk, "request": fixture.request}
        digest = sha256(outbound_contents(fixture.request).encode()).hexdigest()
        self.policy = override_settings(PRESCRIPTION_GEMINI_APPROVED_INPUT_SHA256=[digest])
        self.policy.enable()
        self.addCleanup(self.policy.disable)

    def test_actual_graph_persists_proposal_and_audit_and_replay_reuses_answer(self):
        response = SimpleNamespace(text=json.dumps(self.fixture.payload), usage_metadata=None, response_id="synthetic-response")
        with patch("google.genai.Client") as client:
            client.return_value.models.generate_content.return_value = response
            result = execute_repair_graph(self.state)
            replay = execute_repair_graph(self.state)
        self.assertEqual(result["proposal"], replay["proposal"])
        self.assertEqual(client.return_value.models.generate_content.call_count, 1)
        self.fixture.review.refresh_from_db()
        self.assertEqual(self.fixture.review.reviewed_data, self.fixture.draft)
        self.assertEqual(LLMInvocation.objects.get().request_kind, "targeted_repair")
        self.assertEqual(self.fixture.run.checkpoints.filter(namespace="repair-proposal").count(), 1)

    def test_unapproved_exact_input_never_dispatches(self):
        with override_settings(PRESCRIPTION_GEMINI_APPROVED_INPUT_SHA256=[]), patch("google.genai.Client") as client:
            with self.assertRaises(ProviderDataPolicyError):
                execute_repair_graph(self.state)
            client.assert_not_called()
        self.assertFalse(LLMInvocation.objects.exists())

    def test_uncertain_provider_failure_cannot_redispatch_and_draft_survives(self):
        with patch("google.genai.Client") as client:
            client.return_value.models.generate_content.side_effect = RuntimeError("synthetic fault")
            with self.assertRaises(RuntimeError):
                execute_repair_graph(self.state)
            with self.assertRaises(ValueError):
                execute_repair_graph(self.state)
            self.assertEqual(client.return_value.models.generate_content.call_count, 1)
        self.fixture.review.refresh_from_db()
        self.assertEqual(self.fixture.review.reviewed_data, self.fixture.draft)

    def test_changed_partition_and_disabled_flag_block_completed_replay(self):
        with override_settings(PRESCRIPTION_GEMINI_DATA_APPROVAL_REFERENCE="changed"), self.assertRaises(ValueError):
            execute_repair_graph(self.state)
        with override_settings(PRESCRIPTION_REPAIR_ENABLED=False), self.assertRaises(ValueError):
            execute_repair_graph(self.state)

    def test_prepare_uses_saved_revision_and_verified_source_then_reuses_run(self):
        from prescriptions.models import PrescriptionPage
        PrescriptionPage.objects.create(document=self.fixture.document, page_number=1, cleaned_text="Synthetic biopsy date 2020-01-02")
        args = {"collection": "histopathologies", "record_id": self.fixture.request["record_id"], "field_names": ["biopsy_date"], "source_sections": self.fixture.request["source_sections"]}
        run, request = prepare_saved_repair(self.fixture.review.pk, **args)
        repeated, _ = prepare_saved_repair(self.fixture.review.pk, **args)
        self.assertEqual(run.pk, repeated.pk)
        self.assertEqual(request["review_revision"], 3)
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            prepare_saved_repair(self.fixture.review.pk, **{**args, "field_names": ["patient_id"]})

    def test_celery_task_exhaustion_preserves_review_and_releases_lease(self):
        from prescriptions.models import PrescriptionPage
        from prescriptions.tasks import repair_prescription_section
        from prescriptions.services.workflow_state import release_workflow_lease
        PrescriptionPage.objects.create(document=self.fixture.document, page_number=1, cleaned_text="Synthetic biopsy date 2020-01-02")
        release_workflow_lease(self.fixture.run.pk, self.fixture.owner)
        with override_settings(PRESCRIPTION_REPAIR_TOKEN_UNITS=1), patch("google.genai.Client") as client:
            result = repair_prescription_section.run(self.fixture.review.pk, "histopathologies", self.fixture.request["record_id"], ["biopsy_date"], self.fixture.request["source_sections"])
        self.assertEqual(result["status"], "exception_draft")
        client.assert_not_called()
        self.fixture.run.refresh_from_db()
        self.assertIsNone(self.fixture.run.lease_owner)
        self.fixture.review.refresh_from_db()
        self.assertEqual(self.fixture.review.reviewed_data, self.fixture.draft)

    def test_completed_provider_stage_resumes_with_new_lease_after_storage_fault(self):
        from prescriptions.services.workflow_state import release_workflow_lease, acquire_workflow_lease
        response = SimpleNamespace(text=json.dumps(self.fixture.payload), usage_metadata=None, response_id="synthetic-response")
        with patch("google.genai.Client") as client:
            client.return_value.models.generate_content.return_value = response
            with patch("prescriptions.services.repair_graph.store_saved_proposal", side_effect=RuntimeError("synthetic storage fault")), self.assertRaises(RuntimeError):
                execute_repair_graph(self.state)
            release_workflow_lease(self.fixture.run.pk, self.fixture.owner, status="failed")
            owner = acquire_workflow_lease(self.fixture.run.pk)
            result = execute_repair_graph({**self.state, "owner": str(owner)})
            self.assertEqual(client.return_value.models.generate_content.call_count, 1)
        self.assertIn("proposal", result)
        self.assertEqual(LLMInvocation.objects.count(), 1)

    def test_reviewer_edit_during_provider_call_discards_response(self):
        def response(**kwargs):
            PrescriptionReview.objects.filter(pk=self.fixture.review.pk).update(revision=4)
            return SimpleNamespace(text=json.dumps(self.fixture.payload), usage_metadata=None, response_id="synthetic-response")
        with patch("google.genai.Client") as client:
            client.return_value.models.generate_content.side_effect = response
            with self.assertRaises(ValueError):
                execute_repair_graph(self.state)
        self.assertFalse(self.fixture.run.checkpoints.filter(namespace="repair-proposal").exists())
        self.fixture.review.refresh_from_db()
        self.assertEqual(self.fixture.review.reviewed_data, self.fixture.draft)

    def test_truncated_json_response_cannot_become_a_repair_proposal(self):
        from prescriptions.services.extraction import GeminiStructuredOutputError
        response = SimpleNamespace(text=json.dumps(self.fixture.payload), candidates=[SimpleNamespace(finish_reason="MAX_TOKENS")], usage_metadata=None, response_id="synthetic")
        with patch("google.genai.Client") as client:
            client.return_value.models.generate_content.return_value = response
            with self.assertRaises(GeminiStructuredOutputError):
                execute_repair_graph(self.state)
        self.assertEqual(LLMInvocation.objects.get().status, "failed")
        self.assertEqual(LLMInvocation.objects.get().output_text, response.text)
        self.assertFalse(self.fixture.run.checkpoints.filter(namespace="repair-proposal").exists())

    def test_checkpoint_failure_after_audited_answer_recovers_without_dispatch(self):
        from prescriptions.services.checkpoint import DjangoCheckpointSaver
        original = DjangoCheckpointSaver.put
        failed = []
        def put(saver, config, checkpoint, metadata, versions):
            if checkpoint.get("channel_values",{}).get("invocation_id") and not failed:
                failed.append(True)
                raise RuntimeError("synthetic checkpoint failure")
            return original(saver, config, checkpoint, metadata, versions)
        response = SimpleNamespace(text=json.dumps(self.fixture.payload),usage_metadata=None,response_id="synthetic")
        with patch("google.genai.Client") as client:
            client.return_value.models.generate_content.return_value = response
            with patch.object(DjangoCheckpointSaver,"put",put), self.assertRaises(RuntimeError):
                execute_repair_graph(self.state)
            result = execute_repair_graph(self.state)
            self.assertEqual(client.return_value.models.generate_content.call_count,1)
        self.assertTrue(failed)
        self.assertIn("proposal",result)
        self.assertEqual(LLMInvocation.objects.count(),1)
