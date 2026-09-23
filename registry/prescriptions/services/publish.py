from datetime import date

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from options.models import (
    MolecularAlterationType,
    MolecularPathologyExon,
    MolecularPathologyGene,
    MolecularPathologyResult,
    TNMM,
    TNMN,
    TNMStage,
    TNMT,
)
from records.models import (
    ClinicalObservation,
    ClinicalTNMStaging,
    Diagnosis,
    Histopathology,
    MolecularTest,
    MolecularTestResult,
    PathologicalTNMStaging,
)
from prescriptions.models import PrescriptionReview, RecordProvenance


def value_of(item):
    return item.get("value") if isinstance(item, dict) else item


def date_of(item):
    value = value_of(item)
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def option_by_name(model, value):
    value = value_of(value)
    if not value:
        return None
    return model.objects.filter(name__iexact=str(value).strip()).first()


def provenance(record, review, run, field_path, evidence, user):
    RecordProvenance.objects.create(
        content_type=ContentType.objects.get_for_model(record),
        object_id=record.pk,
        document=review.document,
        extraction_run=run,
        source_text=(evidence or {}).get("source_text", "") if isinstance(evidence, dict) else "",
        source_page=(evidence or {}).get("page") if isinstance(evidence, dict) else None,
        field_path=field_path,
        reviewer=user,
    )


def publish_reviewed_candidates(observation, review, run, user):
    """Publish only explicit, reviewed values that map safely to current models."""
    data = review.reviewed_data or {}
    counts = {"diagnoses": 0, "histopathologies": 0, "tnm_stagings": 0, "molecular_results": 0}

    for candidate in data.get("diagnosis_candidates", []):
        evidence = candidate if isinstance(candidate, dict) else {}
        detail = value_of(evidence)
        if not detail:
            continue
        record = Diagnosis.objects.create(observation=observation, diagnosis_in_details=str(detail))
        provenance(record, review, run, "diagnosis_candidates", evidence, user)
        counts["diagnoses"] += 1

    for candidate in data.get("histopathology_candidates", []):
        evidence = candidate.get("finding") if isinstance(candidate, dict) else candidate
        detail = value_of(evidence)
        if not detail:
            continue
        record = Histopathology.objects.create(observation=observation, report_summary=str(detail))
        provenance(record, review, run, "histopathology_candidates", evidence, user)
        counts["histopathologies"] += 1

    for candidate in data.get("staging_candidates", []):
        if not isinstance(candidate, dict):
            continue
        fields = {
            "t": option_by_name(TNMT, candidate.get("t")),
            "n": option_by_name(TNMN, candidate.get("n")),
            "m": option_by_name(TNMM, candidate.get("m")),
            "stage": option_by_name(TNMStage, candidate.get("stage")),
        }
        if not any(fields.values()):
            continue
        model = PathologicalTNMStaging if candidate.get("staging_type") == "pathological" else ClinicalTNMStaging
        record = model.objects.create(observation=observation, **fields)
        provenance(record, review, run, "staging_candidates", candidate.get("t") or candidate.get("stage"), user)
        counts["tnm_stagings"] += 1

    for candidate in data.get("molecular_candidates", []):
        if not isinstance(candidate, dict):
            continue
        gene = option_by_name(MolecularPathologyGene, candidate.get("gene"))
        alteration_type = option_by_name(MolecularAlterationType, candidate.get("alteration_type"))
        result = option_by_name(MolecularPathologyResult, candidate.get("reported_result"))
        if not (gene and alteration_type and result):
            continue
        test = MolecularTest.objects.create(observation=observation, notes="Published from reviewed prescription extraction.")
        record = MolecularTestResult.objects.create(
            molecular_test=test,
            gene=gene,
            exon=option_by_name(MolecularPathologyExon, candidate.get("exon")),
            alteration_type=alteration_type,
            result=result,
            dna_change=str(value_of(candidate.get("variant")) or ""),
            origin=MolecularTestResult.Origin.EXPLICIT,
        )
        provenance(record, review, run, "molecular_candidates", candidate.get("gene"), user)
        counts["molecular_results"] += 1
    return counts


@transaction.atomic
def publish_review(review, user):
    if review.status != PrescriptionReview.Status.APPROVED:
        raise ValidationError("Only approved reviews can be published.")
    if review.published_at:
        raise ValidationError("This review has already been published.")
    if not review.selected_patient_id:
        raise ValidationError("A reviewer must select the patient before publishing.")
    observation = ClinicalObservation.objects.create(
        patient=review.selected_patient,
        status=ClinicalObservation.Status.PUBLISHED,
        published_at=timezone.now(),
        published_by=user,
        clinical_notes="Published from human-reviewed prescription extraction.",
    )
    run = review.document.extraction_runs.filter(status="completed").first()
    provenance(observation, review, run, "clinical_observation", None, user)
    counts = publish_reviewed_candidates(observation, review, run, user)
    review.published_at = timezone.now()
    review.published_by = user
    review.save(update_fields=["published_at", "published_by", "updated_at"])
    return observation, counts
