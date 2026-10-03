from types import SimpleNamespace
from django.test import SimpleTestCase
from prescriptions.services.extraction import validate_extraction
from prescriptions.services.intake_draft import build_intake_draft


class MarkerValueMappingTests(SimpleTestCase):
    def fixture(self, wrapped):
        quote = "Synthetic marker Alpha 12.5 on 2024-01-02"
        def evidence(value):
            return {"value": value, "source_text": quote, "page": 1, "confidence": 0.9}
        payload = {"patient": {}, "observations": [{"temporal_context": "unknown", "cancer_markers": [{"marker": evidence("Alpha"), "tested_on": evidence("2024-01-02"), "value": evidence(12.5) if wrapped else 12.5}]}], "warnings": [], "unresolved_items": []}
        return payload, [SimpleNamespace(page_number=1, cleaned_text=quote, raw_text=quote)]

    def test_value_named_field_does_not_swallow_other_record_fields(self):
        payload, pages = self.fixture(True)
        draft = build_intake_draft({"gemini_extraction": validate_extraction(payload)}, document_id=1, pages=pages, resolve_options=False)
        record = draft["observations"][0]["cancer_markers"][0]
        self.assertEqual(record["values"], {"marker": "Alpha", "tested_on": "2024-01-02", "value": 12.5})
        self.assertEqual(len(record["fact_dispositions"]), 3)

    def test_bare_numeric_value_is_retained_but_never_accepted_as_evidence_backed(self):
        payload, pages = self.fixture(False)
        draft = build_intake_draft({"gemini_extraction": validate_extraction(payload)}, document_id=1, pages=pages, resolve_options=False)
        record = draft["observations"][0]["cancer_markers"][0]
        self.assertEqual(record["values"]["marker"], "Alpha")
        self.assertIsNone(record["values"]["value"])
        self.assertEqual(record["extracted_values"]["value"], 12.5)
        fact = next(f for f in draft["source_facts"] if f.get("canonical_field") == "value")
        self.assertEqual(fact["raw_value"], 12.5)
        self.assertEqual(fact["disposition"], "unresolved")

    def test_bare_string_field_is_visible_but_requires_evidence_review(self):
        payload, pages = self.fixture(True)
        payload["observations"][0]["cancer_markers"][0]["marker"] = "Alpha"
        draft = build_intake_draft({"gemini_extraction": validate_extraction(payload)}, document_id=1, pages=pages, resolve_options=False)
        record = draft["observations"][0]["cancer_markers"][0]
        self.assertIsNone(record["values"]["marker"])
        self.assertEqual(record["extracted_values"]["marker"], "Alpha")
        self.assertEqual(record["state"], "unresolved")

    def test_nonfinite_bare_number_is_rejected(self):
        payload, _pages = self.fixture(False)
        payload["observations"][0]["cancer_markers"][0]["value"] = float("nan")
        with self.assertRaises(ValueError):
            validate_extraction(payload)
