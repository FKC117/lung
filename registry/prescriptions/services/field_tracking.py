"""Field-coverage tracking for human review; absence is never a clinical conclusion."""


def entry(key, label, state, evidence_count=0, detail=""):
    return {
        "key": key,
        "label": label,
        "state": state,
        "evidence_count": evidence_count,
        "detail": detail,
    }


def track_fields(result):
    """Attach a transparent coverage checklist to a deterministic extraction result."""
    patient = result.get("patient", {})
    identifiers = patient.get("identifiers", [])
    hns = [item for item in identifiers if item.get("identifier_type") in {"hn", "registration_no"}]
    phones = patient.get("phones", [])
    candidates = patient.get("match_candidates", [])
    medications = result.get("medications", [])
    dates = result.get("date_candidates", [])
    resolved_dates = [item for item in dates if item.get("normalized_date")]
    resolved_drugs = [item for item in medications if item.get("drug_match", {}).get("status") == "resolved"]

    groups = [
        {
            "group": "Patient identification",
            "fields": [
                entry("patient.hn_registration_no", "HN / hospital registration number", "evidence_found" if hns else "not_found_in_document", len(hns)),
                entry("patient.phone", "Phone number", "evidence_found" if phones else "not_found_in_document", len(phones)),
                entry("patient.match", "Existing patient match", "review_required" if candidates else "not_found_in_registry", len(candidates), "A reviewer must select a patient; candidates are never auto-selected."),
            ],
        },
        {
            "group": "Prescription context",
            "fields": [
                entry("prescription.date", "Prescription/date references", "evidence_found" if resolved_dates else ("review_required" if dates else "not_found_in_document"), len(dates)),
                entry("prescription.prescriber", "Prescriber", "evidence_found" if result.get("prescriber_candidates") else "not_found_in_document", len(result.get("prescriber_candidates", []))),
            ],
        },
        {
            "group": "Medication prescription",
            "fields": [
                entry("medication.drug", "Drug", "evidence_found" if medications else "not_found_in_document", len(medications)),
                entry("medication.strength", "Strength", "evidence_found" if any(item.get("strength") for item in medications) else "not_found_in_document", sum(bool(item.get("strength")) for item in medications)),
                entry("medication.frequency", "Frequency", "evidence_found" if any(item.get("frequency") for item in medications) else "review_required", sum(bool(item.get("frequency")) for item in medications)),
                entry("medication.option_match", "Approved drug option match", "evidence_found" if resolved_drugs else ("review_required" if medications else "not_found_in_document"), len(resolved_drugs)),
            ],
        },
        {
            "group": "Clinical fields",
            "fields": [
                entry("diagnosis", "Diagnosis", "evidence_found" if result.get("diagnosis_candidates") else "not_found_in_document", len(result.get("diagnosis_candidates", []))),
                entry("staging", "TNM / stage", "evidence_found" if result.get("staging_candidates") else "not_found_in_document", len(result.get("staging_candidates", []))),
                entry("histopathology", "Histopathology", "evidence_found" if result.get("histopathology_candidates") else "not_found_in_document", len(result.get("histopathology_candidates", []))),
                entry("molecular", "Molecular testing", "evidence_found" if result.get("molecular_candidates") else "not_found_in_document", len(result.get("molecular_candidates", []))),
                entry("ihc", "IHC results", "evidence_found" if result.get("ihc_candidates") else "not_found_in_document", len(result.get("ihc_candidates", []))),
                entry("treatment_course", "Treatment course and line", "evidence_found" if result.get("treatment_candidates") else "not_found_in_document", len(result.get("treatment_candidates", []))),
                entry("administration", "Explicit treatment administration", "evidence_found" if result.get("administration_candidates") else "not_found_in_document", len(result.get("administration_candidates", []))),
                entry("response", "Response assessment", "evidence_found" if result.get("response_candidates") else "not_found_in_document", len(result.get("response_candidates", []))),
                entry("progression", "Disease progression", "evidence_found" if result.get("progression_candidates") else "not_found_in_document", len(result.get("progression_candidates", []))),
                entry("survival", "Survival follow-up", "evidence_found" if result.get("survival_candidates") else "not_found_in_document", len(result.get("survival_candidates", []))),
                entry("surgery", "Surgery", "evidence_found" if result.get("surgery_candidates") else "not_found_in_document", len(result.get("surgery_candidates", []))),
                entry("radiotherapy", "Radiotherapy", "evidence_found" if result.get("radiotherapy_candidates") else "not_found_in_document", len(result.get("radiotherapy_candidates", []))),
                entry("cancer_markers", "Cancer markers", "evidence_found" if result.get("cancer_marker_candidates") else "not_found_in_document", len(result.get("cancer_marker_candidates", []))),
            ],
        },
    ]
    fields = [field for group in groups for field in group["fields"]]
    result["field_tracking"] = {
        "groups": groups,
        "summary": {state: sum(field["state"] == state for field in fields) for state in sorted({field["state"] for field in fields})},
        "note": "not_found_in_document means no evidence was extracted from this document; it is not a negative clinical finding.",
    }
    return result
