"""Versioned, draft-only contract for longitudinal prescription intake."""

from copy import deepcopy
from datetime import date, datetime
from uuid import uuid4

from django.core.exceptions import ValidationError

from records.models import Patient
from prescriptions.services.field_contract import fields, normalize_aliases, contract


SCHEMA_VERSION = 1
MATCH_STATUSES = {"existing", "new", "unresolved"}
TEMPORAL_CONTEXTS = {"current", "historical", "planned", "unknown"}
RECORD_STATES = {"extracted", "edited", "unresolved", "validated"}

COLLECTIONS = (
    "comorbidities",
    "diagnoses",
    "histopathologies",
    "ihc_results",
    "pathological_staging_results",
    "clinical_tnm_stagings",
    "pathological_tnm_stagings",
    "molecular_tests",
    "cancer_markers",
    "treatments",
    "surgeries",
    "radiotherapies",
    "recist_assessments",
    "irecist_assessments",
    "pathological_responses",
    "progression_records",
    "survival_records",
)

OBSERVATION_KEYS = {
    "temp_id",
    "observed_at",
    "prescription_date",
    "temporal_context",
    "anthropometry",
    *COLLECTIONS,
    "evidence_refs",
}
TOP_LEVEL_KEYS = {"schema_version", "document_id", "patient", "observations", "unresolved_items"}
OPTIONAL_TOP_LEVEL_KEYS = {"source_facts", "fact_decisions"}
PATIENT_KEYS = {"match_status", "patient_id", "values"}
EVIDENCE_KEYS = {"evidence_id", "field_path", "source_text", "page", "confidence"}
RECORD_KEYS = {"temp_id", "state", "values", "resolutions", "evidence_refs"}
OPTIONAL_RECORD_KEYS = {"extracted_values", "fact_dispositions"}

LEGACY_COLLECTIONS = {
    "diagnosis_candidates": "diagnoses",
    "histopathology_candidates": "histopathologies",
    "ihc_candidates": "ihc_results",
    "molecular_candidates": "molecular_tests",
    "cancer_marker_candidates": "cancer_markers",
    "treatment_candidates": "treatments",
    "medications": "treatments",
    "administration_candidates": "treatments",
    "surgery_candidates": "surgeries",
    "radiotherapy_candidates": "radiotherapies",
    "response_candidates": "recist_assessments",
    "progression_candidates": "progression_records",
    "survival_candidates": "survival_records",
}


def _temp_id(prefix):
    return f"{prefix}-{uuid4().hex}"


def empty_observation(*, temporal_context="unknown", temp_id=None):
    observation = {
        "temp_id": temp_id or _temp_id("observation"),
        "observed_at": None,
        "prescription_date": None,
        "temporal_context": temporal_context if temporal_context in TEMPORAL_CONTEXTS else "unknown",
        "anthropometry": None,
        "evidence_refs": [],
    }
    observation.update({name: [] for name in COLLECTIONS})
    return observation


def empty_draft(document_id, *, patient_id=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "document_id": int(document_id),
        "patient": {
            "match_status": "existing" if patient_id else "unresolved",
            "patient_id": int(patient_id) if patient_id else None,
            "values": {},
        },
        "observations": [],
        "unresolved_items": [],
    }


def is_canonical_draft(value):
    return isinstance(value, dict) and value.get("schema_version") == SCHEMA_VERSION and TOP_LEVEL_KEYS <= set(value)


def _evidence_value(value, *, field_path, evidence, evidence_ids):
    """Strip evidence metadata while retaining a separately addressable reference."""
    if isinstance(value, dict) and "value" in value and set(value) <= {"value", "source_text", "page", "confidence", "start", "end"}:
        evidence_id = _temp_id("evidence")
        evidence.append({
            "evidence_id": evidence_id,
            "field_path": field_path,
            "source_text": str(value.get("source_text") or ""),
            "page": value.get("page"),
            "confidence": value.get("confidence"),
            "extracted_value": deepcopy(value.get("value")),
        })
        evidence_ids.append(evidence_id)
        return value.get("value")
    if isinstance(value, dict):
        return {
            key: _evidence_value(item, field_path=f"{field_path}.{key}", evidence=evidence, evidence_ids=evidence_ids)
            for key, item in value.items()
            if key not in {"source_text", "page", "confidence", "start", "end"}
        }
    if isinstance(value, list):
        return [
            _evidence_value(item, field_path=f"{field_path}.{index}", evidence=evidence, evidence_ids=evidence_ids)
            for index, item in enumerate(value)
        ]
    return value


