"""Atomic persistence for validated longitudinal prescription drafts.

Extraction never calls this module.  It is the server-side persistence boundary
for a human-approved canonical draft, and intentionally uses selected option
IDs rather than extracted option names.
"""
from datetime import date, datetime
from uuid import uuid4
from decimal import Decimal, InvalidOperation

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from options.api_views import OPTION_RESOURCES
from records.models import (
    CancerMarkerResult, ClinicalObservation, ClinicalTNMStaging, Diagnosis,
    DiseaseProgressionRecord, Histopathology, IHCResult, IRECISTAssessment,
    MetastaticSiteRecord, MolecularTest, MolecularTestResult,
    PathologicalResponseAssessment, PathologicalStagingResult,
    PathologicalTNMStaging, Patient, PatientAnthropometry, PatientComorbidity,
    RadiotherapyCourse, RECIST11Assessment, SurgeryRecord, SurvivalFollowUp,
    TreatmentAdministration, TreatmentCourse,
)
from records.services.molecular import finalize_molecular_test
from prescriptions.models import PrescriptionPublicationObservation, PrescriptionReview, RecordProvenance
from .draft_schema import COLLECTIONS, validate_draft
from .option_resolver import OPTION_FIELDS, validate_approval_readiness, validate_selected_resolutions


def _date(value):
    if value in (None, ""):
        return None
    try:
        return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])
    except ValueError as exc:
        raise ValidationError({"date": f"Invalid ISO date: {value!r}."}) from exc


def _datetime(value):
    if value in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError({"observed_at": f"Invalid ISO datetime: {value!r}."}) from exc


def _decimal(value, field):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValidationError({field: "Must be a valid number."}) from exc


def _plain(values, fields):
    return {key: values[key] for key in fields if values.get(key) not in (None, "")}


def _option(record, field, collection):
    option_id = record.get("resolutions", {}).get(field, {}).get("option_id")
    if option_id is None:
        return None
    return OPTION_RESOURCES[OPTION_FIELDS[collection][field]].objects.get(pk=option_id)


def _options(record, field, collection):
    ids = record.get("resolutions", {}).get(field, {}).get("option_ids", [])
    model = OPTION_RESOURCES[OPTION_FIELDS[collection][field]]
    found = {item.pk: item for item in model.objects.filter(pk__in=ids)}
    return [found[item_id] for item_id in ids]


def _save(instance, path, context):
    try:
        instance.full_clean()
        instance.save()
    except DjangoValidationError as exc:
        raise ValidationError({path: getattr(exc, "message_dict", exc.messages)}) from exc
    context["counts"][instance._meta.model_name] = context["counts"].get(instance._meta.model_name, 0) + 1
    return instance


def _provenance(instance, review, run, path, evidence_ids, evidence_by_id, user):
    if review is None:
        return
    # Older normalized drafts may retain inline observation evidence while new
    # drafts use evidence IDs.  Preserve either representation without letting
    # audit metadata affect validated clinical values.
    evidence = [
        item if isinstance(item, dict) else evidence_by_id[item]
        for item in evidence_ids
        if isinstance(item, dict) or item in evidence_by_id
    ] or [{}]
    content_type = ContentType.objects.get_for_model(instance, for_concrete_model=False)
    RecordProvenance.objects.bulk_create([
        RecordProvenance(
            content_type=content_type, object_id=instance.pk, document=review.document,
            extraction_run=run, source_text=str(item.get("source_text") or ""),
            source_page=item.get("page"), field_path=item.get("field_path") or path,
            reviewer=user,
        ) for item in evidence
    ])


def _record_provenance(instance, review, run, path, record, evidence_by_id, user):
    _provenance(instance, review, run, path, record.get("evidence_refs", []), evidence_by_id, user)


PATIENT_FIELDS = {"registration_no", "patient_id", "name", "phone", "email", "nid", "passport", "photo", "date_of_birth", "age", "area", "first_diagnosis_date", "dietary_habits", "personal_history_of_cancer", "family_history_of_cancer", "any_known_mutation", "cigarettes_per_day", "smoking_duration_in_years", "quit_smoking_for_in_years", "covid_infection_date", "is_draft"}
PATIENT_OPTIONS = {"sex": "sexes", "district": "districts", "thana": "thanas", "marital_status": "marital-statuses", "alcohol_history": "alcohol-histories", "economic_status": "economic-statuses", "blood_group": "blood-groups", "type_of_patient": "patient-types", "smoking_history": "smoking-histories", "tb_history": "tb-histories", "covid_history": "covid-histories", "vaccine": "vaccines", "vaccination_dose": "vaccination-doses"}


