from copy import deepcopy

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from options.models import (
    DiagnosisDiseaseGroup,
    DiagnosisDiseaseSubgroup,
    DiagnosisMetastaticSite,
    District,
    Doctor,
    MolecularAlterationType,
    MolecularPanel,
    MolecularPanelTarget,
    MolecularPanelVersion,
    MolecularPathologyExon,
    MolecularPathologyGene,
    MolecularPathologyMethod,
    MolecularPathologyResult,
    ProgressionSite,
    Thana,
    TreatmentDrug,
    TreatmentProtocol,
    TreatmentProtocolDrug,
)
from records.models import ClinicalObservation, Diagnosis, MolecularTest, MolecularTestResult, Patient, PatientAnthropometry

from .models import ExtractionRun, PrescriptionBatchJob, PrescriptionDocument, PrescriptionPage, PrescriptionReview, RecordProvenance
from .services.publish import publish_review
from .services.draft_schema import COLLECTIONS, empty_draft, empty_observation, normalize_extraction, validate_draft
from .services.extraction import validate_extraction
from .services.intake_draft import build_intake_draft
from .services.option_resolver import resolve_option, validate_approval_readiness, validate_selected_resolutions


def record(temp_id="record-1", *, state="edited", values=None, evidence_refs=None):
    return {
        "temp_id": temp_id,
        "state": state,
        "values": values or {},
        "resolutions": {},
        "evidence_refs": evidence_refs or [],
    }


