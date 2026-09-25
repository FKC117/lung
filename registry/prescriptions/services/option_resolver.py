"""Conservative resolution of extracted text against administered options."""

import re
import unicodedata
from copy import deepcopy
from difflib import SequenceMatcher

from django.core.exceptions import ValidationError

from options.api_views import OPTION_RESOURCES
from prescriptions.models import PrescriptionDrugAlias


OPTION_FIELDS = {
    "comorbidities": {"comorbidity": "comorbidities"},
    "diagnoses": {
        "disease_group": "diagnosis-disease-groups",
        "disease_subgroup": "diagnosis-disease-subgroups",
        "primary_site": "diagnosis-primary-sites",
        "laterality": "diagnosis-lateralities",
    },
    "histopathologies": {
        "histopathology_details": "histopathology-details",
        "histopathology_type": "histopathology-types",
        "histopathology_site": "histopathology-sites",
        "histopathology_grade": "histopathology-grades",
    },
    "ihc_results": {"marker": "ihc-cycles", "reported_result": "ihc-cycle-results", "result": "ihc-cycle-results"},
    "pathological_staging_results": {"feature": "ihc-staging-cycles", "result": "ihc-staging-cycle-results"},
    "clinical_tnm_stagings": {"t": "tnm-t", "n": "tnm-n", "m": "tnm-m", "stage": "tnm-stages"},
    "pathological_tnm_stagings": {"t": "tnm-t", "n": "tnm-n", "m": "tnm-m", "stage": "tnm-stages"},
    "molecular_tests": {
        "method": "molecular-methods",
        "specimen": "molecular-specimens",
        "gene": "molecular-genes",
        "exon": "molecular-exons",
        "alteration_type": "molecular-alteration-types",
        "reported_result": "molecular-results",
        "result": "molecular-results",
    },
    "cancer_markers": {"marker": "cancer-marker-names", "marker_name": "cancer-marker-names"},
    "treatments": {
        "modality": "treatment-modalities",
        "line_of_treatment": "lines-of-treatment",
        "protocol": "treatment-protocols",
        "drug": "treatment-drugs",
    },
    "surgeries": {"modality": "surgery-modalities", "laterality": "surgery-lateralities"},
    "radiotherapies": {"site": "radiotherapy-sites", "intent": "radiotherapy-intents", "modality": "radiotherapy-modalities"},
    "recist_assessments": {
        "target_lesion": "recist-target-lesions",
        "non_target_lesion": "recist-non-target-lesions",
        "new_lesion": "recist-new-lesions",
        "overall_response": "recist-response-results",
        "estimation_method": "response-estimation-methods",
    },
    "irecist_assessments": {
        "target_lesion": "irecist-target-lesions",
        "non_target_lesion": "irecist-non-target-lesions",
        "new_lesion": "irecist-new-lesions",
        "overall_response": "irecist-response-results",
        "estimation_method": "response-estimation-methods",
    },
    "pathological_responses": {
        "response_category": "pathological-response-categories",
        "tumor_regression_grade": "tumor-regression-grades",
        "estimation_method": "response-estimation-methods",
    },
    "progression_records": {"status": "disease-progression-statuses", "estimation_method": "response-estimation-methods"},
    "survival_records": {"status": "survival-statuses"},
}


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or "")).casefold()
    value = "".join(character for character in value if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", "", value)


def _candidate(option, method, score=1.0):
    return {
        "option_id": option.pk,
        "label": str(option),
        "match_method": method,
        "score": round(score, 3),
    }


def _result(status, resource, raw_value, *, option=None, method=None, candidates=None, reason=""):
    return {
        "status": status,
        "resource": resource,
        "raw_value": raw_value,
        "option_id": option.pk if option is not None else None,
        "match_method": method,
        "candidates": candidates or [],
        "reason": reason,
    }


def resolve_option(resource, value, *, filters=None):
    """Resolve only a unique approved option; fuzzy output is suggestion-only."""
    if resource not in OPTION_RESOURCES:
        raise ValidationError({"resource": "Unknown option resource."})
    name = str(value or "").strip()
    if not name:
        return _result("unresolved", resource, value, reason="No option text was extracted.")

    model = OPTION_RESOURCES[resource]
    queryset = model.objects.all()
    filters = filters or {}
    valid_fields = {field.name for field in model._meta.fields}
    invalid_filters = set(filters) - valid_fields
    if invalid_filters:
        raise ValidationError({"filters": f"Invalid scope for {resource}: {', '.join(sorted(invalid_filters))}."})
    if filters:
        queryset = queryset.filter(**filters)
    options = list(queryset)

    if resource == "treatment-drugs":
        aliases = list(PrescriptionDrugAlias.objects.filter(alias__iexact=name).select_related("drug"))
        alias_drugs = {alias.drug_id: alias.drug for alias in aliases}
        if len(alias_drugs) == 1:
            option = next(iter(alias_drugs.values()))
            return _result("resolved", resource, value, option=option, method="approved_alias")
        if len(alias_drugs) > 1:
            return _result("ambiguous", resource, value, candidates=[_candidate(item, "approved_alias") for item in alias_drugs.values()], reason="Multiple approved aliases matched.")

    exact = [option for option in options if hasattr(option, "name") and option.name.casefold() == name.casefold()]
    if len(exact) == 1:
        return _result("resolved", resource, value, option=exact[0], method="exact_name")
    if len(exact) > 1:
        return _result("ambiguous", resource, value, candidates=[_candidate(item, "exact_name") for item in exact], reason="Multiple options have this name in the supplied scope.")

    target = normalize(name)
    normalized = [option for option in options if normalize(getattr(option, "name", str(option))) == target]
    if len(normalized) == 1:
        return _result("resolved", resource, value, option=normalized[0], method="normalized_name")
    if len(normalized) > 1:
        return _result("ambiguous", resource, value, candidates=[_candidate(item, "normalized_name") for item in normalized], reason="Multiple normalized option names matched.")

    suggestions = []
    for option in options:
        score = SequenceMatcher(None, target, normalize(getattr(option, "name", str(option)))).ratio()
        if score >= 0.70:
            suggestions.append(_candidate(option, "fuzzy", score))
    suggestions.sort(key=lambda item: (-item["score"], item["label"], item["option_id"]))
    if suggestions:
        return _result("ambiguous", resource, value, candidates=suggestions[:5], reason="Fuzzy matches require human selection.")
    return _result("unresolved", resource, value, reason="No approved option matched this text.")


def resolve_draft_options(draft):
    """Attach server-generated option resolutions without modifying extracted values."""
    resolved = deepcopy(draft)
    for observation in resolved.get("observations", []):
        for collection, fields in OPTION_FIELDS.items():
            for record in observation.get(collection, []):
                values = record.get("values", {})
                resolutions = record.setdefault("resolutions", {})
                for field, resource in fields.items():
                    existing = resolutions.get(field)
                    if isinstance(existing, dict) and existing.get("option_id") is not None:
                        continue
                    raw_value = values.get(field)
                    if raw_value in (None, "") or isinstance(raw_value, (dict, list)):
                        continue
                    resolutions[field] = resolve_option(resource, str(raw_value))
                    if resolutions[field]["status"] in {"ambiguous", "unresolved"}:
                        record["state"] = "unresolved"
    return resolved


def validate_selected_resolutions(draft):
    """Verify that reviewer-selected option IDs belong to their declared resource."""
    for observation in draft.get("observations", []):
        for collection, expected_fields in OPTION_FIELDS.items():
            for record in observation.get(collection, []):
                for field, resolution in record.get("resolutions", {}).items():
                    if not isinstance(resolution, dict):
                        raise ValidationError({field: "Resolution must be an object."})
                    if field not in expected_fields:
                        raise ValidationError({field: f"This field is not resolvable for {collection}."})
                    resource = resolution.get("resource")
                    option_id = resolution.get("option_id")
                    status = resolution.get("status")
                    if resource != expected_fields[field]:
                        raise ValidationError({field: "Resolution uses the wrong option resource."})
                    if status not in {"resolved", "ambiguous", "unresolved"}:
                        raise ValidationError({field: "Resolution has an invalid status."})
                    if status != "resolved" and option_id is not None:
                        raise ValidationError({field: "Only a resolved value may select an option ID."})
                    if status == "resolved" and option_id is None:
                        raise ValidationError({field: "A resolved value requires an option ID."})
                    if option_id is None:
                        continue
                    if not isinstance(option_id, int) or isinstance(option_id, bool) or not OPTION_RESOURCES[resource].objects.filter(pk=option_id).exists():
                        raise ValidationError({field: "The selected option does not exist in that resource."})
    return draft


# Backward-compatible helpers used by deterministic text extraction.
def resolve_drug(value):
    result = resolve_option("treatment-drugs", value)
    if result["status"] == "resolved":
        option = OPTION_RESOURCES["treatment-drugs"].objects.get(pk=result["option_id"])
        return {
            "status": "resolved",
            "resolution": result["match_method"],
            "matched_option": {
                "option_id": result["option_id"],
                "name": option.name,
                "match_method": result["match_method"],
                "score": 1.0,
            },
            "candidates": [],
        }
    return {"status": "review_required" if result["status"] == "ambiguous" else "unresolved", "reason": result["reason"], "candidates": result["candidates"]}


def resolve_medications(medications):
    for medication in medications:
        drug = medication.get("drug", {})
        medication["drug_match"] = resolve_drug(drug.get("value") if isinstance(drug, dict) else drug)
    return medications