def _patient(draft, review, context):
    data = draft["patient"]
    if data["match_status"] == "existing":
        patient = (review.selected_patient if review else None) or Patient.objects.get(pk=data["patient_id"])
        values = data.get("values", {})
        # A reviewer-approved correction is part of publication, not silently
        # discarded.  Identity keys are deliberately immutable for a match.
        conflicting = {key for key in ("registration_no", "patient_id") if values.get(key) and values[key] != getattr(patient, key)}
        if conflicting:
            raise ValidationError({"patient": f"Matched patient identity conflicts: {', '.join(sorted(conflicting))}. Select another patient or resolve the draft."})
        attrs = _plain(values, PATIENT_FIELDS - {"registration_no", "patient_id"})
        for field, resource in PATIENT_OPTIONS.items():
            if values.get(field) not in (None, ""):
                attrs[field] = OPTION_RESOURCES[resource].objects.get(pk=values[field])
        if attrs:
            for field, value in attrs.items():
                setattr(patient, field, value)
            _save(patient, "patient", context)
            _provenance(patient, review, context["run"], "patient.correction", [], {}, context["user"])
        return patient
    if data["match_status"] != "new":
        raise ValidationError({"patient": "Patient matching must be resolved before publication."})
    values = data["values"]
    missing = [key for key in ("registration_no", "patient_id", "name") if not values.get(key)]
    if missing:
        raise ValidationError({"patient": f"New patient requires reviewer-entered {', '.join(missing)}; extracted identifiers are never invented."})
    attrs = _plain(values, PATIENT_FIELDS)
    for field, resource in PATIENT_OPTIONS.items():
        if values.get(field) not in (None, ""):
            attrs[field] = OPTION_RESOURCES[resource].objects.get(pk=values[field])
    patient = _save(Patient(**attrs), "patient", context)
    _provenance(patient, review, context["run"], "patient", [], {}, context["user"])
    if review:
        review.selected_patient = patient
        review.save(update_fields=["selected_patient", "updated_at"])
    return patient


def _attrs(values, record, collection, plain, option_fields):
    result = _plain(values, plain)
    for key in list(result):
        if key.endswith(("_on", "_date", "_at")):
            result[key] = _date(result[key])
        elif key in {"height_cm", "weight_kg", "percentage", "value", "variant_allele_frequency", "copy_number", "dose", "dose_per_fraction_cgy", "residual_viable_tumor_percentage"}:
            result[key] = _decimal(result[key], key)
        elif key in {"age", "cigarettes_per_day", "cycle_number", "day_number", "planned_fractions", "completed_fractions"}:
            try:
                result[key] = int(result[key])
            except (TypeError, ValueError) as exc:
                raise ValidationError({key: "Must be a whole number."}) from exc
    for field in option_fields:
        if field in values:
            result[field] = _option(record, field, collection)
    return result


