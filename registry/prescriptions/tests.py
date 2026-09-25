from copy import deepcopy

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from options.models import (
    DiagnosisDiseaseGroup,
    DiagnosisDiseaseSubgroup,
    Doctor,
    MolecularPathologyGene,
    MolecularPathologyResult,
    TreatmentDrug,
)
from records.models import ClinicalObservation, Diagnosis, MolecularTest, MolecularTestResult, Patient

from .models import ExtractionRun, PrescriptionDocument, PrescriptionReview
from .services.draft_schema import COLLECTIONS, empty_draft, empty_observation, normalize_extraction, validate_draft
from .services.extraction import validate_extraction
from .services.intake_draft import build_intake_draft
from .services.option_resolver import resolve_option


def record(temp_id="record-1", *, state="edited", values=None, evidence_refs=None):
    return {
        "temp_id": temp_id,
        "state": state,
        "values": values or {},
        "resolutions": {},
        "evidence_refs": evidence_refs or [],
    }


class DraftSchemaTests(TestCase):
    def test_normalization_preserves_multiple_observations_and_separates_evidence(self):
        source = {
            "gemini_extraction": {
                "patient": {"name": {"value": "Example Patient", "source_text": "Name: Example Patient", "page": 1, "confidence": 0.95}},
                "observations": [
                    {
                        "temporal_context": "historical",
                        "diagnoses": [{"diagnosis_in_details": {"value": "Earlier disease", "source_text": "Earlier disease", "page": 1, "confidence": 0.8}}],
                    },
                    {
                        "temporal_context": "planned",
                        "treatments": [{"protocol": {"value": "Planned protocol", "source_text": "Plan: Planned protocol", "page": 2, "confidence": 0.9}}],
                    },
                ],
                "unresolved_items": [],
                "warnings": [],
            }
        }

        draft = normalize_extraction(source, document_id=17)

        self.assertEqual(draft["schema_version"], 1)
        self.assertEqual(len(draft["observations"]), 2)
        diagnosis = draft["observations"][0]["diagnoses"][0]
        self.assertEqual(diagnosis["values"]["diagnosis_in_details"], "Earlier disease")
        self.assertNotIn("confidence", diagnosis["values"]["diagnosis_in_details"])
        evidence = draft["observations"][0]["evidence_refs"][0]
        self.assertEqual((evidence["source_text"], evidence["confidence"]), ("Earlier disease", 0.8))
        self.assertEqual(diagnosis["evidence_refs"], [evidence["evidence_id"]])

    def test_all_required_observation_collections_are_present(self):
        draft = empty_draft(3)
        draft["observations"].append(empty_observation())
        validate_draft(draft, document_id=3, check_database=False)
        self.assertTrue(all(name in draft["observations"][0] for name in COLLECTIONS))

    def test_duplicate_temporary_ids_are_rejected(self):
        draft = empty_draft(4)
        observation = empty_observation(temp_id="duplicate")
        observation["diagnoses"].append(record("duplicate"))
        draft["observations"].append(observation)
        with self.assertRaises(ValidationError):
            validate_draft(draft, document_id=4, check_database=False)

    def test_cross_observation_evidence_reference_is_rejected(self):
        draft = empty_draft(5)
        first = empty_observation(temp_id="first")
        first["evidence_refs"].append({
            "evidence_id": "evidence-1",
            "field_path": "diagnoses.0",
            "source_text": "Source",
            "page": 1,
            "confidence": 0.8,
        })
        second = empty_observation(temp_id="second")
        second["diagnoses"].append(record("diagnosis-1", evidence_refs=["evidence-1"]))
        draft["observations"] = [first, second]
        with self.assertRaises(ValidationError):
            validate_draft(draft, document_id=5, check_database=False)

    def test_extractor_database_ids_are_rejected(self):
        with self.assertRaisesMessage(ValueError, "database IDs"):
            validate_extraction({
                "patient": {},
                "observations": [{"temporal_context": "current", "diagnoses": [{"option_id": 99}]}],
                "unresolved_items": [],
                "warnings": [],
            })