def _record_from_candidate(candidate, collection, index, observation, *, require_source_evidence=False):
    evidence_ids = []
    values = _evidence_value(
        candidate,
        field_path=f"{collection}.{index}",
        evidence=observation["evidence_refs"],
        evidence_ids=evidence_ids,
    )
    if not isinstance(values, dict):
        values = {"value": values}
    # Deterministic extractors may already have advisory match metadata. The
    # canonical contract regenerates all option IDs in ``resolutions`` so IDs
    # can never be mistaken for extracted clinical values.
    values = {key: value for key, value in values.items() if not key.endswith("_match")}
    original = deepcopy(values)
    values, issues = normalize_aliases(collection, values)
    definitions = fields(collection)
    from prescriptions.services.field_contract import ALIASES
    if require_source_evidence and isinstance(candidate, dict) and not {"source_text", "page", "confidence"} <= set(candidate):
        for key, raw_value in candidate.items():
            canonical = ALIASES.get(collection, {}).get(key, key)
            if canonical in definitions and raw_value not in (None, "", []) and not isinstance(raw_value, dict):
                issues.append({"code": "unsupported_evidence", "field": canonical, "reason": "The returned value has no field-level source evidence; verify it explicitly.", "raw_value": deepcopy(raw_value)})
                values[canonical] = None
    dispositions = []
    for key, value in original.items():
        from prescriptions.services.field_contract import ALIASES
        canonical = ALIASES.get(collection, {}).get(key, key)
        disposition = "mapped" if canonical in definitions else "unresolved"
        dispositions.append({"field": key, "canonical_field": canonical, "raw_value": deepcopy(value), "disposition": disposition})
    for key, value in values.items():
        if key not in definitions and value not in (None, "", []):
            issues.append({"code": "unsupported_field", "field": key, "reason": "This extracted fact has no supported field destination.", "raw_value": value})
        elif key in definitions and value not in (None, "", []):
            definition = definitions[key]
            if definition.get("persisted") is False:
                issues.append({"code": "unsupported_destination", "field": key, "reason": "This form field has no canonical persistence destination.", "raw_value": value})
            kind = definition.get("type")
            valid = True
            if kind in {"date", "datetime-local"}:
                try:
                    _validate_date(value, key, date_time=kind == "datetime-local")
                except ValidationError:
                    valid = False
            elif kind == "number":
                from decimal import Decimal, InvalidOperation
                try:
                    valid = not isinstance(value, bool) and Decimal(str(value)).is_finite()
                except (InvalidOperation, ValueError):
                    valid = False
            elif kind == "boolean":
                valid = isinstance(value, bool)
            elif definition.get("choices"):
                valid = value in [choice["value"] for choice in definition["choices"]]
            if not valid:
                issues.append({"code": "invalid_field_value", "field": key, "reason": "Extracted value requires explicit correction before canonical storage.", "raw_value": value})
                values[key] = None
    record_id = _temp_id(collection.rstrip("s"))
    for issue in issues:
        observation.setdefault("_mapping_issues", []).append({"type": issue["code"], **issue, "collection": collection, "record_index": index,
            "record_temp_id": record_id, "observation_temp_id": observation["temp_id"]})
        for disposition in dispositions:
            if disposition["canonical_field"] == issue["field"]:
                disposition["disposition"] = "unresolved"
    return {
        "temp_id": record_id,
        "state": "unresolved" if issues else "extracted",
        "values": values,
        "resolutions": {},
        "evidence_refs": evidence_ids,
        "extracted_values": normalize_aliases(collection, original)[0],
        "fact_dispositions": dispositions,
    }


def _patient_values(source, *, allow_identifier_fields=True):
    patient = source.get("patient") if isinstance(source.get("patient"), dict) else {}
    values = {}
    for key, value in patient.items():
        if key in {"identifiers", "phones", "match_candidates"}:
            continue
        from prescriptions.services.field_contract import ALIASES
        if not allow_identifier_fields and ALIASES.get("patient", {}).get(key, key) in {"registration_no", "patient_id"}:
            continue
        if isinstance(value, dict) and "value" in value and set(value) <= {"value", "source_text", "page", "confidence", "start", "end"}:
            values[key] = value.get("value")
        elif not isinstance(value, (dict, list)):
            values[key] = value
    identifiers = patient.get("identifiers") if allow_identifier_fields and isinstance(patient.get("identifiers"), list) else []
    for item in identifiers:
        if not isinstance(item, dict):
            continue
        field = item.get("patient_field") or item.get("identifier_type")
        if field in {"registration_no", "patient_id"} and item.get("value"):
            values.setdefault(field, item.get("value"))
    phones = patient.get("phones") if isinstance(patient.get("phones"), list) else []
    if phones:
        first = phones[0]
        values.setdefault("phone", first.get("value") if isinstance(first, dict) else first)
    return normalize_aliases("patient", values)[0]


