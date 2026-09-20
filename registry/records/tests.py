from django.core.exceptions import ValidationError
from django.test import TestCase

from options.models import (
    MolecularAlterationType,
    MolecularPanel,
    MolecularPanelTarget,
    MolecularPanelVersion,
    MolecularPathologyGene,
    MolecularPathologyResult,
)
from records.models import ClinicalObservation, MolecularTest, MolecularTestResult, Patient
from records.services.molecular import finalize_molecular_test


class MolecularFinalizationTests(TestCase):
    def setUp(self):
        patient = Patient.objects.create(
            registration_no="REG-001",
            patient_id="PAT-001",
            name="Test Patient",
        )
        observation = ClinicalObservation.objects.create(patient=patient)
        panel = MolecularPanel.objects.create(name="Lung panel")
        self.panel_version = MolecularPanelVersion.objects.create(
            panel=panel,
            version="1.0",
            reporting_policy=MolecularPanelVersion.ReportingPolicy.UNREPORTED_NEGATIVE,
        )
        self.gene = MolecularPathologyGene.objects.create(name="EGFR")
        self.alteration_type = MolecularAlterationType.objects.create(name="SNV")
        self.target = MolecularPanelTarget.objects.create(
            panel_version=self.panel_version,
            gene=self.gene,
            alteration_type=self.alteration_type,
        )
        MolecularPathologyResult.objects.create(code="not_detected", name="Not detected")
        self.molecular_test = MolecularTest.objects.create(
            observation=observation,
            panel_version=self.panel_version,
            qc_status=MolecularTest.QCStatus.PASSED,
        )

    def test_finalization_creates_missing_negative_and_locks_test(self):
        result = finalize_molecular_test(self.molecular_test.pk)

        self.molecular_test.refresh_from_db()
        derived_result = self.molecular_test.results.get()

        self.assertFalse(result["already_completed"])
        self.assertEqual(result["created_negatives"], 1)
        self.assertEqual(self.molecular_test.status, MolecularTest.Status.COMPLETED)
        self.assertEqual(derived_result.panel_target, self.target)
        self.assertEqual(derived_result.origin, MolecularTestResult.Origin.DERIVED)

        self.molecular_test.notes = "late edit"
        with self.assertRaises(ValidationError):
            self.molecular_test.save()

        derived_result.notes = "late edit"
        with self.assertRaises(ValidationError):
            derived_result.save()

    def test_finalization_rejects_a_linked_target_with_mismatched_gene(self):
        other_gene = MolecularPathologyGene.objects.create(name="ALK")
        other_target = MolecularPanelTarget.objects.create(
            panel_version=self.panel_version,
            gene=other_gene,
            alteration_type=self.alteration_type,
        )
        detected = MolecularPathologyResult.objects.create(code="detected", name="Detected")
        MolecularTestResult.objects.create(
            molecular_test=self.molecular_test,
            panel_target=other_target,
            gene=self.gene,
            alteration_type=self.alteration_type,
            result=detected,
        )

        with self.assertRaisesMessage(ValidationError, "must match its panel target"):
            finalize_molecular_test(self.molecular_test.pk)
