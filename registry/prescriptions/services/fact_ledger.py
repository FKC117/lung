"""Immutable accounting of every returned provider field, including context."""
from copy import deepcopy
from .field_contract import ALIASES, fields


def source_fact_ledger(payload, draft):
    from .draft_schema import COLLECTIONS
    facts = []

    def add(path, value, disposition, reason="", **target):
        facts.append({"fact_id": path, "source_path": path, "raw_value": deepcopy(value),
                      "disposition": disposition, "reason": reason, **target})

    for key, value in payload.items():
        if key == "patient" and isinstance(value, dict):
            for field, raw in value.items():
                canonical = ALIASES.get("patient", {}).get(field, field)
                mapped = (canonical in fields("patient") and canonical in draft["patient"]["values"]
                          and canonical not in {"registration_no", "patient_id"}
                          and draft["patient"]["values"][canonical] is not None)
                add(f"patient.{field}", raw, "mapped" if mapped else "unresolved",
                    "" if mapped else "Patient fact requires explicit placement or authorized identity selection.", canonical_field=canonical)
        elif key == "observations" and isinstance(value, list):
            for index, observation in enumerate(value):
                path = f"observations.{index}"
                target_observation = next((item for item in draft["observations"] if item["temp_id"] == f"observation-extracted-{index + 1}"), None)
                if not isinstance(observation, dict) or not target_observation:
                    add(path, observation, "unresolved", "Observation requires supported placement.")
                    continue
                for field, raw in observation.items():
                    target = {"observation_temp_id": target_observation["temp_id"]}
                    if field in COLLECTIONS and isinstance(raw, list):
                        for record_index, candidate in enumerate(raw):
                            record_path = f"{path}.{field}.{record_index}"
                            record = target_observation[field][record_index]
                            if not isinstance(candidate, dict):
                                add(record_path, candidate, "unresolved", "Record requires supported placement.", **target)
                                continue
                            for original, fact_value in candidate.items():
                                disposition = next((item["disposition"] for item in record["fact_dispositions"] if item["field"] == original), "unresolved")
                                add(f"{record_path}.{original}", fact_value, disposition,
                                    "" if disposition == "mapped" else "Returned field requires explicit correction or placement.",
                                    collection=field, record_temp_id=record["temp_id"], canonical_field=ALIASES.get(field, {}).get(original, original), **target)
                    elif field in {"observed_at", "prescription_date", "temporal_context"}:
                        add(f"{path}.{field}", raw, "mapped", canonical_field=field, **target)
                    elif field == "anthropometry" and isinstance(raw, dict):
                        for name, fact_value in raw.items():
                            mapped = name in fields("anthropometry")
                            add(f"{path}.{field}.{name}", fact_value, "mapped" if mapped else "unresolved",
                                "" if mapped else "Anthropometry field has no supported destination.", canonical_field=name, **target)
                    else:
                        add(f"{path}.{field}", raw, "unresolved", "Observation field requires supported placement.", **target)
        else:
            metadata = key in {"schema_version", "warnings", "unresolved_items"}
            add(key, value, "excluded" if metadata else "unresolved",
                "Provider metadata retained for audit; not a clinical form fact." if metadata else "Returned field has no supported destination.")
    return facts
