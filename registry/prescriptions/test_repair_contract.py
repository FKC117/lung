from prescriptions.evaluation.evidence_fixture import evidence_backed_fixture
from copy import deepcopy
from types import SimpleNamespace
from django.test import SimpleTestCase
from django.core.exceptions import ValidationError
from prescriptions.services.draft_schema import normalize_extraction
from prescriptions.services.repair_contract import prepare_repair_request, validate_repair_proposal


class TargetedRepairContractTests(SimpleTestCase):
    def setUp(self):
        self.draft = normalize_extraction(evidence_backed_fixture({"gemini_extraction": {"observations": [{"histopathologies": [{"biopsy_date": {
            "value": "invalid synthetic date", "page": 1, "source_text": "Synthetic biopsy date 2020-01-02"}, "report_summary": "Synthetic reviewer summary"}]}]}}), document_id=1)
        self.record = self.draft["observations"][0]["histopathologies"][0]
        self.pages = [SimpleNamespace(page_number=1, cleaned_text="Synthetic biopsy date 2020-01-02", raw_text="")]
        self.args = {"collection": "histopathologies", "record_id": self.record["temp_id"], "field_names": ["biopsy_date"],
            "source_sections": [{"page": 1, "source_text": "Synthetic biopsy date 2020-01-02"}], "pages": self.pages, "revision": 3, "document_sha256": "a" * 64}
        self.payload = {"patches": {"biopsy_date": {"value": "2020-01-02", "page": 1, "source_text": "Synthetic biopsy date 2020-01-02"}}}

    def check(self, request, payload=None, draft=None, revision=3, source="a" * 64):
        return validate_repair_proposal(request, payload or self.payload, current_draft=draft or self.draft, current_revision=revision, document_sha256=source)

    def test_supported_proposal_preserves_draft_and_original_evidence(self):
        before = deepcopy(self.draft)
        request = prepare_repair_request(self.draft, **self.args)
        proposal = self.check(request)
        self.assertEqual(proposal["patches"]["biopsy_date"]["value"], "2020-01-02")
        self.assertEqual(self.draft, before)
        self.assertEqual(request["fields"], ["biopsy_date"])
        self.assertNotIn("patient", request)

    def test_only_affected_supported_fields_and_bounded_verified_sections(self):
        for changes in ({"field_names": ["report_summary"]}, {"field_names": ["patient_id"]}, {"field_names": ["biopsy_date", "biopsy_date"]},
                        {"source_sections": [{"page": 2, "source_text": "Synthetic biopsy date 2020-01-02"}]},
                        {"source_sections": [{"page": 1, "source_text": "Missing synthetic source"}]},
                        {"source_sections": [{"page": 1, "source_text": "a" * 3001}]}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                prepare_repair_request(self.draft, **{**self.args, **changes})

    def test_tool_patient_extra_field_and_unbacked_value_injection_fail(self):
        request = prepare_repair_request(self.draft, **self.args)
        for payload in ({**self.payload, "tool": "publish"}, {"patches": {"patient_id": 7}},
                        {"patches": {"biopsy_date": {"value": "2021-01-02", "page": 1, "source_text": "Synthetic biopsy date 2020-01-02"}}}):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                self.check(request, payload)

    def test_stale_review_source_and_reviewer_values_fail(self):
        request = prepare_repair_request(self.draft, **self.args)
        for changes in ({"revision": 4}, {"source": "b" * 64}):
            with self.assertRaises(ValidationError):
                self.check(request, **changes)
        edited = deepcopy(self.draft)
        edited["observations"][0]["histopathologies"][0]["values"]["biopsy_date"] = "2022-01-02"
        with self.assertRaises(ValidationError):
            self.check(request, draft=edited)
        self.record["state"] = "edited"
        with self.assertRaises(ValidationError):
            prepare_repair_request(self.draft, **self.args)

    def test_request_snapshot_mutation_is_rejected(self):
        request = prepare_repair_request(self.draft, **self.args)
        request["fields"].append("report_summary")
        with self.assertRaises(ValidationError):
            self.check(request)
