from prescriptions.evaluation.evidence_fixture import evidence_backed_fixture
from copy import deepcopy
from django.test import SimpleTestCase, TestCase
from django.core.exceptions import ValidationError
from prescriptions.services.draft_schema import normalize_extraction
from prescriptions.services.fact_decisions import reconcile_fact_decisions, validate_clinical_fact_coverage


class FactReconciliationTests(SimpleTestCase):
    def test_unplaced_patient_and_context_facts_need_checked_decisions(self):
        draft = normalize_extraction(evidence_backed_fixture({"gemini_extraction": {"patient": {"patient_identifier": "SYNTHETIC", "unknown_detail": "Synthetic"},
            "observations": [{"unknown_context": "Synthetic context"}]}}), document_id=1)
        with self.assertRaises(ValidationError):
            validate_clinical_fact_coverage(draft)
        draft["fact_decisions"] = [{"fact_id": fact["fact_id"], "action": "exclude", "reason": "Synthetic unsupported detail excluded"} for fact in draft["source_facts"]]
        result = reconcile_fact_decisions(draft)
        validate_clinical_fact_coverage(result)
        self.assertFalse(result["unresolved_items"])
        self.assertNotIn("unknown_detail", result["patient"]["values"])
        self.assertEqual(result["patient"]["match_status"], "unresolved")
        self.assertEqual(result["source_facts"], draft["source_facts"])
        result["fact_decisions"] = []
        self.assertTrue(reconcile_fact_decisions(result)["unresolved_items"])

    def test_identity_decision_cannot_select_patient_or_override_deterministic_identity(self):
        draft = normalize_extraction(evidence_backed_fixture({"patient": {"registration_no": "DETERMINISTIC-SYNTHETIC"},
            "gemini_extraction": {"patient": {"patient_identifier": "PROVIDER-SYNTHETIC"}}}), document_id=1)
        draft["fact_decisions"] = [{"fact_id": "patient.patient_identifier", "action": "reviewed", "reason": "Synthetic"}]
        with self.assertRaises(ValidationError):
            reconcile_fact_decisions(draft)
        draft["fact_decisions"][0]["action"] = "exclude"
        result = reconcile_fact_decisions(draft)
        self.assertEqual(result["patient"]["values"]["registration_no"], "DETERMINISTIC-SYNTHETIC")
        self.assertIsNone(result["patient"]["patient_id"])

    def test_checked_context_evidence_does_not_clear_another_observation(self):
        from prescriptions.services.intake_draft import build_intake_draft
        draft = build_intake_draft(evidence_backed_fixture({"gemini_extraction": {"observations": [{"prescription_date": {
            "value": "2020-01-01", "source_text": "Synthetic missing", "page": 1}}, {"prescription_date": {
            "value": "2020-01-02", "source_text": "Synthetic missing", "page": 1}}]}}), document_id=1, resolve_options=False, pages=[])
        draft["fact_decisions"] = [{"fact_id": "observations.0.prescription_date", "action": "reviewed", "reason": "Synthetic source manually checked"}]
        result = reconcile_fact_decisions(draft)
        remaining = [item for item in result["unresolved_items"] if item["type"] == "unsupported_evidence"]
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["observation_temp_id"], draft["observations"][1]["temp_id"])
        with self.assertRaises(ValidationError):
            validate_clinical_fact_coverage(result)

    def test_clearing_mapped_fields_requires_exclusion_even_when_record_remains(self):
        draft = normalize_extraction(evidence_backed_fixture({"gemini_extraction": {"patient": {"name": "Synthetic name"}, "observations": [{
            "prescription_date": "2020-01-01", "histopathologies": [{"report_summary": "Synthetic original"}]}]}}), document_id=1)
        draft["observations"][0]["histopathologies"][0]["values"]["report_summary"] = ""
        with self.assertRaises(ValidationError):
            validate_clinical_fact_coverage(draft)
        draft["fact_decisions"] = [{"fact_id": "observations.0.histopathologies.0.report_summary", "action": "exclude", "reason": "Synthetic duplicate"}]
        validate_clinical_fact_coverage(reconcile_fact_decisions(draft))
        draft["patient"]["values"]["name"] = ""
        with self.assertRaises(ValidationError):
            validate_clinical_fact_coverage(draft)

    def test_empty_catalog_field_requires_clearing_before_checked_exclusion(self):
        draft = normalize_extraction(evidence_backed_fixture({"gemini_extraction": {"observations": [{"histopathologies": [{"histopathology_type": "Synthetic unknown histology"}]}]}}), document_id=1)
        record = draft["observations"][0]["histopathologies"][0]
        record["resolutions"]["histopathology_type"] = {"status": "unresolved", "option_id": None, "resource": "histopathology-types", "raw_value": "Synthetic unknown histology"}
        draft["fact_decisions"] = [{"fact_id": "observations.0.histopathologies.0.histopathology_type", "action": "exclude", "reason": "Synthetic optional fact excluded"}]
        with self.assertRaises(ValidationError):
            reconcile_fact_decisions(draft)
        record["values"]["histopathology_type"] = ""
        result = reconcile_fact_decisions(draft)
        self.assertNotIn("histopathology_type", result["observations"][0]["histopathologies"][0]["resolutions"])
        self.assertEqual(result["source_facts"], draft["source_facts"])

    def test_deleting_originally_mapped_record_requires_explicit_exclusion(self):
        draft = normalize_extraction(evidence_backed_fixture({"gemini_extraction": {"observations": [{"histopathologies": [{"report_summary": "Synthetic original summary"}]}]}}), document_id=1)
        self.assertEqual(draft["source_facts"][0]["disposition"], "mapped")
        draft["observations"][0]["histopathologies"] = []
        for decisions in ([], [{"fact_id": draft["source_facts"][0]["fact_id"], "action": "reviewed", "reason": "Synthetic review"}]):
            draft["fact_decisions"] = decisions
            with self.assertRaises(ValidationError):
                validate_clinical_fact_coverage(draft)
        draft["fact_decisions"][0]["action"] = "exclude"
        validate_clinical_fact_coverage(reconcile_fact_decisions(draft))

    def test_moving_mapped_record_preserves_coverage_by_stable_identity(self):
        draft = normalize_extraction(evidence_backed_fixture({"gemini_extraction": {"observations": [{"histopathologies": [{"report_summary": "Synthetic original summary"}]}, {}]}}), document_id=1)
        record = draft["observations"][0]["histopathologies"].pop()
        draft["observations"][1]["histopathologies"].append(record)
        validate_clinical_fact_coverage(draft)

    def setUp(self):
        self.draft = normalize_extraction(evidence_backed_fixture({"gemini_extraction": {"observations": [{"histopathologies": [{"unsupported_detail": "Synthetic original"}]}]}}), document_id=1)
        self.identity = "observations.0.histopathologies.0.unsupported_detail"

    def test_exclusion_removes_only_checked_unsupported_value_and_keeps_evidence(self):
        self.draft["fact_decisions"] = [{"fact_id": self.identity, "action": "exclude", "reason": "Synthetic duplicate narrative"}]
        self.draft["unresolved_items"].append({"type": "chronology", "reason": "Unrelated synthetic ambiguity"})
        result = reconcile_fact_decisions(self.draft)
        self.assertNotIn("unsupported_detail", result["observations"][0]["histopathologies"][0]["values"])
        self.assertEqual(result["source_facts"], self.draft["source_facts"])
        self.assertIn("unsupported_detail", self.draft["observations"][0]["histopathologies"][0]["values"])
        self.assertEqual([item["type"] for item in result["unresolved_items"]], ["chronology"])
        validate_clinical_fact_coverage(result)
        result["fact_decisions"] = []
        with self.assertRaises(ValidationError):
            validate_clinical_fact_coverage(result)

    def test_reviewed_annotation_cannot_resolve_unsupported_field(self):
        self.draft["fact_decisions"] = [{"fact_id": self.identity, "action": "reviewed", "reason": "Synthetic explanation"}]
        with self.assertRaises(ValidationError):
            reconcile_fact_decisions(self.draft)

    def test_supported_corrected_date_rechecks_value_before_resolving(self):
        draft = normalize_extraction(evidence_backed_fixture({"gemini_extraction": {"observations": [{"histopathologies": [{"biopsy_date": "invalid synthetic date"}]}]}}), document_id=1)
        draft["fact_decisions"] = [{"fact_id": "observations.0.histopathologies.0.biopsy_date", "action": "reviewed", "reason": "Synthetic date corrected"}]
        with self.assertRaises(ValidationError):
            reconcile_fact_decisions(draft)
        draft["observations"][0]["histopathologies"][0]["values"]["biopsy_date"] = "2020-01-01"
        result = reconcile_fact_decisions(draft)
        self.assertFalse(result["unresolved_items"])
        self.assertEqual(result["source_facts"], draft["source_facts"])