def _persist_record(collection, values, record, observation, courses, delayed, path, context):
    def child(instance, child_path):
        item = _save(instance, child_path, context)
        _provenance(item, context["review"], context["run"], child_path, record.get("evidence_refs", []), {}, context["user"])
        return item
    if collection == "comorbidities": return _save(PatientComorbidity(observation=observation, **_attrs(values, record, collection, {"diagnosed_on", "is_active", "notes"}, {"comorbidity"})), path, context)
    if collection == "diagnoses":
        item = _save(Diagnosis(observation=observation, **_attrs(values, record, collection, {"diagnosed_on", "diagnosis_in_details"}, {"disease_group", "disease_subgroup", "primary_site", "laterality"})), path, context)
        for site in _options(record, "metastatic_sites", collection): child(MetastaticSiteRecord(diagnosis=item, site=site), f"{path}.metastatic_sites")
        return item
    if collection == "histopathologies": return _save(Histopathology(observation=observation, **_attrs(values, record, collection, {"biopsy_date", "report_date", "report_summary"}, {"histopathology_details", "histopathology_type", "histopathology_site", "histopathology_grade"})), path, context)
    if collection == "ihc_results": return _save(IHCResult(observation=observation, **_attrs(values, record, collection, {"tested_at", "percentage", "notes"}, {"marker", "result"})), path, context)
    if collection == "pathological_staging_results": return _save(PathologicalStagingResult(observation=observation, **_attrs(values, record, collection, {"assessed_at", "percentage", "notes"}, {"feature", "result"})), path, context)
    if collection in {"clinical_tnm_stagings", "pathological_tnm_stagings"}:
        model = ClinicalTNMStaging if collection == "clinical_tnm_stagings" else PathologicalTNMStaging
        return _save(model(observation=observation, **_attrs(values, record, collection, {"staged_on", "notes"}, {"t", "n", "m", "stage"})), path, context)
    if collection == "cancer_markers": return _save(CancerMarkerResult(observation=observation, **_attrs(values, record, collection, {"tested_on", "value", "notes"}, {"marker"})), path, context)
    if collection == "treatments":
        item = _save(TreatmentCourse(observation=observation, **_attrs(values, record, collection, {"started_on", "ended_on", "status", "reason_for_stopping", "notes"}, {"modality", "line_of_treatment", "protocol"})), path, context)
        courses[record["temp_id"]] = item
        for admin in values.get("administrations", []):
            if admin.get("drug"):
                admin_attrs = _plain(admin, {"administered_on", "cycle_number", "day_number", "dose", "dose_unit", "status", "notes"})
                if "administered_on" in admin_attrs: admin_attrs["administered_on"] = _date(admin_attrs["administered_on"])
                child(TreatmentAdministration(treatment_course=item, observation=observation, drug=OPTION_RESOURCES["treatment-drugs"].objects.get(pk=admin["drug"]), **admin_attrs), f"{path}.administrations")
        return item
    if collection == "surgeries": return _save(SurgeryRecord(observation=observation, **_attrs(values, record, collection, {"surgery_date", "status", "procedure_details", "operative_findings", "complications", "notes"}, {"modality", "laterality"})), path, context)
    if collection == "radiotherapies": return _save(RadiotherapyCourse(observation=observation, **_attrs(values, record, collection, {"started_on", "ended_on", "dose_per_fraction_cgy", "planned_fractions", "completed_fractions", "status", "reason_for_stopping", "notes"}, {"site", "intent", "modality"})), path, context)
    if collection in {"recist_assessments", "irecist_assessments", "pathological_responses"}: delayed.append((collection, values, record, path)); return None
    if collection == "progression_records":
        item = _save(DiseaseProgressionRecord(observation=observation, **_attrs(values, record, collection, {"assessed_on", "progression_date", "notes"}, {"status", "estimation_method"})), path, context); item.progression_sites.set(_options(record, "progression_sites", collection)); return item
    if collection == "survival_records": return _save(SurvivalFollowUp(observation=observation, **_attrs(values, record, collection, {"followed_up_on", "death_date", "cause_of_death", "notes"}, {"status"})), path, context)
    if collection == "molecular_tests":
        test = _save(MolecularTest(observation=observation, **_attrs(values, record, collection, {"specimen_collected_on", "tested_on", "reported_on", "qc_status", "laboratory", "accession_number", "notes"}, {"panel_version", "method", "specimen"})), path, context)
        for result in values.get("results", [values]):
            result_record = record if result is values else {**record, "values": result}
            result_attrs = _attrs(result, result_record, collection, {"dna_change", "protein_change", "common_name", "variant_allele_frequency", "copy_number", "origin", "notes"}, {"panel_target", "gene", "exon", "alteration_type", "result", "partner_gene", "clinical_significance"})
            child(MolecularTestResult(molecular_test=test, **result_attrs), f"{path}.results")
        if values.get("status") == MolecularTest.Status.COMPLETED:
            existing = set(test.results.values_list("pk", flat=True)); finalize_molecular_test(test.pk)
            for result in test.results.exclude(pk__in=existing): _provenance(result, context["review"], context["run"], f"{path}.derived", record.get("evidence_refs", []), {}, context["user"])
        return test
    raise ValidationError({path: f"Unsupported collection {collection}."})


