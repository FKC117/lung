"""Validate reviewer decisions without rewriting original fact evidence."""
from django.core.exceptions import ValidationError
from copy import deepcopy


def _context_target(draft, fact):
    """Locate a supported destination without guessing patient identity or placement."""
    from .field_contract import fields
    path = fact["source_path"]
    key = fact.get("canonical_field") or path.rsplit(".", 1)[-1]
    if path.startswith("patient."):
        # Provider identifiers were deliberately never copied into identity fields.
        if key in {"patient_id", "registration_no"}:
            return None, key, None
        return draft["patient"]["values"], key, fields("patient").get(key)
    observation = next((item for item in draft["observations"] if item["temp_id"] == fact.get("observation_temp_id")), None)
    if not observation:
        return None, key, None
    if ".anthropometry." in path:
        values = observation.get("anthropometry")
        return values if isinstance(values, dict) else None, key, fields("anthropometry").get(key)
    if key == "temporal_context":
        return observation, key, {"choices": [{"value": item} for item in ("current", "historical", "planned", "unknown")]}
    return observation, key, fields("observation").get(key)


def _check_context_decision(draft, fact, decision):
    from .readiness import populated
    from .draft_schema import _validate_date
    from decimal import Decimal, InvalidOperation
    values, key, definition = _context_target(draft, fact)
    value = values.get(key) if values is not None else None
    if decision["action"] == "exclude":
        if definition and populated(value):
            raise ValidationError({"fact_decisions": "Clear the canonical context field before excluding its source fact."})
        if not definition and values is not None:
            values.pop(key, None)
        return
    if not definition or definition.get("readOnly") or definition.get("persisted") is False or not populated(value):
        raise ValidationError({"fact_decisions": "Reviewed context facts require a populated supported field; identifiers require separate explicit patient selection."})
    kind = definition.get("type")
    if kind in {"date", "datetime-local"}:
        _validate_date(value, key, date_time=kind == "datetime-local")
    if kind == "number":
        try:
            valid = not isinstance(value, bool) and Decimal(str(value)).is_finite() and Decimal(str(value)) >= 0
        except (InvalidOperation, ValueError):
            valid = False
        if not valid:
            raise ValidationError({"fact_decisions": "Correct the context numeric field first."})
    if definition.get("choices") and value not in [item["value"] for item in definition["choices"]]:
        raise ValidationError({"fact_decisions": "Choose a supported temporal context first."})
    if definition.get("resource"):
        from options.api_views import OPTION_RESOURCES
        if not isinstance(value, int) or isinstance(value, bool) or not OPTION_RESOURCES[definition["resource"]].objects.filter(pk=value).exists():
            raise ValidationError({"fact_decisions": "Choose a valid patient dropdown option first."})


def validate_fact_decisions(draft):
    decisions = draft.get("fact_decisions", [])
    facts = {item["fact_id"]: item for item in draft.get("source_facts", [])}
    if not isinstance(decisions, list):
        raise ValidationError({"fact_decisions": "Must be an array."})
    seen = set()
    for decision in decisions:
        if not isinstance(decision, dict) or set(decision) != {"fact_id", "action", "reason"}:
            raise ValidationError({"fact_decisions": "Expected fact_id, action and reason."})
        identity = decision["fact_id"]
        if not isinstance(identity, str) or identity not in facts or identity in seen:
            raise ValidationError({"fact_decisions": "Choose each existing source fact at most once."})
        if not isinstance(decision["action"], str) or decision["action"] not in {"exclude", "reviewed"}:
            raise ValidationError({"fact_decisions": "Action must be exclude or reviewed."})
        if not isinstance(decision["reason"], str) or not decision["reason"].strip():
            raise ValidationError({"fact_decisions": "An explicit reviewer reason is required."})
        seen.add(identity)
    return decisions


