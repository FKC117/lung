from prescriptions.evaluation.evidence_fixture import evidence_backed_fixture
from copy import deepcopy
from django.test import SimpleTestCase
from prescriptions.services.draft_schema import normalize_extraction
from prescriptions.services.fact_decisions import reconcile_fact_decisions


class CrossSourceRecordReconciliationTests(SimpleTestCase):
    def draft(self,summary="Synthetic carcinoma",date="2020-01-02"):
        return normalize_extraction(evidence_backed_fixture({"histopathology_candidates":[{"report_summary":"Synthetic carcinoma","biopsy_date":"2020-01-02"}],"gemini_extraction":{"observations":[{"histopathologies":[{"report_summary":summary,"biopsy_date":date}]}]}}),document_id=1)

    def test_overlap_is_visible_and_preserved_until_checked_decisions(self):
        draft=self.draft()
        self.assertEqual(len(draft["observations"]),2)
        self.assertTrue(all(obs["observed_at"] is None for obs in draft["observations"]))
        self.assertEqual(sum(len(obs["histopathologies"]) for obs in draft["observations"]),2)
        self.assertTrue(any("overlap" in issue["reason"] for issue in draft["unresolved_items"]))
        self.assertTrue(all(fact["disposition"] == "unresolved" for fact in draft["source_facts"]))
        draft["fact_decisions"]=[{"fact_id":fact["fact_id"],"action":"reviewed","reason":"Synthetic reviewer confirmed distinct records"} for fact in draft["source_facts"]]
        checked=reconcile_fact_decisions(draft)
        self.assertFalse(any("overlap" in issue["reason"] for issue in checked["unresolved_items"]))
        self.assertEqual(sum(len(obs["histopathologies"]) for obs in checked["observations"]),2)

    def test_repeated_dated_events_are_preserved_without_overlap(self):
        draft=self.draft(date="2020-02-02")
        self.assertFalse(any(issue["type"] == "fact_decision_required" for issue in draft["unresolved_items"]))
        self.assertEqual(len(draft["observations"]),2)

    def test_same_date_conflicting_findings_remain_separate_and_visible(self):
        draft=self.draft(summary="Synthetic no carcinoma")
        summaries=[obs["histopathologies"][0]["values"]["report_summary"] for obs in draft["observations"]]
        self.assertEqual(set(summaries),{"Synthetic carcinoma","Synthetic no carcinoma"})
        self.assertTrue(any("findings differ" in issue["reason"] for issue in draft["unresolved_items"]))

    def test_explained_duplicate_exclusion_preserves_original_source_ledger(self):
        draft=self.draft()
        originals=deepcopy(draft["source_facts"])
        draft["observations"][0]["histopathologies"]=[]
        draft["fact_decisions"]=[{"fact_id":fact["fact_id"],"action":"exclude","reason":"Synthetic confirmed duplicate of deterministic record"} for fact in originals]
        checked=reconcile_fact_decisions(draft)
        self.assertEqual(checked["source_facts"],originals)
        self.assertFalse(any("overlap" in issue["reason"] for issue in checked["unresolved_items"]))
        self.assertEqual(len(checked["observations"][1]["histopathologies"]),1)