def _persist_observation(data, index, patient, review, context):
    if review:
        existing = PrescriptionPublicationObservation.objects.filter(review=review, draft_observation_temp_id=data["temp_id"]).select_related("observation").first()
        if existing:
            return existing.observation
    evidence = {item["evidence_id"]: item for item in data.get("evidence_refs", [])}
    source_note = f"Published from prescription review {review.pk}" if review else "Published from manual New Entry"
    observation = _save(ClinicalObservation(patient=patient, observed_at=_datetime(data.get("observed_at")), prescription_date=_date(data.get("prescription_date")), status=ClinicalObservation.Status.PUBLISHED, published_at=timezone.now(), published_by=context["user"], clinical_notes=f"{source_note} ({data.get('temporal_context', 'unknown')})."), f"observations.{index}", context)
    _provenance(observation, review, context["run"], f"observations.{index}", data.get("evidence_refs", []), evidence, context["user"])
    if review:
        PrescriptionPublicationObservation.objects.create(review=review, draft_observation_temp_id=data["temp_id"], observation=observation)
    if data.get("anthropometry"):
        anthropometry = data["anthropometry"]
        item = _save(PatientAnthropometry(
            observation=observation,
            height_cm=_decimal(anthropometry.get("height_cm"), "height_cm"),
            weight_kg=_decimal(anthropometry.get("weight_kg"), "weight_kg"),
        ), f"observations.{index}.anthropometry", context)
        _provenance(item, review, context["run"], f"observations.{index}.anthropometry", [], evidence, context["user"])
    courses, delayed = {}, []
    for collection in COLLECTIONS:
        for record_index, record in enumerate(data.get(collection, [])):
            path = f"observations.{index}.{collection}.{record_index}"
            item = _persist_record(collection, record.get("values", {}), record, observation, courses, delayed, path, context)
            if item is not None: _record_provenance(item, review, context["run"], path, record, evidence, context["user"])
    for collection, values, record, path in delayed:
        course = courses.get(values.get("treatment_temp_id")) if values.get("treatment_temp_id") else next(iter(courses.values()), None)
        if course is None: raise ValidationError({path: "This assessment requires a treatment course in the same observation."})
        model = {"recist_assessments": RECIST11Assessment, "irecist_assessments": IRECISTAssessment, "pathological_responses": PathologicalResponseAssessment}[collection]
        fields = set(values) - {"treatment_temp_id"}
        item = _save(model(observation=observation, treatment_course=course, **_attrs(values, record, collection, fields, set(OPTION_FIELDS[collection]))), path, context)
        _record_provenance(item, review, context["run"], path, record, evidence, context["user"])
    return observation


@transaction.atomic
def persist_canonical_draft(draft, *, review=None, user):
    """Shared validated persistence service. Any child failure rolls back all."""
    validate_draft(draft, document_id=review.document_id if review else None, check_database=True)
    validate_selected_resolutions(draft); validate_approval_readiness(draft)
    context = {"review": review, "user": user, "run": review.document.extraction_runs.filter(status="completed").first() if review else None, "counts": {}}
    patient = _patient(draft, review, context)
    observations = [_persist_observation(item, i, patient, review, context) for i, item in enumerate(draft["observations"])]
    return patient, observations, context["counts"]


@transaction.atomic
def publish_review(review, user):
    # Lock the review row only; ``selected_patient`` is nullable and PostgreSQL
    # cannot lock the nullable side of that outer join.
    review = PrescriptionReview.objects.select_for_update(of=("self",)).select_related("document", "selected_patient").get(pk=review.pk)
    if review.published_at:
        return list(ClinicalObservation.objects.filter(prescription_publication_mapping__review=review)), {"already_published": True}
    if review.status != PrescriptionReview.Status.APPROVED: raise ValidationError("Only approved reviews can be published.")
    patient, observations, counts = persist_canonical_draft(review.reviewed_data, review=review, user=user)
    review.published_at = timezone.now(); review.published_by = user; review.selected_patient = patient
    review.save(update_fields=["published_at", "published_by", "selected_patient", "updated_at"])
    return observations, counts
