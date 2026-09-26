"""Adapter from the established New Entry request to the canonical intake draft."""
from uuid import uuid4

from rest_framework.exceptions import ValidationError

from prescriptions.services.draft_schema import COLLECTIONS, empty_draft, empty_observation
from prescriptions.services.option_resolver import OPTION_FIELDS
from prescriptions.services.publish import persist_canonical_draft


def _record(values, collection):
    values = {key: value for key, value in values.items() if value not in (None, "", [])}
    resolutions = {}
    for field, resource in OPTION_FIELDS.get(collection, {}).items():
        value = values.get(field)
        if value in (None, "", []):
            continue
        if isinstance(value, list):
            resolutions[field] = {"status": "resolved", "resource": resource, "raw_value": "manual", "option_id": None, "option_ids": value, "match_method": "manual_selection", "candidates": [], "reason": ""}
        else:
            resolutions[field] = {"status": "resolved", "resource": resource, "raw_value": "manual", "option_id": value, "match_method": "manual_selection", "candidates": [], "reason": ""}
    return {"temp_id": f"manual-{collection}-{uuid4().hex}", "state": "validated", "values": values, "resolutions": resolutions, "evidence_refs": []}


def manual_payload_to_draft(payload, *, draft=False):
    def one(value, label):
        if not isinstance(value, list):
            return value
        if len(value) > 1:
            raise ValidationError({label: "Multiple selections are not supported by the current clinical model. Split them into separate records."})
        return value[0] if value else None
    patient_values = {**(payload.get("patient") or {}), **(payload.get("history") or {})}
    patient_values.update({
        "alcohol_history": (payload.get("history") or {}).get("history_of_alcohol_consumption"),
        "any_known_mutation": (payload.get("history") or {}).get("any_known_mutations"),
    })
    first = lambda name: ((payload.get(name) or [{}])[0] or {})
    smoking, tb, covid = first("smoking_history_records"), first("tb_history_records"), first("covid_history_records")
    patient_values.update({"smoking_history": smoking.get("smoking_history"), "cigarettes_per_day": smoking.get("cigarettes_per_day"), "smoking_duration_in_years": smoking.get("smoking_duration_in_years"), "quit_smoking_for_in_years": smoking.get("quit_smoking_for_years"), "tb_history": tb.get("tb_history"), "covid_history": covid.get("covid_history"), "covid_infection_date": covid.get("covid_infection_date"), "vaccine": covid.get("vaccine_name"), "vaccination_dose": covid.get("vaccination_dose"), "is_draft": draft})
    existing = payload.get("existing_patient_id")
    draft_data = empty_draft(0, patient_id=existing)
    draft_data["patient"] = {"match_status": "existing" if existing else "new", "patient_id": existing or None, "values": {key: value for key, value in patient_values.items() if value not in (None, "")}}
    observation = empty_observation(temp_id=f"manual-observation-{uuid4().hex}")
    observation.update({key: (payload.get("observation") or {}).get(key) for key in ("observed_at", "prescription_date")})
    observation["anthropometry"] = {key: (payload.get("history") or {}).get(key) for key in ("height_cm", "weight_kg") if (payload.get("history") or {}).get(key) not in (None, "")} or None
    def add(collection, rows):
        observation[collection].extend(_record(row, collection) for row in rows if isinstance(row, dict))
    add("comorbidities", payload.get("comorbidities") or [])
    for row in payload.get("diagnoses") or []:
        add("diagnoses", [{**row, "metastatic_sites": row.get("metastatic_sites") or []}])
    add("histopathologies", payload.get("histopathologies") or [])
    add("clinical_tnm_stagings", [{**row, "staged_on": row.get("staged_on") or row.get("staged_at")} for row in payload.get("clinical_tnm_stagings") or []])
    add("pathological_tnm_stagings", [{**row, "staged_on": row.get("staged_on") or row.get("staged_at")} for row in payload.get("pathological_tnm_stagings") or []])
    for panel in payload.get("ihc_panels") or []:
        add("ihc_results", [{"tested_at": panel.get("tested_at"), "marker": row.get("cycle"), "result": row.get("result")} for row in panel.get("results", [])])
        add("pathological_staging_results", [{"assessed_at": panel.get("tested_at"), "feature": row.get("cycle"), "result": row.get("result")} for row in panel.get("staging_results", [])])
    add("cancer_markers", [{"marker": row.get("marker_name"), "value": row.get("marker_value"), "tested_on": row.get("tested_at")} for row in payload.get("cancer_markers") or []])
    add("molecular_tests", payload.get("molecular_tests") or [])
    for row in payload.get("treatment_cycles") or []:
        treatment = _record({"modality": one(row.get("modalities"), "treatment modalities"), "protocol": row.get("treatment_protocol"), "line_of_treatment": row.get("line_of_treatment"), "started_on": row.get("started_at"), "ended_on": row.get("ended_at"), "status": row.get("status"), "notes": row.get("course_notes") or row.get("chemotherapy_details"), "administrations": row.get("administrations") or []}, "treatments")
        observation["treatments"].append(treatment)
        link = {"treatment_temp_id": treatment["temp_id"]}
        add("recist_assessments", [{**link, "assessed_on": item.get("assessed_at"), "timepoint": item.get("timepoint") or "on_treatment", "target_lesion": item.get("target_lesion"), "non_target_lesion": item.get("non_target_lesion"), "new_lesion": item.get("new_lesion"), "overall_response": item.get("response_result"), "estimation_method": item.get("estimation_method"), "notes": item.get("notes")} for item in row.get("recist11_assessments", [])])
        add("irecist_assessments", [{**link, "assessed_on": item.get("assessed_at"), "timepoint": item.get("timepoint") or "on_treatment", "target_lesion": item.get("target_lesion"), "non_target_lesion": item.get("non_target_lesion"), "new_lesion": item.get("new_lesion"), "overall_response": item.get("response_result"), "estimation_method": item.get("estimation_method"), "notes": item.get("notes")} for item in row.get("irecist_assessments", [])])
        add("pathological_responses", [{**link, "assessed_on": item.get("assessed_at"), "timepoint": item.get("timepoint") or "post_treatment", "response_category": item.get("response_category"), "residual_viable_tumor_percentage": item.get("residual_viable_tumor_percentage"), "tumor_regression_grade": item.get("tumor_regression_grade"), "estimation_method": item.get("estimation_method"), "notes": item.get("notes")} for item in row.get("pathological_response_records", []) if item.get("assessed_at")])
    add("progression_records", payload.get("progression_records") or [])
    add("survival_records", payload.get("survival_followups") or [])
    add("surgeries", [{"modality": row.get("surgery_modality"), "laterality": one(row.get("lateralities"), "surgery lateralities"), "surgery_date": row.get("surgery_date"), "status": row.get("status"), "procedure_details": row.get("procedure_details"), "operative_findings": row.get("operative_findings"), "complications": row.get("complications"), "notes": row.get("notes")} for row in payload.get("surgeries") or []])
    add("radiotherapies", [{"site": one(row.get("sites"), "radiotherapy sites"), "intent": row.get("radiotherapy_intent"), "modality": one(row.get("modalities"), "radiotherapy modalities"), "started_on": row.get("started_at"), "ended_on": row.get("ended_at"), "dose_per_fraction_cgy": row.get("fraction_dose"), "planned_fractions": row.get("fraction_count"), "completed_fractions": row.get("completed_fractions"), "status": row.get("status"), "reason_for_stopping": row.get("reason_for_stopping"), "notes": row.get("notes")} for row in payload.get("radiotherapy_schedules") or []])
    draft_data["observations"] = [observation]
    return draft_data


def persist_manual_entry(payload, *, user, draft=False):
    canonical = manual_payload_to_draft(payload, draft=draft)
    from records.models import ClinicalObservation
    return persist_canonical_draft(canonical, user=user, observation_status=ClinicalObservation.Status.DRAFT if draft else ClinicalObservation.Status.PUBLISHED), canonical
