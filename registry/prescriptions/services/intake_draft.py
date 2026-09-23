"""Canonical review draft shaped like the registry intake form."""

def set_path(target, path, value):
    parts = path.split(".")
    current = target
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value

def build_intake_draft(result):
    draft = {key: {} for key in ("patient", "history", "smoking", "tb", "covid", "diagnosis", "histopathology", "ihc", "molecular", "treatment", "response", "progression", "survival", "surgery", "radiotherapy")}
    for candidate in result.get("form_field_candidates", []):
        set_path(draft, candidate["field_path"], {key: candidate[key] for key in ("value", "source_text", "page", "confidence")})
    patient = result.get("patient", {})
    draft["patient"].setdefault("registration_no", next((item for item in patient.get("identifiers", []) if item.get("patient_field") == "registration_no"), None))
    draft["patient"].setdefault("phone", patient.get("phones", [None])[0] if patient.get("phones") else None)
    draft["diagnosis"]["candidates"] = result.get("diagnosis_candidates", [])
    draft["diagnosis"]["staging"] = result.get("staging_candidates", [])
    draft["histopathology"]["candidates"] = result.get("histopathology_candidates", [])
    draft["ihc"]["results"] = result.get("ihc_candidates", [])
    draft["molecular"]["findings"] = result.get("molecular_candidates", [])
    draft["treatment"]["courses"] = result.get("treatment_candidates", [])
    draft["treatment"]["administrations"] = result.get("administration_candidates", [])
    draft["response"]["candidates"] = result.get("response_candidates", [])
    draft["progression"]["candidates"] = result.get("progression_candidates", [])
    draft["survival"]["candidates"] = result.get("survival_candidates", [])
    draft["surgery"]["candidates"] = result.get("surgery_candidates", [])
    draft["radiotherapy"]["candidates"] = result.get("radiotherapy_candidates", [])
    return draft
