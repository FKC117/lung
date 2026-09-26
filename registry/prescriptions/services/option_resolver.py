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
        "metastatic_sites": "diagnosis-metastatic-sites",
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
        "partner_gene": "molecular-genes",
        "exon": "molecular-exons",
        "alteration_type": "molecular-alteration-types",
        "reported_result": "molecular-results",
        "result": "molecular-results",
        "clinical_significance": "molecular-clinical-significances",
        "panel": "molecular-panels",
        "panel_version": "molecular-panel-versions",
        "panel_target": "molecular-panel-targets",
    },
    "cancer_markers": {"marker": "cancer-marker-names", "marker_name": "cancer-marker-names"},
    "treatments": {
        "modality": "treatment-modalities",
        "line_of_treatment": "lines-of-treatment",
        "protocol": "treatment-protocols",
        "drug": "treatment-drugs",
        "protocol_drug": "treatment-protocol-drugs",
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
    "progression_records": {"status": "disease-progression-statuses", "progression_sites": "progression-sites", "estimation_method": "response-estimation-methods"},
    "survival_records": {"status": "survival-statuses"},
}

MULTI_OPTION_FIELDS = {("diagnoses", "metastatic_sites"), ("progression_records", "progression_sites")}

# These historical lookup models were deleted by existing options migrations.
# A draft may retain their extracted text for review, but it cannot claim a
# controlled resolution until the registry has an active canonical option.
RETIRED_PARENT_SCOPED_FIELDS = {
    "molecular_tests": {"mutation"},
    "treatments": {"protocol_cycle", "treatment_protocol_cycle"},
}