def _append_extractor_observations(draft, extracted):
    for index, item in enumerate(extracted or []):
        if not isinstance(item, dict):
            draft["unresolved_items"].append({"type": "observation", "reason": "Extractor observation was not an object.", "raw_value": item})
            continue
        temporal = str(item.get("temporal_context") or "unknown").casefold()
        if temporal == "uncertain":
            temporal = "unknown"
        observation = empty_observation(temporal_context=temporal, temp_id=f"observation-extracted-{index + 1}")
        observation["observed_at"] = _evidence_value(
            item.get("observed_at"),
            field_path="observed_at",
            evidence=observation["evidence_refs"],
            evidence_ids=[],
        )
        observation["prescription_date"] = _evidence_value(
            item.get("prescription_date"),
            field_path="prescription_date",
            evidence=observation["evidence_refs"],
            evidence_ids=[],
        )
        if isinstance(item.get("anthropometry"), dict):
            observation["anthropometry"] = _evidence_value(
                item["anthropometry"],
                field_path="anthropometry",
                evidence=observation["evidence_refs"],
                evidence_ids=[],
            )
        recognized = False
        for collection in COLLECTIONS:
            candidates = item.get(collection)
            if isinstance(candidates, list):
                recognized = recognized or bool(candidates)
                observation[collection].extend(
                    _record_from_candidate(candidate, collection, candidate_index, observation, require_source_evidence=True)
                    for candidate_index, candidate in enumerate(candidates)
                )
        evidence = item.get("evidence")
        if evidence:
            _evidence_value(evidence, field_path="observation", evidence=observation["evidence_refs"], evidence_ids=[])
        unknown = {key: value for key, value in item.items() if key not in OBSERVATION_KEYS | {"event_type", "evidence"}}
        if unknown or (not recognized and item.get("event_type")):
            draft["unresolved_items"].append({
                "type": "extracted_observation",
                "observation_temp_id": observation["temp_id"],
                "reason": "Extractor fields require human placement in a supported record section.",
                "raw_value": unknown or {"event_type": item.get("event_type")},
            })
        draft["unresolved_items"].extend(observation.pop("_mapping_issues", []))
        draft["observations"].append(observation)


def normalize_extraction(source, *, document_id, linked_patient_id=None):
    """Convert extractor/legacy review output to schema v1 without clinical writes."""
    if is_canonical_draft(source):
        draft = deepcopy(source)
        draft["document_id"] = int(document_id)
        validate_draft(draft, document_id=document_id, check_database=False)
        return draft

    source = source if isinstance(source, dict) else {}
    draft = empty_draft(document_id, patient_id=linked_patient_id)
    gemini = source.get("gemini_extraction") if isinstance(source.get("gemini_extraction"), dict) else {}
    patient_source = gemini if gemini.get("patient") else source
    # LLM output may help with patient name/age, but it is not trusted for
    # identifiers. HN/registration values come only from deterministic,
    # label-aware parsing so a clinician's BMDC number cannot become a patient
    # registration number.
    draft["patient"]["values"] = _patient_values(patient_source, allow_identifier_fields=False)
    deterministic_patient_values = _patient_values(source)
    for field in ("registration_no", "patient_id"):
        if deterministic_patient_values.get(field):
            draft["patient"]["values"][field] = deterministic_patient_values[field]

    candidates = source.get("patient", {}).get("match_candidates", []) if isinstance(source.get("patient"), dict) else []
    if not linked_patient_id and candidates:
        draft["unresolved_items"].append({
            "type": "patient_match",
            "reason": "A reviewer must choose among registry patient candidates.",
            "candidates": candidates,
        })

    _append_extractor_observations(draft, gemini.get("observations", []))

    legacy_observation = empty_observation(temp_id="observation-legacy-1")
    for source_key, collection in LEGACY_COLLECTIONS.items():
        values = source.get(source_key)
        if not isinstance(values, list):
            continue
        for index, candidate in enumerate(values):
            legacy_observation[collection].append(_record_from_candidate(candidate, collection, index, legacy_observation))

    staging = source.get("staging_candidates")
    if isinstance(staging, list):
        for index, candidate in enumerate(staging):
            staging_type = candidate.get("staging_type") if isinstance(candidate, dict) else None
            collection = "pathological_tnm_stagings" if staging_type == "pathological" else "clinical_tnm_stagings"
            legacy_observation[collection].append(_record_from_candidate(candidate, collection, index, legacy_observation))

    if any(legacy_observation[name] for name in COLLECTIONS) or legacy_observation["evidence_refs"]:
        draft["unresolved_items"].extend(legacy_observation.pop("_mapping_issues", []))
        draft["observations"].append(legacy_observation)

    for item in source.get("unresolved_items", []) if isinstance(source.get("unresolved_items"), list) else []:
        draft["unresolved_items"].append(item if isinstance(item, dict) else {"type": "extraction", "reason": str(item)})
    for item in gemini.get("unresolved_items", []) if isinstance(gemini.get("unresolved_items"), list) else []:
        draft["unresolved_items"].append(item if isinstance(item, dict) else {"type": "gemini_extraction", "reason": str(item)})

    if not draft["observations"]:
        draft["observations"].append(empty_observation(temp_id="observation-1"))
    if gemini:
        from .record_reconciliation import reconcile_extracted_records
        reconcile_extracted_records(draft)
        from .fact_ledger import source_fact_ledger
        draft["source_facts"] = source_fact_ledger(gemini, draft)
    validate_draft(draft, document_id=document_id, check_database=False)
    return draft


