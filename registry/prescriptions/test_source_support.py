from types import SimpleNamespace
from django.test import SimpleTestCase, override_settings
from prescriptions.services.intake_draft import build_intake_draft


class ClinicalSourceSupportTests(SimpleTestCase):
    def draft(self,value,quote,field="report_summary"):
        return build_intake_draft({"gemini_extraction":{"observations":[{"histopathologies":[{field:{"value":value,"page":1,"source_text":quote,"confidence":1.0}}]}]}},document_id=1,resolve_options=False,pages=[SimpleNamespace(page_number=1,cleaned_text=quote,raw_text=quote)])

    def test_existing_quote_cannot_support_invented_value_even_at_full_confidence(self):
        draft=self.draft("Adenocarcinoma","Synthetic small cell carcinoma")
        record=draft["observations"][0]["histopathologies"][0]
        self.assertIsNone(record["values"]["report_summary"])
        self.assertEqual(record["extracted_values"]["report_summary"],"Adenocarcinoma")
        self.assertEqual(record["state"],"unresolved")

    @override_settings(PRESCRIPTION_DATE_ORDER="DMY")
    def test_explicit_calendar_date_can_normalize_without_becoming_a_new_event(self):
        draft=self.draft("2020-02-22","Synthetic biopsy 22/02/2020", "biopsy_date")
        self.assertEqual(draft["observations"][0]["histopathologies"][0]["values"]["biopsy_date"],"2020-02-22")
        self.assertIsNone(draft["observations"][0]["observed_at"])

    @override_settings(PRESCRIPTION_DATE_ORDER="")
    def test_ambiguous_numeric_date_remains_exception(self):
        draft=self.draft("2020-03-02","Synthetic biopsy 02/03/2020", "biopsy_date")
        self.assertIsNone(draft["observations"][0]["histopathologies"][0]["values"]["biopsy_date"])

    def test_verified_literal_result_stays_prefilled(self):
        draft=self.draft("Small cell carcinoma","Synthetic Small cell carcinoma")
        self.assertEqual(draft["observations"][0]["histopathologies"][0]["values"]["report_summary"],"Small cell carcinoma")

    def test_prescription_cannot_become_administration_or_invented_diagnosis(self):
        for value, quote in (("administered", "Synthetic medication prescribed"),("lung cancer", "Synthetic carboplatin prescription"),("true", "Synthetic palliative treatment")):
            draft=self.draft(value,quote)
            self.assertIsNone(draft["observations"][0]["histopathologies"][0]["values"]["report_summary"])

    def test_positive_label_inside_negated_evidence_remains_exception(self):
        draft=self.draft("carcinoma","Synthetic no carcinoma")
        self.assertIsNone(draft["observations"][0]["histopathologies"][0]["values"]["report_summary"])
        negative=self.draft("no carcinoma","Synthetic no carcinoma")
        self.assertEqual(negative["observations"][0]["histopathologies"][0]["values"]["report_summary"],"no carcinoma")