def reconcile_fact_decisions(draft):
    """Recheck affected fields; source evidence and unrelated blockers survive."""
    from .field_contract import fields
    from .readiness import populated, record_issues
    from .draft_schema import _validate_date
    from decimal import Decimal, InvalidOperation
    result = deepcopy(draft)
    facts = {item["fact_id"]: item for item in result.get("source_facts", [])}
    resolved = set()
    touched = set()
    checked_context = set()
    for decision in validate_fact_decisions(result):
        fact = facts[decision["fact_id"]]
        collection, record_id, key = fact.get("collection"), fact.get("record_temp_id"), fact.get("canonical_field")
        if not collection or not record_id or not key:
            _check_context_decision(result, fact, decision)
            checked_context.add(fact["fact_id"])
            continue
        record = next((record for observation in result["observations"] for record in observation.get(collection, []) if record["temp_id"] == record_id), None)
        if record is None:
            if decision["action"] == "exclude":
                resolved.add((collection, record_id, key))
            else:
                raise ValidationError({"fact_decisions": "A removed record requires exclusion, not a reviewed annotation."})
            continue
        definition = fields(collection).get(key)
        value = record["values"].get(key)
        if decision["action"] == "exclude":
            if definition and populated(value):
                raise ValidationError({"fact_decisions": "Clear the canonical field before excluding its source fact."})
            if not definition:
                record["values"].pop(key, None)
            resolution = record["resolutions"].get(key)
            if resolution and (resolution.get("option_id") or resolution.get("option_ids")):
                raise ValidationError({"fact_decisions": "Clear the canonical selection before exclusion."})
            record["resolutions"].pop(key, None)
        else:
            if not definition or definition.get("persisted") is False or not populated(value):
                raise ValidationError({"fact_decisions": "Reviewed facts require a populated supported canonical field."})
            kind = definition.get("type")
            if kind in {"date", "datetime-local"}:
                _validate_date(value, key, date_time=kind == "datetime-local")
            if kind == "number":
                try:
                    valid = not isinstance(value, bool) and Decimal(str(value)).is_finite()
                except (InvalidOperation, ValueError):
                    valid = False
                if not valid:
                    raise ValidationError({"fact_decisions": "Correct the numeric field before recording it as reviewed."})
            if kind == "boolean" and not isinstance(value, bool):
                raise ValidationError({"fact_decisions": "Correct the boolean field first."})
            if definition.get("choices") and value not in [item["value"] for item in definition["choices"]]:
                raise ValidationError({"fact_decisions": "Choose a valid canonical status first."})
            if definition.get("resource") and record["resolutions"].get(key, {}).get("status") != "resolved":
                raise ValidationError({"fact_decisions": "Choose a valid canonical dropdown option first."})
        resolved.add((collection, record_id, key))
        touched.add((collection, record_id))
    allowed = {"invalid_field_value", "unsupported_field", "unsupported_destination", "conflicting_alias", "unsupported_evidence", "fact_decision_required"}
    result["unresolved_items"] = [issue for issue in result["unresolved_items"] if not (
        issue.get("type") in allowed and (issue.get("collection"), issue.get("record_temp_id"), issue.get("field")) in resolved)]
    def context_issue_checked(issue):
        if issue.get("type") == "fact_decision_required" and issue.get("fact_id") in checked_context:
            return True
        if issue.get("type") == "unsupported_evidence" and issue.get("observation_temp_id"):
            return any(fact["fact_id"] in checked_context and fact.get("observation_temp_id") == issue["observation_temp_id"] and
                       fact["source_path"].split(".", 2)[-1] == issue.get("field_path") for fact in facts.values())
        if issue.get("type") == "extracted_observation":
            group = [fact for fact in facts.values() if fact.get("observation_temp_id") == issue.get("observation_temp_id") and
                     not fact.get("record_temp_id") and not _context_target(result, fact)[2] and fact["disposition"] == "unresolved"]
            return bool(group) and all(fact["fact_id"] in checked_context for fact in group)
        return False
    result["unresolved_items"] = [issue for issue in result["unresolved_items"] if not context_issue_checked(issue)]
    for fact in facts.values():
        if fact["disposition"] == "unresolved" and not fact.get("record_temp_id") and fact["fact_id"] not in checked_context:
            if not any(issue.get("fact_id") == fact["fact_id"] for issue in result["unresolved_items"]):
                result["unresolved_items"].append({"type": "fact_decision_required", "fact_id": fact["fact_id"], "observation_temp_id": fact.get("observation_temp_id"),
                    "reason": "Original unresolved context fact requires a checked reviewer decision."})
    for fact in facts.values():
        target = (fact.get("collection"), fact.get("record_temp_id"), fact.get("canonical_field"))
        if fact["disposition"] != "unresolved" or not target[1] or target in resolved:
            continue
        if not any((issue.get("collection"), issue.get("record_temp_id"), issue.get("field")) == target for issue in result["unresolved_items"]):
            result["unresolved_items"].append({"type": "fact_decision_required", "collection": target[0], "record_temp_id": target[1],
                "field": target[2], "reason": "Original unresolved fact requires a checked reviewer decision."})
        for observation in result["observations"]:
            for record in observation.get(target[0], []):
                if record["temp_id"] == target[1]:
                    record["state"] = "unresolved"
    for observation in result["observations"]:
        for collection, record_id in touched:
            record = next((item for item in observation.get(collection, []) if item["temp_id"] == record_id), None)
            if record and not record_issues(collection, record) and not any(issue.get("record_temp_id") == record_id for issue in result["unresolved_items"]):
                # Every original mapping exception needs its own checked decision.
                if all(fact.get("disposition") != "unresolved" or (collection, record_id, fact["canonical_field"]) in resolved for fact in record.get("fact_dispositions", [])):
                    record["state"] = "validated"
    return result


def validate_clinical_fact_coverage(draft):
    decisions = {item["fact_id"]: item for item in validate_fact_decisions(draft)}
    for fact in draft.get("source_facts", []):
        if fact.get("disposition") == "excluded":
            continue
        decision = decisions.get(fact["fact_id"])
        if fact.get("disposition") == "unresolved" and not decision:
            raise ValidationError({"approval": "Original unresolved clinical facts require explicit checked decisions."})
        if fact.get("record_temp_id"):
            present = any(record["temp_id"] == fact["record_temp_id"] and record["values"].get(fact.get("canonical_field")) not in (None, "", [])
                          for observation in draft["observations"] for record in observation.get(fact.get("collection"), []))
        else:
            values, key, definition = _context_target(draft, fact)
            present = bool(definition and values is not None and values.get(key) not in (None, "", []))
        raw = fact["raw_value"]
        raw = raw.get("value") if isinstance(raw, dict) and "value" in raw else raw
        if raw in (None, "", []):
            continue
        if not present and (not decision or decision["action"] != "exclude"):
            raise ValidationError({"approval": "Removed clinical facts require an explicit exclusion reason."})