def _validate_date(value, path, *, date_time=False):
    if value is None:
        return
    if not isinstance(value, str):
        raise ValidationError({path: "Must be an ISO-8601 string or null."})
    try:
        (datetime.fromisoformat if date_time else date.fromisoformat)(value.replace("Z", "+00:00") if date_time else value)
    except ValueError as exc:
        raise ValidationError({path: "Must be a valid ISO-8601 date/time."}) from exc


def validate_draft(draft, *, document_id=None, check_database=True):
    """Strictly validate the shared draft contract and return it unchanged."""
    if not isinstance(draft, dict):
        raise ValidationError("The intake draft must be an object.")
    if not TOP_LEVEL_KEYS <= set(draft) or set(draft) - TOP_LEVEL_KEYS - OPTIONAL_TOP_LEVEL_KEYS:
        raise ValidationError({"draft": f"Expected exactly these keys: {', '.join(sorted(TOP_LEVEL_KEYS))}."})
    if "source_facts" in draft:
        facts = draft["source_facts"]
        if not isinstance(facts, list):
            raise ValidationError({"source_facts": "Must be an array."})
        identities = set()
        for fact in facts:
            if (not isinstance(fact, dict) or not isinstance(fact.get("fact_id"), str) or not fact["fact_id"]
                    or fact["fact_id"] in identities or not isinstance(fact.get("source_path"), str)
                    or "raw_value" not in fact or fact.get("disposition") not in {"mapped", "unresolved", "excluded"}
                    or (fact["disposition"] != "mapped" and not fact.get("reason"))):
                raise ValidationError({"source_facts": "Every fact requires a unique identity, original value and explained disposition."})
            identities.add(fact["fact_id"])
    if draft.get("schema_version") != SCHEMA_VERSION:
        raise ValidationError({"schema_version": f"Only schema version {SCHEMA_VERSION} is supported."})
    if not isinstance(draft.get("document_id"), int) or isinstance(draft.get("document_id"), bool):
        raise ValidationError({"document_id": "Must be an integer."})
    if document_id is not None and draft["document_id"] != int(document_id):
        raise ValidationError({"document_id": "The draft does not belong to this prescription document."})

    patient = draft.get("patient")
    if not isinstance(patient, dict) or set(patient) != PATIENT_KEYS:
        raise ValidationError({"patient": f"Expected exactly these keys: {', '.join(sorted(PATIENT_KEYS))}."})
    if patient["match_status"] not in MATCH_STATUSES:
        raise ValidationError({"patient.match_status": "Must be existing, new, or unresolved."})
    patient_id = patient["patient_id"]
    if patient["match_status"] == "existing" and not isinstance(patient_id, int):
        raise ValidationError({"patient.patient_id": "An existing match requires a patient ID."})
    if patient["match_status"] != "existing" and patient_id is not None:
        raise ValidationError({"patient.patient_id": "Only an existing match may have a patient ID."})
    if not isinstance(patient["values"], dict):
        raise ValidationError({"patient.values": "Must be an object."})
    if check_database and patient_id is not None and not Patient.objects.filter(pk=patient_id).exists():
        raise ValidationError({"patient.patient_id": "The selected patient does not exist."})

    observations = draft.get("observations")
    if not isinstance(observations, list) or not observations:
        raise ValidationError({"observations": "At least one observation draft is required."})
    unresolved = draft.get("unresolved_items")
    if not isinstance(unresolved, list) or any(not isinstance(item, dict) for item in unresolved):
        raise ValidationError({"unresolved_items": "Must be an array of objects."})

    all_temp_ids = set()
    for observation_index, observation in enumerate(observations):
        prefix = f"observations.{observation_index}"
        if not isinstance(observation, dict) or set(observation) != OBSERVATION_KEYS:
            raise ValidationError({prefix: f"Expected exactly these keys: {', '.join(sorted(OBSERVATION_KEYS))}."})
        temp_id = observation.get("temp_id")
        if not isinstance(temp_id, str) or not temp_id.strip() or temp_id in all_temp_ids:
            raise ValidationError({f"{prefix}.temp_id": "Must be a non-empty ID unique within the draft."})
        all_temp_ids.add(temp_id)
        if observation.get("temporal_context") not in TEMPORAL_CONTEXTS:
            raise ValidationError({f"{prefix}.temporal_context": "Must be current, historical, planned, or unknown."})
        _validate_date(observation.get("observed_at"), f"{prefix}.observed_at", date_time=True)
        _validate_date(observation.get("prescription_date"), f"{prefix}.prescription_date")
        if observation.get("anthropometry") is not None and not isinstance(observation["anthropometry"], dict):
            raise ValidationError({f"{prefix}.anthropometry": "Must be an object or null."})

        evidence = observation.get("evidence_refs")
        if not isinstance(evidence, list):
            raise ValidationError({f"{prefix}.evidence_refs": "Must be an array."})
        evidence_ids = set()
        for evidence_index, item in enumerate(evidence):
            path = f"{prefix}.evidence_refs.{evidence_index}"
            if not isinstance(item, dict) or not EVIDENCE_KEYS <= set(item) or set(item) - EVIDENCE_KEYS - {"extracted_value"}:
                raise ValidationError({path: f"Expected exactly these keys: {', '.join(sorted(EVIDENCE_KEYS))}."})
            evidence_id = item.get("evidence_id")
            if not isinstance(evidence_id, str) or not evidence_id or evidence_id in evidence_ids:
                raise ValidationError({f"{path}.evidence_id": "Must be unique within the observation."})
            evidence_ids.add(evidence_id)
            page = item.get("page")
            if page is not None and (not isinstance(page, int) or isinstance(page, bool) or page < 1):
                raise ValidationError({f"{path}.page": "Must be a positive integer or null."})
            confidence = item.get("confidence")
            if confidence is not None and (not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1):
                raise ValidationError({f"{path}.confidence": "Must be between 0 and 1 or null."})

        for collection in COLLECTIONS:
            records = observation.get(collection)
            if not isinstance(records, list):
                raise ValidationError({f"{prefix}.{collection}": "Must be an array."})
            for record_index, record in enumerate(records):
                path = f"{prefix}.{collection}.{record_index}"
                if not isinstance(record, dict) or not RECORD_KEYS <= set(record) or set(record) - RECORD_KEYS - OPTIONAL_RECORD_KEYS:
                    raise ValidationError({path: f"Expected exactly these keys: {', '.join(sorted(RECORD_KEYS))}."})
                record_id = record.get("temp_id")
                if not isinstance(record_id, str) or not record_id.strip() or record_id in all_temp_ids:
                    raise ValidationError({f"{path}.temp_id": "Must be a non-empty ID unique within the draft."})
                all_temp_ids.add(record_id)
                if record.get("state") not in RECORD_STATES:
                    raise ValidationError({f"{path}.state": "Must be extracted, edited, unresolved, or validated."})
                if not isinstance(record.get("values"), dict) or not isinstance(record.get("resolutions"), dict):
                    raise ValidationError({path: "Values and resolutions must be objects."})
                if "extracted_values" in record and not isinstance(record["extracted_values"], dict):
                    raise ValidationError({path: "Extracted values must be an object."})
                if "fact_dispositions" in record and (not isinstance(record["fact_dispositions"], list) or any(not isinstance(item, dict) or item.get("disposition") not in {"mapped", "unresolved", "excluded"} for item in record["fact_dispositions"])):
                    raise ValidationError({path: "Invalid fact dispositions."})
                refs = record.get("evidence_refs")
                if not isinstance(refs, list) or any(not isinstance(ref, str) or ref not in evidence_ids for ref in refs):
                    raise ValidationError({f"{path}.evidence_refs": "Every reference must identify evidence in the same observation."})
    from .fact_decisions import validate_fact_decisions
    validate_fact_decisions(draft)
    return draft