class OptionResolutionTests(TestCase):
    def test_unique_exact_option_is_resolved_by_server_id(self):
        drug = TreatmentDrug.objects.create(name="Osimertinib")
        result = resolve_option("treatment-drugs", "osimertinib")
        self.assertEqual((result["status"], result["option_id"]), ("resolved", drug.pk))

    def test_extractor_match_metadata_is_not_copied_into_clinical_values(self):
        drug = TreatmentDrug.objects.create(name="Gefitinib")
        draft = build_intake_draft({
            "medications": [{
                "drug": {"value": "Gefitinib", "source_text": "Gefitinib", "page": 1, "confidence": 0.9},
                "drug_match": {"status": "resolved", "matched_option": {"option_id": 999999}},
            }]
        }, document_id=12)
        treatment = draft["observations"][0]["treatments"][0]
        self.assertNotIn("drug_match", treatment["values"])
        self.assertEqual(treatment["resolutions"]["drug"]["option_id"], drug.pk)

    def test_duplicate_names_remain_ambiguous(self):
        Doctor.objects.create(name="Same Doctor", bmdc_number="1")
        Doctor.objects.create(name="Same Doctor", bmdc_number="2")
        result = resolve_option("doctors", "Same Doctor")
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(len(result["candidates"]), 2)

    def test_context_scopes_a_non_unique_option(self):
        first_group = DiagnosisDiseaseGroup.objects.create(name="Group A")
        second_group = DiagnosisDiseaseGroup.objects.create(name="Group B")
        first = DiagnosisDiseaseSubgroup.objects.create(disease_group=first_group, name="Shared")
        DiagnosisDiseaseSubgroup.objects.create(disease_group=second_group, name="Shared")
        ambiguous = resolve_option("diagnosis-disease-subgroups", "Shared")
        scoped = resolve_option("diagnosis-disease-subgroups", "Shared", filters={"disease_group": first_group})
        self.assertEqual(ambiguous["status"], "ambiguous")
        self.assertEqual((scoped["status"], scoped["option_id"]), ("resolved", first.pk))

    def test_negative_molecular_text_does_not_create_results(self):
        MolecularPathologyGene.objects.create(name="EGFR")
        MolecularPathologyResult.objects.create(code="not_detected", name="Not detected")
        draft = build_intake_draft({
            "molecular_candidates": [{
                "gene": {"value": "EGFR", "source_text": "EGFR not detected", "page": 1, "confidence": 0.95},
                "reported_result": {"value": "Not detected", "source_text": "EGFR not detected", "page": 1, "confidence": 0.95},
            }]
        }, document_id=6)
        molecular = draft["observations"][0]["molecular_tests"][0]
        self.assertEqual(molecular["resolutions"]["reported_result"]["status"], "resolved")
        self.assertEqual(MolecularTest.objects.count(), 0)
        self.assertEqual(MolecularTestResult.objects.count(), 0)


class DraftApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="reviewer", password="password")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.document = PrescriptionDocument.objects.create(
            file="prescriptions/test.pdf",
            original_filename="test.pdf",
            sha256="a" * 64,
            status=PrescriptionDocument.Status.READY_FOR_REVIEW,
            uploaded_by=self.user,
        )
        self.run = ExtractionRun.objects.create(
            document=self.document,
            schema_version="1",
            status=ExtractionRun.Status.COMPLETED,
            structured_data={
                "patient": {},
                "diagnosis_candidates": [{"value": "Explicit diagnosis", "source_text": "Diagnosis: Explicit diagnosis", "page": 1, "confidence": 0.9}],
                "unresolved_items": [],
            },
            raw_response="sensitive duplicate response",
        )

    def test_start_review_creates_only_a_canonical_draft(self):
        response = self.client.post(f"/api/prescriptions/documents/{self.document.pk}/start-review/")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["reviewed_data"]["schema_version"], 1)
        self.assertEqual(response.data["reviewed_data"]["document_id"], self.document.pk)
        self.assertEqual(PrescriptionReview.objects.count(), 1)
        self.assertEqual(ClinicalObservation.objects.count(), 0)
        self.assertEqual(Diagnosis.objects.count(), 0)
        self.assertEqual(MolecularTest.objects.count(), 0)

    def test_entry_draft_action_is_on_document_route(self):
        response = self.client.get(f"/api/prescriptions/documents/{self.document.pk}/entry-draft/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intake_draft"], response.data["reviewed_data"])

    def test_review_patch_rejects_wrong_document(self):
        self.client.post(f"/api/prescriptions/documents/{self.document.pk}/start-review/")
        review = PrescriptionReview.objects.get(document=self.document)
        invalid = deepcopy(review.reviewed_data)
        invalid["document_id"] = self.document.pk + 1
        response = self.client.patch(
            f"/api/prescriptions/documents/{self.document.pk}/review/",
            {"reviewed_data": invalid},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_review_patch_rejects_missing_patient(self):
        self.client.post(f"/api/prescriptions/documents/{self.document.pk}/start-review/")
        review = PrescriptionReview.objects.get(document=self.document)
        invalid = deepcopy(review.reviewed_data)
        invalid["patient"] = {"match_status": "existing", "patient_id": 999999, "values": {}}
        response = self.client.patch(
            f"/api/prescriptions/documents/{self.document.pk}/review/",
            {"reviewed_data": invalid},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_document_api_does_not_expose_raw_provider_response(self):
        response = self.client.get(f"/api/prescriptions/documents/{self.document.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("raw_response", response.data["extraction_runs"][0])

    def test_document_has_no_publication_action(self):
        response = self.client.post(f"/api/prescriptions/documents/{self.document.pk}/publish-review/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(ClinicalObservation.objects.count(), 0)

    def test_selected_patient_is_synchronized_into_draft(self):
        patient = Patient.objects.create(registration_no="REG-P", patient_id="PAT-P", name="Patient")
        self.client.post(f"/api/prescriptions/documents/{self.document.pk}/start-review/")
        response = self.client.patch(
            f"/api/prescriptions/documents/{self.document.pk}/review/",
            {"selected_patient": patient.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["reviewed_data"]["patient"]["match_status"], "existing")
        self.assertEqual(response.data["reviewed_data"]["patient"]["patient_id"], patient.pk)