class FactDecisionAPITests(TestCase):
    def test_context_decisions_save_reload_audit_and_approve_without_provider_rerun(self):
        from records.models import Patient, ClinicalObservation
        from prescriptions.models import LLMInvocation
        draft = normalize_extraction(evidence_backed_fixture({"gemini_extraction": {"patient": {"patient_identifier": "PROVIDER-SYNTHETIC", "unknown_detail": "Synthetic detail"},
            "observations": [{"prescription_date": "2020-01-01", "unknown_context": "Synthetic duplicate", "histopathologies": [{"report_summary": "Synthetic summary"}]}]}}), document_id=self.review.document_id)
        self.review.reviewed_data = draft
        self.review.save()
        patient = Patient.objects.create(registration_no="SYNTHETIC-CONTEXT", patient_id="SYNTHETIC-CONTEXT", name="Synthetic patient")
        draft["patient"]["match_status"] = "existing"
        draft["patient"]["patient_id"] = patient.pk
        draft["fact_decisions"] = [{"fact_id": item["fact_id"], "action": "exclude", "reason": "Synthetic unsupported fact explicitly excluded"} for item in draft["source_facts"] if item["disposition"] == "unresolved"]
        saved = self.client.patch(self.url + "review/", {"reviewed_data": draft, "expected_revision": 1}, format="json")
        self.assertEqual(saved.status_code, 200, saved.data)
        self.review.refresh_from_db()
        self.assertEqual(self.review.reviewed_data["fact_decisions"], draft["fact_decisions"])
        self.assertTrue(self.review.changes.filter(field_path__contains="fact_decisions").exists())
        approved = self.client.post(self.url + "approve-review/", {"expected_revision": 2}, format="json")
        self.assertEqual(approved.status_code, 200, approved.data)
        self.assertEqual(approved.data["approved_revision"], 2)
        self.assertFalse(ClinicalObservation.objects.exists())
        self.assertFalse(LLMInvocation.objects.exists())

    def setUp(self):
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient
        from prescriptions.models import PrescriptionDocument, PrescriptionReview
        self.user = get_user_model().objects.create_user(username="synthetic-fact-reviewer")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        document = PrescriptionDocument.objects.create(file="synthetic.pdf", sha256="a" * 64, uploaded_by=self.user)
        self.draft = normalize_extraction(evidence_backed_fixture({"gemini_extraction": {"observations": [{"histopathologies": [{
            "report_summary": "Synthetic summary", "unsupported_detail": "Synthetic duplicate"}]}]}}), document_id=document.pk)
        self.review = PrescriptionReview.objects.create(document=document, reviewed_data=self.draft)
        self.url = f"/api/prescriptions/documents/{document.pk}/"

    def test_checked_exclusion_saves_revision_and_removal_restores_blocker(self):
        from records.models import ClinicalObservation
        from prescriptions.models import LLMInvocation
        draft = deepcopy(self.draft)
        draft["fact_decisions"] = [{"fact_id": "observations.0.histopathologies.0.unsupported_detail", "action": "exclude", "reason": "Synthetic duplicate excluded"}]
        saved = self.client.patch(self.url + "review/", {"reviewed_data": draft, "expected_revision": 1}, format="json")
        self.assertEqual(saved.status_code, 200, saved.data)
        self.assertEqual(saved.data["revision"], 2)
        current = saved.data["reviewed_data"]
        self.assertEqual(current["source_facts"], self.draft["source_facts"])
        self.assertFalse(current["unresolved_items"])
        self.assertNotIn("unsupported_detail", current["observations"][0]["histopathologies"][0]["values"])
        self.assertEqual(self.client.patch(self.url + "review/", {"reviewed_data": draft, "expected_revision": 1}, format="json").status_code, 409)
        current["fact_decisions"] = []
        removed = self.client.patch(self.url + "review/", {"reviewed_data": current, "expected_revision": 2}, format="json")
        self.assertEqual(removed.status_code, 200, removed.data)
        self.assertEqual(removed.data["reviewed_data"]["unresolved_items"][0]["type"], "fact_decision_required")
        self.assertEqual(self.client.post(self.url + "approve-review/", {"expected_revision": 3}, format="json").status_code, 400)
        self.assertFalse(ClinicalObservation.objects.exists())
        self.assertFalse(LLMInvocation.objects.exists())
