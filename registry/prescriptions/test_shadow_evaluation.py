from copy import deepcopy
from unittest.mock import patch
from django.test import SimpleTestCase
from prescriptions.evaluation.runner import evaluate_synthetic
from prescriptions.evaluation.corpus import cases


class ShadowEvaluationTests(SimpleTestCase):
    def test_shadow_parity_metrics_and_no_provider_or_database_access(self):
        # SimpleTestCase prohibits database access; provider dispatch is explicitly forbidden.
        with patch("google.genai.Client", side_effect=AssertionError("Provider dispatch forbidden")):
            report = evaluate_synthetic(shadow=True)
        self.assertTrue(report["passed"])
        self.assertEqual(len(report["cases"]), 10)
        self.assertTrue(all(case["baseline_parity"] for case in report["cases"]))
        self.assertTrue(all(metric["accuracy"] == 1 for metric in report["field_metrics"].values()))
        self.assertEqual(report["provider_calls"], 0)
        self.assertIn("observed reviewer corrections and time", report["unmeasured"])

    def test_omission_is_reported_per_field_and_fails_gate(self):
        fixture = deepcopy(cases()[0])
        fixture["expected"]["histopathologies.0.report_summary"] = "Missing synthetic annotation"
        with patch("prescriptions.evaluation.runner.cases", return_value=[fixture]):
            report = evaluate_synthetic(shadow=True)
        self.assertFalse(report["passed"])
        self.assertEqual(report["field_metrics"]["histopathologies.report_summary"]["omitted"], 1)

    def test_non_synthetic_input_cannot_be_evaluated(self):
        fixture = deepcopy(cases()[0])
        fixture["pages"] = ["Unapproved input"]
        with patch("prescriptions.evaluation.runner.cases", return_value=[fixture]), self.assertRaises(ValueError):
            evaluate_synthetic(shadow=True)
