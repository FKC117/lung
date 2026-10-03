from copy import deepcopy
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from prescriptions.evaluation.corpus import cases
from prescriptions.services.field_contract import contract, fields, extraction_schema, option_fields
from prescriptions.services.intake_draft import build_intake_draft
from prescriptions.services.draft_evidence import verify_review_evidence
from prescriptions.services.draft_schema import COLLECTIONS


class FieldContractTests(SimpleTestCase):
    def test_mapping_exceptions_link_to_stable_record_and_observation_ids(self):
        draft = build_intake_draft({"gemini_extraction": {"observations": [{"histopathologies": [{"unsupported_detail": "Synthetic fact"}]}]}},
            document_id=1, resolve_options=False)
        observation = draft["observations"][0]
        issue = next(item for item in draft["unresolved_items"] if item["type"] == "unsupported_field")
        self.assertEqual(issue["record_temp_id"], observation["histopathologies"][0]["temp_id"])
        self.assertEqual(issue["observation_temp_id"], observation["temp_id"])

    def test_contract_covers_every_collection_and_provider_field(self):
        self.assertEqual(set(contract()["collections"]), set(COLLECTIONS))
        schema = extraction_schema()
        properties = schema["properties"]["observations"]["items"]["properties"]
        for collection in COLLECTIONS:
            self.assertEqual(set(properties[collection]["items"]["properties"]), {key for key, field in fields(collection).items() if not field.get("readOnly")})
            for key, resource in option_fields()[collection].items():
                self.assertIsInstance(resource, str)

    def test_synthetic_corpus_mapping_and_exception_expectations(self):
        for case in cases():
            with self.subTest(case=case["id"]):
                pages = [SimpleNamespace(page_number=i + 1, cleaned_text=text, raw_text=text) for i, text in enumerate(case["pages"])]
                draft = build_intake_draft({"gemini_extraction": case["payload"]}, document_id=1, resolve_options=False, pages=pages)
                observation = draft["observations"][0]
                for path, expected in case["expected"].items():
                    collection, index, key = path.split(".")
                    self.assertEqual(observation[collection][int(index)]["values"][key], expected)
                for path in case.get("absent", []):
                    collection, index, key = path.split(".")
                    self.assertFalse(observation[collection][int(index)]["values"].get(key))
                self.assertTrue(set(case["exceptions"]) <= {issue["type"] for issue in draft["unresolved_items"]})
                source_facts = sum(len(record) for records in case["payload"]["observations"][0].values() if isinstance(records, list) for record in records)
                dispositions = [fact for collection in COLLECTIONS for record in observation[collection] for fact in record["fact_dispositions"]]
                self.assertEqual(len(dispositions), source_facts)

    def test_original_values_are_not_changed_by_canonical_edits_or_record_moves(self):
        case = cases()[1]
        original = build_intake_draft({"gemini_extraction": case["payload"]}, document_id=1, resolve_options=False)
        edited = deepcopy(original)
        record = edited["observations"][0]["histopathologies"][0]
        record["values"]["histopathology_type"] = 99
        verify_review_evidence(original, edited)
        record["extracted_values"]["histopathology_type"] = "Fabricated replacement"
        with self.assertRaises(ValidationError):
            verify_review_evidence(original, edited)

    def test_source_quote_changes_are_rejected(self):
        original = build_intake_draft({"gemini_extraction": cases()[0]["payload"]}, document_id=1, resolve_options=False)
        edited = deepcopy(original)
        edited["observations"][0]["evidence_refs"][0]["source_text"] = "Changed quote"
        with self.assertRaises(ValidationError):
            verify_review_evidence(original, edited)

    def test_changing_record_identity_does_not_allow_rewriting_provenance(self):
        original = build_intake_draft({"gemini_extraction": cases()[0]["payload"]}, document_id=1, resolve_options=False)
        edited = deepcopy(original)
        edited["observations"][0]["histopathologies"][0]["temp_id"] = "fabricated-identity"
        with self.assertRaises(ValidationError):
            verify_review_evidence(original, edited)
