from django.test import TestCase
from prescriptions.services.draft_schema import normalize_extraction
from prescriptions.services.option_resolver import resolve_draft_options, validate_selected_resolutions


class MultiSelectTextTests(TestCase):
    def test_scalar_text_stays_visible_and_unresolved_with_valid_resolution_shape(self):
        draft = normalize_extraction({"gemini_extraction": {"observations": [{"diagnoses": [{"metastatic_sites": {"value": "Synthetic unspecified sites", "page": 1, "source_text": "Synthetic unspecified sites", "confidence": 0.9}}]}]}}, document_id=1)
        resolved = resolve_draft_options(draft)
        validate_selected_resolutions(resolved)
        record = resolved["observations"][0]["diagnoses"][0]
        self.assertEqual(record["values"]["metastatic_sites"], "Synthetic unspecified sites")
        self.assertEqual(record["resolutions"]["metastatic_sites"]["option_ids"], [])
        self.assertEqual(record["resolutions"]["metastatic_sites"]["status"], "unresolved")
