from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date
from rest_framework.test import APIClient

from options.models import (
    MolecularAlterationType,
    MolecularPanel,
    MolecularPanelTarget,
    MolecularPanelVersion,
    MolecularPathologyGene,
    MolecularPathologyExon,
    MolecularPathologyResult,
    TreatmentDrug,
    TreatmentModality,
    TreatmentProtocol,
    TreatmentProtocolDrug,
)
from records.models import ClinicalObservation, MolecularTest, MolecularTestResult, Patient, TreatmentAdministration, TreatmentCourse
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
        self.allowed_exon = MolecularPathologyExon.objects.create(gene=self.gene, name="19")
        self.target.covered_exons.add(self.allowed_exon)
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

        with self.assertRaises(ValidationError):
            MolecularTestResult.objects.create(
                molecular_test=self.molecular_test,
                gene=self.gene,
                alteration_type=self.alteration_type,
                result=derived_result.result,
            )

    def test_finalization_rejects_failed_qc(self):
        self.molecular_test.qc_status = MolecularTest.QCStatus.FAILED
        self.molecular_test.save()

        with self.assertRaisesMessage(ValidationError, "QC must pass"):
            finalize_molecular_test(self.molecular_test.pk)

    def test_finalization_rejects_an_exon_outside_target_coverage(self):
        wrong_exon = MolecularPathologyExon.objects.create(gene=self.gene, name="20")
        detected = MolecularPathologyResult.objects.create(code="detected", name="Detected")
        MolecularTestResult.objects.create(
            molecular_test=self.molecular_test,
            gene=self.gene,
            exon=wrong_exon,
            alteration_type=self.alteration_type,
            result=detected,
        )

        with self.assertRaisesMessage(ValidationError, "is not covered"):
            finalize_molecular_test(self.molecular_test.pk)

    def test_repeated_finalization_is_idempotent(self):
        finalize_molecular_test(self.molecular_test.pk)
        result = finalize_molecular_test(self.molecular_test.pk)

        self.assertTrue(result["already_completed"])
        self.assertEqual(result["created_negatives"], 0)

    def test_api_cannot_mark_a_test_completed_directly(self):
        user = get_user_model().objects.create_user(username="api-user", password="test-password")
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.patch(
            f"/api/records/molecular-tests/{self.molecular_test.pk}/",
            {"status": MolecularTest.Status.COMPLETED},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.molecular_test.refresh_from_db()
        self.assertEqual(self.molecular_test.status, MolecularTest.Status.DRAFT)

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


class TreatmentValidationTests(TestCase):
    def setUp(self):
        patient = Patient.objects.create(registration_no="REG-T1", patient_id="PAT-T1", name="Treatment Patient")
        other_patient = Patient.objects.create(registration_no="REG-T2", patient_id="PAT-T2", name="Other Patient")
        self.observation = ClinicalObservation.objects.create(patient=patient)
        self.other_observation = ClinicalObservation.objects.create(patient=other_patient)
        modality = TreatmentModality.objects.create(name="Systemic therapy")
        self.protocol = TreatmentProtocol.objects.create(name="Protocol A")
        self.protocol_drug = TreatmentDrug.objects.create(name="Drug A")
        self.other_drug = TreatmentDrug.objects.create(name="Drug B")
        TreatmentProtocolDrug.objects.create(protocol=self.protocol, drug=self.protocol_drug)
        self.course = TreatmentCourse.objects.create(
            observation=self.observation,
            modality=modality,
            protocol=self.protocol,
            started_on=date(2026, 1, 10),
        )

    def test_course_end_cannot_precede_start(self):
        course = TreatmentCourse(
            observation=self.observation,
            modality=self.course.modality,
            protocol=self.protocol,
            started_on=date(2026, 1, 10),
            ended_on=date(2026, 1, 9),
        )
        with self.assertRaisesMessage(ValidationError, "cannot precede"):
            course.full_clean()

    def test_administration_requires_protocol_drug_same_patient_and_valid_date(self):
        administration = TreatmentAdministration(
            treatment_course=self.course,
            observation=self.other_observation,
            drug=self.other_drug,
            administered_on=date(2026, 1, 9),
        )
        with self.assertRaises(ValidationError) as error:
            administration.full_clean()

        self.assertIn("observation", error.exception.message_dict)
        self.assertIn("drug", error.exception.message_dict)
        self.assertIn("administered_on", error.exception.message_dict)
