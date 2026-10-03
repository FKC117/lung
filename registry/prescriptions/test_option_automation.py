from prescriptions.evaluation.evidence_fixture import evidence_backed_fixture
from django.test import TestCase
from options.models import DiagnosisDiseaseGroup, DiagnosisDiseaseSubgroup, DiagnosisMetastaticSite
from prescriptions.services.option_resolver import resolve_draft_options, validate_selected_resolutions
from prescriptions.services.option_resolver import resolve_option
from prescriptions.services.readiness import mark_ready_records, record_issues


class AutomatedOptionResolutionTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.approver = get_user_model().objects.create_user(username="synthetic-alias-approver")

    def test_readiness_agrees_on_optional_whitespace_and_remaining_resolution(self):
        optional = {"state": "extracted", "values": {"report_summary": "   "}, "resolutions": {}}
        self.assertEqual(record_issues("histopathologies", optional), [])
        blocked = {"state": "extracted", "values": {}, "resolutions": {"histopathology_type": {"status": "unresolved"}}}
        self.assertTrue(record_issues("histopathologies", blocked))
        mark_ready_records({"observations": [{"histopathologies": [blocked]}]})
        self.assertNotEqual(blocked["state"], "validated")

    def test_case_conflicting_aliases_remain_ambiguous(self):
        from options.models import TreatmentDrug
        from prescriptions.models import PrescriptionDrugAlias
        first = TreatmentDrug.objects.create(name="Synthetic first")
        second = TreatmentDrug.objects.create(name="Synthetic second")
        PrescriptionDrugAlias.objects.create(alias="Synthetic BRAND", drug=first, approved_by=self.approver)
        PrescriptionDrugAlias.objects.create(alias="Synthetic brand", drug=second, approved_by=self.approver)
        result = resolve_option("treatment-drugs", "synthetic brand")
        self.assertEqual(result["status"], "ambiguous")
        self.assertIsNone(result["option_id"])

    def test_changed_catalog_requires_reviewer_selection_before_approval(self):
        from django.core.exceptions import ValidationError
        from prescriptions.services.draft_schema import normalize_extraction
        from prescriptions.services.option_resolver import validate_approval_readiness
        option = DiagnosisMetastaticSite.objects.create(name="Synthetic liver")
        draft = normalize_extraction(evidence_backed_fixture({"gemini_extraction": {"observations": [{"diagnoses": [{"metastatic_sites": [option.name]}]}]}}), document_id=1)
        draft["patient"]["match_status"] = "new"
        draft = mark_ready_records(resolve_draft_options(draft))
        validate_approval_readiness(draft)
        option.name = "Synthetic changed meaning"
        option.save()
        with self.assertRaisesMessage(ValidationError, "catalog changed"):
            validate_approval_readiness(draft)
        resolution = draft["observations"][0]["diagnoses"][0]["resolutions"]["metastatic_sites"]
        resolution["match_method"] = "reviewer_selected"
        validate_selected_resolutions(draft)
        validate_approval_readiness(draft)

    def test_alias_conflicting_with_exact_name_requires_selection(self):
        from options.models import TreatmentDrug
        from prescriptions.models import PrescriptionDrugAlias
        named = TreatmentDrug.objects.create(name="Synthetic named drug")
        aliased = TreatmentDrug.objects.create(name="Synthetic other drug")
        PrescriptionDrugAlias.objects.create(alias=named.name, drug=aliased, approved_by=self.approver)
        result = resolve_option("treatment-drugs", named.name)
        self.assertEqual(result["status"], "ambiguous")
        self.assertIsNone(result["option_id"])
        self.assertEqual({item["option_id"] for item in result["candidates"]}, {named.pk, aliased.pk})

    def test_approved_alias_is_scoped_and_fuzzy_is_suggestion_only(self):
        from options.models import TreatmentDrug
        from prescriptions.models import PrescriptionDrugAlias
        drug = TreatmentDrug.objects.create(name="Synthetic medicine")
        PrescriptionDrugAlias.objects.create(alias="Synthetic brand", drug=drug, approved_by=self.approver)
        result = resolve_option("treatment-drugs", "Synthetic brand")
        self.assertEqual((result["option_id"], result["match_method"]), (drug.pk, "approved_alias"))
        self.assertEqual(resolve_option("treatment-drugs", "Synthetic brand", allowed_ids=[])["status"], "unresolved")
        fuzzy = resolve_option("treatment-drugs", "Synthetic medicin")
        self.assertEqual(fuzzy["status"], "ambiguous")
        self.assertIsNone(fuzzy["option_id"])
        self.assertEqual(fuzzy["candidates"][0]["match_method"], "fuzzy")

    def test_deleted_selected_option_is_rejected(self):
        from django.core.exceptions import ValidationError
        option = DiagnosisMetastaticSite.objects.create(name="Synthetic site")
        draft = resolve_draft_options(self.draft({"metastatic_sites": [option.name]}))
        option.delete()
        with self.assertRaises(ValidationError):
            validate_selected_resolutions(draft)

    def test_empty_catalog_preserves_other_fields_and_does_not_create_options(self):
        from options.api_views import OPTION_RESOURCES
        from prescriptions.models import PrescriptionDrugAlias
        from prescriptions.services.intake_draft import build_intake_draft
        model = OPTION_RESOURCES["histopathology-types"]
        before = model.objects.count()
        self.assertEqual(before, 0)
        aliases = PrescriptionDrugAlias.objects.count()
        draft = build_intake_draft(evidence_backed_fixture({"gemini_extraction": {"observations": [{"histopathologies": [{
            "histopathology_type": "Synthetic missing type", "report_summary": "Synthetic summary", "biopsy_date": "2020-01-01"}]}]}}), document_id=1)
        record = draft["observations"][0]["histopathologies"][0]
        self.assertEqual(record["values"]["report_summary"], "Synthetic summary")
        self.assertEqual(record["values"]["biopsy_date"], "2020-01-01")
        self.assertEqual(record["extracted_values"]["histopathology_type"], "Synthetic missing type")
        self.assertEqual(record["resolutions"]["histopathology_type"]["resource"], "histopathology-types")
        self.assertEqual(record["resolutions"]["histopathology_type"]["status"], "unresolved")
        self.assertIsNone(record["resolutions"]["histopathology_type"]["option_id"])
        self.assertEqual(model.objects.count(), before)
        self.assertEqual(PrescriptionDrugAlias.objects.count(), aliases)
    def test_clinical_polarity_is_not_erased_by_normalization(self):
        from options.models import MolecularPathologyResult
        MolecularPathologyResult.objects.create(name="HER2+")
        result = resolve_option("molecular-results", "HER2-")
        self.assertNotEqual(result["status"], "resolved")

    def test_catalog_change_changes_match_fingerprint(self):
        DiagnosisMetastaticSite.objects.create(name="Liver")
        first = resolve_option("diagnosis-metastatic-sites", "Liver")
        DiagnosisMetastaticSite.objects.create(name="Bone")
        second = resolve_option("diagnosis-metastatic-sites", "Liver")
        self.assertNotEqual(first["catalog_fingerprint"], second["catalog_fingerprint"])

    def test_complete_record_is_ready_without_per_record_approval(self):
        record = {"state": "extracted", "values": {"report_summary": "Synthetic report"}, "resolutions": {}}
        draft = {"observations": [{"histopathologies": [record]}]}
        mark_ready_records(draft)
        self.assertEqual(record["state"], "validated")
        self.assertEqual(record_issues("histopathologies", record), [])

    def draft(self, values):
        return {"observations": [{"diagnoses": [{"values": values, "state": "extracted"}]}]}

    def test_child_never_resolves_without_its_parent(self):
        group = DiagnosisDiseaseGroup.objects.create(name="Group")
        DiagnosisDiseaseSubgroup.objects.create(name="Unique subgroup", disease_group=group)
        result = resolve_draft_options(self.draft({"disease_subgroup": "Unique subgroup"}))
        record = result["observations"][0]["diagnoses"][0]
        self.assertEqual(record["resolutions"]["disease_subgroup"]["status"], "unresolved")
        self.assertIn("parent", record["resolutions"]["disease_subgroup"]["reason"])
        self.assertEqual(record["values"]["disease_subgroup"], "Unique subgroup")

    def test_every_multiselect_is_resolved_and_original_text_retained(self):
        liver = DiagnosisMetastaticSite.objects.create(name="Liver")
        bone = DiagnosisMetastaticSite.objects.create(name="Bone")
        result = resolve_draft_options(self.draft({"metastatic_sites": ["Liver", "Bone"]}))
        record = result["observations"][0]["diagnoses"][0]
        self.assertEqual(record["values"]["metastatic_sites"], [liver.pk, bone.pk])
        self.assertEqual(record["resolutions"]["metastatic_sites"]["raw_value"], ["Liver", "Bone"])
        validate_selected_resolutions(result)

    def test_partial_multiselect_does_not_silently_drop_an_unmatched_fact(self):
        DiagnosisMetastaticSite.objects.create(name="Liver")
        result = resolve_draft_options(self.draft({"metastatic_sites": ["Liver", "Unknown synthetic site"]}))
        record = result["observations"][0]["diagnoses"][0]
        self.assertEqual(record["values"]["metastatic_sites"], ["Liver", "Unknown synthetic site"])
        self.assertEqual(record["resolutions"]["metastatic_sites"]["option_ids"], [])
        self.assertEqual(record["state"], "unresolved")

    def test_pending_alias_is_not_an_automatic_rule_until_explicit_approval(self):
        from prescriptions.models import PrescriptionDrugAlias
        from options.models import TreatmentDrug
        from prescriptions.services.option_resolver import catalog_fingerprint
        drug = TreatmentDrug.objects.create(name="Synthetic canonical medicine")
        before = catalog_fingerprint("treatment-drugs")
        alias = PrescriptionDrugAlias.objects.create(alias="Pending synthetic brand",drug=drug)
        self.assertNotEqual(resolve_option("treatment-drugs",alias.alias)["status"],"resolved")
        self.assertEqual(catalog_fingerprint("treatment-drugs"),before)
        alias.approved_by = self.approver
        alias.save()
        self.assertEqual(resolve_option("treatment-drugs",alias.alias)["match_method"],"approved_alias")
        self.assertNotEqual(catalog_fingerprint("treatment-drugs"),before)