def resolution(resource, option, *, raw_value="selected", status="resolved"):
    return {
        "status": status,
        "resource": resource,
        "raw_value": raw_value,
        "option_id": option.pk if option is not None and status == "resolved" else None,
        "match_method": "reviewer_selected" if status == "resolved" else None,
        "candidates": [],
        "reason": "",
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
        with self.assertRaises(Exception):
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

    def test_disease_subgroup_must_belong_to_selected_group(self):
        selected_group = DiagnosisDiseaseGroup.objects.create(name="Selected group")
        other_group = DiagnosisDiseaseGroup.objects.create(name="Other group")
        subgroup = DiagnosisDiseaseSubgroup.objects.create(disease_group=other_group, name="Subgroup")
        draft = empty_draft(20)
        observation = empty_observation()
        item = record(values={"disease_group": selected_group.name, "disease_subgroup": subgroup.name})
        item["resolutions"] = {
            "disease_group": resolution("diagnosis-disease-groups", selected_group),
            "disease_subgroup": resolution("diagnosis-disease-subgroups", subgroup),
        }
        observation["diagnoses"].append(item)
        draft["observations"].append(observation)
        with self.assertRaisesMessage(ValidationError, "does not belong"):
            validate_selected_resolutions(draft)

    def test_exon_must_belong_to_selected_gene(self):
        selected_gene = MolecularPathologyGene.objects.create(name="EGFR")
        other_gene = MolecularPathologyGene.objects.create(name="ALK")
        exon = MolecularPathologyExon.objects.create(gene=other_gene, name="Exon 20")
        draft = empty_draft(21)
        observation = empty_observation()
        item = record(values={"gene": selected_gene.name, "exon": exon.name})
        item["resolutions"] = {
            "gene": resolution("molecular-genes", selected_gene),
            "exon": resolution("molecular-exons", exon),
        }
        observation["molecular_tests"].append(item)
        draft["observations"].append(observation)
        with self.assertRaisesMessage(ValidationError, "does not belong"):
            validate_selected_resolutions(draft)

    def test_drug_must_belong_to_selected_protocol(self):
        protocol = TreatmentProtocol.objects.create(name="Protocol A")
        other_protocol = TreatmentProtocol.objects.create(name="Protocol B")
        drug = TreatmentDrug.objects.create(name="Drug A")
        TreatmentProtocolDrug.objects.create(protocol=other_protocol, drug=drug)
        draft = empty_draft(22)
        observation = empty_observation()
        item = record(values={"protocol": protocol.name, "drug": drug.name})
        item["resolutions"] = {
            "protocol": resolution("treatment-protocols", protocol),
            "drug": resolution("treatment-drugs", drug),
        }
        observation["treatments"].append(item)
        draft["observations"].append(observation)
        with self.assertRaisesMessage(ValidationError, "does not belong"):
            validate_selected_resolutions(draft)

    def test_panel_version_and_target_parent_scopes_are_validated(self):
        method = MolecularPathologyMethod.objects.create(name="NGS")
        selected_panel = MolecularPanel.objects.create(name="Panel A")
        other_panel = MolecularPanel.objects.create(name="Panel B")
        version = MolecularPanelVersion.objects.create(panel=other_panel, version="1", method=method)
        gene = MolecularPathologyGene.objects.create(name="KRAS")
        alteration = MolecularAlterationType.objects.create(name="SNV")
        target = MolecularPanelTarget.objects.create(panel_version=version, gene=gene, alteration_type=alteration)
        draft = empty_draft(23)
        observation = empty_observation()
        item = record(values={"panel": selected_panel.name, "panel_version": "1", "panel_target": str(target), "gene": gene.name, "alteration_type": alteration.name})
        item["resolutions"] = {
            "panel": resolution("molecular-panels", selected_panel),
            "panel_version": resolution("molecular-panel-versions", version),
            "panel_target": resolution("molecular-panel-targets", target),
            "gene": resolution("molecular-genes", gene),
            "alteration_type": resolution("molecular-alteration-types", alteration),
        }
        observation["molecular_tests"].append(item)
        draft["observations"].append(observation)
        with self.assertRaisesMessage(ValidationError, "does not belong"):
            validate_selected_resolutions(draft)

    def test_thana_must_belong_to_selected_district(self):
        selected = District.objects.create(name="Selected district")
        other = District.objects.create(name="Other district")
        thana = Thana.objects.create(district=other, name="Thana")
        draft = empty_draft(24)
        draft["patient"]["values"] = {"district": selected.pk, "thana": thana.pk}
        draft["observations"].append(empty_observation())
        with self.assertRaisesMessage(ValidationError, "does not belong"):
            validate_selected_resolutions(draft)

    def test_retired_mutation_and_protocol_cycle_options_block_approval(self):
        draft = empty_draft(25)
        draft["patient"]["match_status"] = "new"
        observation = empty_observation()
        observation["molecular_tests"].append(record("mutation", values={"mutation": "L858R"}))
        observation["treatments"].append(record("cycle", values={"protocol_cycle": "Cycle 2"}))
        draft["observations"].append(observation)
        with self.assertRaisesMessage(ValidationError, "no active controlled option"):
            validate_approval_readiness(draft)

    def test_multi_option_resolutions_validate_real_option_ids(self):
        metastatic_site = DiagnosisMetastaticSite.objects.create(name="Liver")
        progression_site = ProgressionSite.objects.create(name="Bone")
        draft = empty_draft(26)
        draft["patient"]["match_status"] = "new"
        observation = empty_observation()
        diagnosis = record(values={"metastatic_sites": [metastatic_site.pk]})
        diagnosis["resolutions"] = {"metastatic_sites": {**resolution("diagnosis-metastatic-sites", None), "status": "resolved", "option_ids": [metastatic_site.pk]}}
        progression = record(values={"progression_sites": [progression_site.pk]})
        progression["resolutions"] = {"progression_sites": {**resolution("progression-sites", None), "status": "resolved", "option_ids": [progression_site.pk]}}
        observation["diagnoses"].append(diagnosis)
        observation["progression_records"].append(progression)
        draft["observations"].append(observation)
        validate_selected_resolutions(draft)
        validate_approval_readiness(draft)

        diagnosis["values"]["metastatic_sites"] = []
        with self.assertRaisesMessage(ValidationError, "must match"):
            validate_selected_resolutions(draft)
        diagnosis["values"]["metastatic_sites"] = [metastatic_site.pk]
        diagnosis["resolutions"]["metastatic_sites"]["option_ids"] = [999999]
        with self.assertRaisesMessage(ValidationError, "does not exist"):
            validate_selected_resolutions(draft)


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

    def test_approved_canonical_draft_publishes_once_with_provenance(self):
        self.client.post(f"/api/prescriptions/documents/{self.document.pk}/start-review/")
        patient = Patient.objects.create(registration_no="REG-PUBLISH", patient_id="PAT-PUBLISH", name="Patient")
        review = PrescriptionReview.objects.get(document=self.document)
        draft = deepcopy(review.reviewed_data)
        draft["patient"] = {"match_status": "existing", "patient_id": patient.pk, "values": {}}
        draft["observations"][0]["anthropometry"] = {"height_cm": "170", "weight_kg": "70"}
        review.reviewed_data = draft
        review.selected_patient = patient
        review.save(update_fields=["reviewed_data", "selected_patient", "updated_at"])
        self.assertEqual(self.client.post(f"/api/prescriptions/documents/{self.document.pk}/approve-review/").status_code, 200)

        response = self.client.post(f"/api/prescriptions/documents/{self.document.pk}/publish/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["observation_ids"]), 1)
        self.assertEqual(ClinicalObservation.objects.count(), 1)
        self.assertEqual(PatientAnthropometry.objects.count(), 1)
        self.assertTrue(RecordProvenance.objects.filter(document=self.document).exists())
        repeated = self.client.post(f"/api/prescriptions/documents/{self.document.pk}/publish/")
        self.assertEqual(repeated.status_code, 200)
        self.assertTrue(repeated.data["counts"]["already_published"])
        self.assertEqual(ClinicalObservation.objects.count(), 1)

    def test_failed_child_rolls_back_complete_publication(self):
        self.client.post(f"/api/prescriptions/documents/{self.document.pk}/start-review/")
        patient = Patient.objects.create(registration_no="REG-ROLLBACK", patient_id="PAT-ROLLBACK", name="Patient")
        review = PrescriptionReview.objects.get(document=self.document)
        draft = deepcopy(review.reviewed_data)
        draft["patient"] = {"match_status": "existing", "patient_id": patient.pk, "values": {}}
        draft["observations"][0]["anthropometry"] = {"height_cm": "bad", "weight_kg": "70"}
        review.reviewed_data = draft; review.selected_patient = patient; review.status = PrescriptionReview.Status.APPROVED
        review.save(update_fields=["reviewed_data", "selected_patient", "status", "updated_at"])
        with self.assertRaises(Exception):
            publish_review(review, self.user)
        self.assertEqual(ClinicalObservation.objects.count(), 0)
        self.assertEqual(PatientAnthropometry.objects.count(), 0)
        review.refresh_from_db()
        self.assertIsNone(review.published_at)

    def test_manual_entry_uses_the_canonical_publication_service(self):
        patient = Patient.objects.create(registration_no="REG-MANUAL", patient_id="PAT-MANUAL", name="Before")
        response = self.client.post("/api/records/intake/", {
            "payload": {
                "existing_patient_id": patient.pk,
                "patient": {"name": "After"},
                "observation": {"prescription_date": "2026-01-01"},
                "history": {"height_cm": "170", "weight_kg": "70"},
            },
            "draft": False,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        patient.refresh_from_db()
        self.assertEqual(patient.name, "After")
        self.assertEqual(ClinicalObservation.objects.count(), 1)
        self.assertEqual(PatientAnthropometry.objects.count(), 1)

    def test_existing_patient_correction_is_applied_and_observation_mapping_is_durable(self):
        self.client.post(f"/api/prescriptions/documents/{self.document.pk}/start-review/")
        patient = Patient.objects.create(registration_no="REG-CORRECT", patient_id="PAT-CORRECT", name="Before")
        review = PrescriptionReview.objects.get(document=self.document)
        draft = deepcopy(review.reviewed_data)
        draft["patient"] = {"match_status": "existing", "patient_id": patient.pk, "values": {"name": "After"}}
        review.reviewed_data = draft; review.selected_patient = patient; review.status = PrescriptionReview.Status.APPROVED
        review.save(update_fields=["reviewed_data", "selected_patient", "status", "updated_at"])
        observations, _ = publish_review(review, self.user)
        patient.refresh_from_db()
        self.assertEqual(patient.name, "After")
        self.assertEqual(review.publication_observations.count(), 1)
        self.assertEqual(review.publication_observations.first().observation_id, observations[0].pk)

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

    def _save_review_draft(self, draft):
        review = PrescriptionReview.objects.get(document=self.document)
        review.reviewed_data = draft
        review.save(update_fields=["reviewed_data", "updated_at"])
        return review

    def test_approval_rejects_unresolved_items_records_and_resolutions(self):
        self.client.post(f"/api/prescriptions/documents/{self.document.pk}/start-review/")
        review = PrescriptionReview.objects.get(document=self.document)
        baseline = deepcopy(review.reviewed_data)
        baseline["patient"] = {"match_status": "new", "patient_id": None, "values": {}}

        unresolved_items = deepcopy(baseline)
        unresolved_items["unresolved_items"] = [{"type": "test", "reason": "Needs review"}]
        self._save_review_draft(unresolved_items)
        response = self.client.post(f"/api/prescriptions/documents/{self.document.pk}/approve-review/")
        self.assertEqual(response.status_code, 400)

        unresolved_record = deepcopy(baseline)
        unresolved_record["observations"][0]["diagnoses"].append(record("unresolved-record", state="unresolved"))
        self._save_review_draft(unresolved_record)
        response = self.client.post(f"/api/prescriptions/documents/{self.document.pk}/approve-review/")
        self.assertEqual(response.status_code, 400)

        ambiguous_resolution = deepcopy(baseline)
        item = record("ambiguous-record", values={"drug": "Unknown brand"})
        item["resolutions"]["drug"] = resolution(
            "treatment-drugs", None, raw_value="Unknown brand", status="ambiguous"
        )
        ambiguous_resolution["observations"][0]["treatments"].append(item)
        self._save_review_draft(ambiguous_resolution)
        response = self.client.post(f"/api/prescriptions/documents/{self.document.pk}/approve-review/")
        self.assertEqual(response.status_code, 400)

        review.refresh_from_db()
        self.assertNotEqual(review.status, PrescriptionReview.Status.APPROVED)

    def test_authorization_scopes_documents_nested_data_reviews_and_files(self):
        self.client.post(f"/api/prescriptions/documents/{self.document.pk}/start-review/")
        page = PrescriptionPage.objects.create(
            document=self.document,
            page_number=1,
            raw_text="sensitive page text",
            image="prescription_pages/test.png",
        )
        outsider = get_user_model().objects.create_user(username="outsider", password="password")
        outsider_client = APIClient()
        outsider_client.force_authenticate(outsider)

        detail_url = f"/api/prescriptions/documents/{self.document.pk}/"
        self.assertEqual(outsider_client.get(detail_url).status_code, 404)
        self.assertEqual(outsider_client.get(f"{detail_url}review/").status_code, 404)
        self.assertEqual(outsider_client.get(f"{detail_url}entry-draft/").status_code, 404)
        self.assertEqual(outsider_client.get(f"{detail_url}source-file/").status_code, 404)
        self.assertEqual(outsider_client.get(f"{detail_url}pages/{page.pk}/image/").status_code, 404)
        self.assertEqual(outsider_client.get("/media/prescriptions/test.pdf").status_code, 404)
        self.assertEqual(self.client.get("/media/prescriptions/test.pdf").status_code, 404)
        list_response = outsider_client.get("/api/prescriptions/documents/")
        self.assertEqual(list_response.status_code, 200)
        self.assertNotContains(list_response, "sensitive duplicate response")
        self.assertNotContains(list_response, self.document.original_filename)

        staff = get_user_model().objects.create_user(username="staff", password="password", is_staff=True)
        staff_client = APIClient()
        staff_client.force_authenticate(staff)
        staff_response = staff_client.get(detail_url)
        self.assertEqual(staff_response.status_code, 200)
        self.assertIn("pages", staff_response.data)
        self.assertIn("extraction_runs", staff_response.data)
        self.assertIn("review", staff_response.data)
        self.assertIn("source-file", staff_response.data["file"])

    def test_assigned_reviewer_can_access_document(self):
        self.client.post(f"/api/prescriptions/documents/{self.document.pk}/start-review/")
        assignee = get_user_model().objects.create_user(username="assignee", password="password")
        review = PrescriptionReview.objects.get(document=self.document)
        review.assigned_to = assignee
        review.save(update_fields=["assigned_to", "updated_at"])
        assigned_client = APIClient()
        assigned_client.force_authenticate(assignee)
        self.assertEqual(
            assigned_client.get(f"/api/prescriptions/documents/{self.document.pk}/").status_code,
            200,
        )

    def test_authorized_api_endpoints_stream_private_prescription_media(self):
        storages = {
            "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        }
        with self.settings(STORAGES=storages):
            self.document.file.save("authorized.pdf", ContentFile(b"private prescription"))
            page = PrescriptionPage.objects.create(document=self.document, page_number=1)
            page.image.save("authorized.png", ContentFile(b"private page"))

            document_response = self.client.get(
                f"/api/prescriptions/documents/{self.document.pk}/source-file/"
            )
            page_response = self.client.get(
                f"/api/prescriptions/documents/{self.document.pk}/pages/{page.pk}/image/"
            )

            self.assertEqual(document_response.status_code, 200)
            self.assertEqual(b"".join(document_response.streaming_content), b"private prescription")
            self.assertEqual(page_response.status_code, 200)
            self.assertEqual(b"".join(page_response.streaming_content), b"private page")

    def test_batch_jobs_are_visible_only_to_submitter_or_staff(self):
        job = PrescriptionBatchJob.objects.create(
            display_name="Private batch",
            model_name="test-model",
            prompt_version="test-prompt",
            submitted_by=self.user,
        )
        outsider = get_user_model().objects.create_user(username="batch-outsider", password="password")
        outsider_client = APIClient()
        outsider_client.force_authenticate(outsider)
        self.assertEqual(
            outsider_client.get(f"/api/prescriptions/batch-jobs/{job.pk}/").status_code,
            404,
        )
        self.assertEqual(
            self.client.get(f"/api/prescriptions/batch-jobs/{job.pk}/").status_code,
            200,
        )
