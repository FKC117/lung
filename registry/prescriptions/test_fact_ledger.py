from prescriptions.evaluation.evidence_fixture import evidence_backed_fixture
from copy import deepcopy
from django.test import SimpleTestCase, TestCase
from django.core.exceptions import ValidationError
from prescriptions.services.draft_schema import normalize_extraction, validate_draft
from prescriptions.services.draft_evidence import verify_review_evidence


class SourceFactLedgerTests(SimpleTestCase):
    def test_unverified_context_evidence_is_not_accounted_as_mapped(self):
        from prescriptions.services.intake_draft import build_intake_draft
        draft = build_intake_draft(evidence_backed_fixture({"gemini_extraction": {"observations": [{"prescription_date": {
            "value": "2020-01-01", "source_text": "Missing synthetic quote", "page": 1}}]}}),
            document_id=1, resolve_options=False, pages=[])
        fact = next(item for item in draft["source_facts"] if item["source_path"] == "observations.0.prescription_date")
        self.assertEqual(fact["disposition"], "unresolved")
        self.assertIn("could not be verified", fact["reason"])

    def test_patient_context_unknown_fields_and_metadata_are_all_retained(self):
        payload = {"patient": {"name": {"value": "Synthetic patient", "source_text": "Synthetic quote", "page": 1},
                               "patient_identifier": "SYNTHETIC-ID", "unmapped_detail": ["Synthetic"], "unsupported_scalar": "Retained"},
                   "observations": [{"temporal_context": "historical", "observed_at": None,
                       "anthropometry": {"weight_kg": {"value": 60, "source_text": "60 kg", "page": 1}, "unknown_measurement": 7},
                       "histopathologies": [{"finding": "Synthetic pathology", "unknown_result": "Preserved"}], "unknown_context": "Preserved"}],
                   "warnings": ["Synthetic warning"]}
        draft = normalize_extraction(evidence_backed_fixture({"gemini_extraction": payload}), document_id=1)
        facts = {item["source_path"]: item for item in draft["source_facts"]}
        self.assertEqual(len(facts), 12)
        self.assertEqual(facts["patient.name"]["raw_value"], payload["patient"]["name"])
        self.assertEqual(facts["patient.patient_identifier"]["disposition"], "unresolved")
        self.assertEqual(facts["patient.unsupported_scalar"]["disposition"], "unresolved")
        self.assertNotIn("registration_no", draft["patient"]["values"])
        self.assertEqual(facts["observations.0.histopathologies.0.finding"]["disposition"], "mapped")
        self.assertEqual(facts["observations.0.unknown_context"]["raw_value"], "Preserved")
        self.assertEqual(facts["warnings"]["disposition"], "excluded")
        self.assertTrue(facts["warnings"]["reason"])

    def test_canonical_edits_cannot_delete_change_or_fabricate_source_facts(self):
        draft = normalize_extraction(evidence_backed_fixture({"gemini_extraction": {"patient": {"name": "Synthetic"}}}), document_id=1)
        edited = deepcopy(draft)
        edited["patient"]["values"]["name"] = "Corrected synthetic name"
        verify_review_evidence(draft, edited)
        for modification in ([], [{"fabricated": True}], None):
            edited["source_facts"] = modification
            with self.assertRaises(ValidationError):
                verify_review_evidence(draft, edited)

    def test_legacy_drafts_still_validate_and_duplicate_fact_ids_fail(self):
        draft = normalize_extraction(evidence_backed_fixture({}), document_id=1)
        validate_draft(draft, check_database=False)
        draft = normalize_extraction(evidence_backed_fixture({"gemini_extraction": {"patient": {"name": "Synthetic"}}}), document_id=1)
        draft["source_facts"].append(deepcopy(draft["source_facts"][0]))
        with self.assertRaises(ValidationError):
            validate_draft(draft, check_database=False)


class SourceFactPersistenceTests(TestCase):
    def test_review_save_reload_preserves_original_patient_and_context(self):
        from prescriptions.models import PrescriptionDocument, PrescriptionReview
        from prescriptions.serializers import PrescriptionReviewUpdateSerializer
        document = PrescriptionDocument.objects.create(file="synthetic.pdf", sha256="f" * 64)
        draft = normalize_extraction(evidence_backed_fixture({"gemini_extraction": {"patient": {"name": "Original synthetic"},
            "observations": [{"temporal_context": "historical", "prescription_date": "2020-01-01"}]}}), document_id=document.pk)
        review = PrescriptionReview.objects.create(document=document, reviewed_data=draft)
        review.refresh_from_db()
        edited = deepcopy(review.reviewed_data)
        edited["patient"]["values"]["name"] = "Corrected synthetic"
        edited["fact_decisions"] = [{"fact_id": "patient.name", "action": "reviewed", "reason": "Synthetic name correction checked"}]
        edited["observations"][0]["prescription_date"] = "2020-01-02"
        serializer = PrescriptionReviewUpdateSerializer(data={"reviewed_data": edited}, context={"document_id": document.pk, "previous_draft": review.reviewed_data})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        review.reviewed_data = serializer.validated_data["reviewed_data"]
        review.save(update_fields=["reviewed_data"])
        review.refresh_from_db()
        self.assertEqual(review.reviewed_data["source_facts"], draft["source_facts"])
        self.assertEqual(review.reviewed_data["fact_decisions"], edited["fact_decisions"])
        facts = {item["source_path"]: item for item in review.reviewed_data["source_facts"]}
        self.assertEqual(facts["patient.name"]["raw_value"], "Original synthetic")
        self.assertEqual(facts["observations.0.prescription_date"]["raw_value"], "2020-01-01")