RESOLUTION_SCOPES = {
    ("diagnoses", "disease_subgroup"): {"disease_group_id": "disease_group"},
    ("molecular_tests", "exon"): {"gene_id": "gene"},
    ("molecular_tests", "panel_version"): {"panel_id": "panel"},
    ("molecular_tests", "panel_target"): {
        "panel_version_id": "panel_version",
        "gene_id": "gene",
        "alteration_type_id": "alteration_type",
    },
    ("treatments", "protocol_drug"): {
        "protocol_id": "protocol",
        "drug_id": "drug",
    },
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
                    filters = {}
                    for filter_name, parent_field in RESOLUTION_SCOPES.get((collection, field), {}).items():
                        parent = resolutions.get(parent_field, {})
                        if parent.get("status") == "resolved" and parent.get("option_id") is not None:
                            filters[filter_name] = parent["option_id"]
                    resolutions[field] = resolve_option(resource, str(raw_value), filters=filters)
                    if resolutions[field]["status"] in {"ambiguous", "unresolved"}:
                        record["state"] = "unresolved"
    return resolved


def validate_selected_resolutions(draft):
    """Verify that reviewer-selected option IDs belong to their declared resource."""
    patient_values = draft.get("patient", {}).get("values", {})
    district_id = patient_values.get("district")
    thana_id = patient_values.get("thana")
    if isinstance(thana_id, int) and not isinstance(thana_id, bool):
        if not isinstance(district_id, int) or isinstance(district_id, bool):
            raise ValidationError({"patient.thana": "A selected thana requires a selected district."})
        if not OPTION_RESOURCES["thanas"].objects.filter(pk=thana_id, district_id=district_id).exists():
            raise ValidationError({"patient.thana": "The selected thana does not belong to the selected district."})
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
                    option_ids = resolution.get("option_ids")
                    status = resolution.get("status")
                    if resource != expected_fields[field]:
                        raise ValidationError({field: "Resolution uses the wrong option resource."})
                    if status not in {"resolved", "ambiguous", "unresolved"}:
                        raise ValidationError({field: "Resolution has an invalid status."})
                    is_multi = (collection, field) in MULTI_OPTION_FIELDS
                    if is_multi:
                        if option_id is not None:
                            raise ValidationError({field: "A multi-select resolution uses option_ids, not option_id."})
                        if not isinstance(option_ids, list) or any(not isinstance(item, int) or isinstance(item, bool) for item in option_ids):
                            raise ValidationError({field: "A multi-select resolution requires an option_ids list."})
                        if status != "resolved" and option_ids:
                            raise ValidationError({field: "Only a resolved value may select option IDs."})
                        if len(option_ids) != len(set(option_ids)):
                            raise ValidationError({field: "A multi-select resolution cannot contain duplicate option IDs."})
                        if OPTION_RESOURCES[resource].objects.filter(pk__in=option_ids).count() != len(option_ids):
                            raise ValidationError({field: "A selected option does not exist in that resource."})
                        value_ids = record.get("values", {}).get(field, [])
                        if status == "resolved" and (not isinstance(value_ids, list) or any(not isinstance(item, int) or isinstance(item, bool) for item in value_ids) or sorted(value_ids) != sorted(option_ids)):
                            raise ValidationError({field: "Validated multi-select values must match their resolved option IDs."})
                        continue
                    if option_ids is not None:
                        raise ValidationError({field: "A single-select resolution cannot use option_ids."})
                    if status != "resolved" and option_id is not None:
                        raise ValidationError({field: "Only a resolved value may select an option ID."})
                    if status == "resolved" and option_id is None:
                        raise ValidationError({field: "A resolved value requires an option ID."})
                    if option_id is None:
                        continue
                    if not isinstance(option_id, int) or isinstance(option_id, bool) or not OPTION_RESOURCES[resource].objects.filter(pk=option_id).exists():
                        raise ValidationError({field: "The selected option does not exist in that resource."})
                _validate_record_hierarchies(collection, record)
    return draft


def _resolved_id(record, field):
    resolution = record.get("resolutions", {}).get(field, {})
    if resolution.get("status") == "resolved":
        return resolution.get("option_id")
    return None


def _require_parent(record, *, child_field, parent_field, relation_field, collection):
    child_id = _resolved_id(record, child_field)
    if child_id is None:
        return
    parent_id = _resolved_id(record, parent_field)
    if parent_id is None:
        raise ValidationError({child_field: f"A resolved {child_field} requires a resolved {parent_field}."})
    resource = OPTION_FIELDS[collection][child_field]
    if not OPTION_RESOURCES[resource].objects.filter(pk=child_id, **{relation_field: parent_id}).exists():
        raise ValidationError({child_field: f"The selected {child_field} does not belong to the selected {parent_field}."})


def _validate_record_hierarchies(collection, record):
    if collection == "diagnoses":
        _require_parent(
            record,
            child_field="disease_subgroup",
            parent_field="disease_group",
            relation_field="disease_group_id",
            collection=collection,
        )
    elif collection == "molecular_tests":
        _require_parent(
            record,
            child_field="exon",
            parent_field="gene",
            relation_field="gene_id",
            collection=collection,
        )
        _require_parent(
            record,
            child_field="panel_version",
            parent_field="panel",
            relation_field="panel_id",
            collection=collection,
        )
        for parent_field, relation_field in (
            ("panel_version", "panel_version_id"),
            ("gene", "gene_id"),
            ("alteration_type", "alteration_type_id"),
        ):
            _require_parent(
                record,
                child_field="panel_target",
                parent_field=parent_field,
                relation_field=relation_field,
                collection=collection,
            )
        target_id = _resolved_id(record, "panel_target")
        exon_id = _resolved_id(record, "exon")
        if target_id is not None and exon_id is not None:
            target_model = OPTION_RESOURCES["molecular-panel-targets"]
            target = target_model.objects.get(pk=target_id)
            if target.covered_exons.exists() and not target.covered_exons.filter(pk=exon_id).exists():
                raise ValidationError({"exon": "The selected exon is not covered by the selected panel target."})
    elif collection == "treatments":
        protocol_id = _resolved_id(record, "protocol")
        drug_id = _resolved_id(record, "drug")
        membership = OPTION_RESOURCES["treatment-protocol-drugs"]
        if protocol_id is not None and drug_id is not None and not membership.objects.filter(
            protocol_id=protocol_id, drug_id=drug_id
        ).exists():
            raise ValidationError({"drug": "The selected drug does not belong to the selected protocol."})
        for parent_field, relation_field in (("protocol", "protocol_id"), ("drug", "drug_id")):
            _require_parent(
                record,
                child_field="protocol_drug",
                parent_field=parent_field,
                relation_field=relation_field,
                collection=collection,
            )


def validate_approval_readiness(draft):
    """Reject approval while any review decision remains unresolved."""
    errors = []
    if draft.get("patient", {}).get("match_status") == "unresolved":
        errors.append("Patient matching is unresolved.")
    if draft.get("unresolved_items"):
        errors.append("The draft still contains unresolved items.")

    for observation_index, observation in enumerate(draft.get("observations", [])):
        for collection, fields in OPTION_FIELDS.items():
            retired_fields = RETIRED_PARENT_SCOPED_FIELDS.get(collection, set())
            for record_index, record in enumerate(observation.get(collection, [])):
                path = f"observations.{observation_index}.{collection}.{record_index}"
                if record.get("state") == "unresolved":
                    errors.append(f"{path} is unresolved.")
                values = record.get("values", {})
                resolutions = record.get("resolutions", {})
                for field in retired_fields:
                    if values.get(field) not in (None, ""):
                        errors.append(f"{path}.{field} has no active controlled option and remains unresolved.")
                for field in fields:
                    raw_value = values.get(field)
                    if raw_value in (None, "", []) or isinstance(raw_value, dict):
                        continue
                    resolution = resolutions.get(field)
                    if not resolution or resolution.get("status") != "resolved":
                        errors.append(f"{path}.{field} is not resolved.")
                for field, resolution in resolutions.items():
                    if resolution.get("status") in {"ambiguous", "unresolved"}:
                        errors.append(f"{path}.{field} is {resolution.get('status')}.")
    if errors:
        raise ValidationError({"approval": errors})
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
