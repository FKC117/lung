from copy import deepcopy
from django.test import SimpleTestCase
from django.core.exceptions import ValidationError
from prescriptions.services.draft_schema import normalize_extraction, validate_draft
from prescriptions.services.draft_evidence import verify_review_evidence


class FactDecisionTests(SimpleTestCase):
    def setUp(self):
        self.draft = normalize_extraction({"gemini_extraction": {"patient": {"unknown_detail": "Synthetic original"}}}, document_id=1)

    def test_decisions_are_separate_and_original_evidence_is_preserved(self):
        edited = deepcopy(self.draft)
        edited["fact_decisions"] = [{"fact_id": "patient.unknown_detail", "action": "exclude", "reason": "Synthetic duplicate narrative"}]
        validate_draft(edited, check_database=False)
        verify_review_evidence(self.draft, edited)
        self.assertEqual(edited["source_facts"], self.draft["source_facts"])
        self.assertEqual(edited["patient"]["match_status"], "unresolved")

    def test_unknown_duplicate_and_unexplained_decisions_are_rejected(self):
        valid = {"fact_id": "patient.unknown_detail", "action": "reviewed", "reason": "Synthetic explanation"}
        for decisions in ([{**valid, "fact_id": "invented"}], [valid, valid], [{**valid, "reason": " "}], [{**valid, "action": "publish"}]):
            with self.subTest(decisions=decisions):
                draft = deepcopy(self.draft)
                draft["fact_decisions"] = decisions
                with self.assertRaises(ValidationError):
                    validate_draft(draft, check_database=False)
