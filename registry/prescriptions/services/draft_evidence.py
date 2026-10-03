"""Evidence and immutable-review protections, independent of model confidence."""

from copy import deepcopy
import re

from django.core.exceptions import ValidationError

from prescriptions.services.field_contract import ALIASES, fields


def _text(value):
    return re.sub(r"\s+", " ", str("" if value is None else value)).strip().casefold()


def _value_supported(reference):
    """Literal values or deterministic calendar normalization; confidence is irrelevant."""
    value = reference.get("extracted_value")
    quote = reference.get("source_text", "")
    path = reference["field_path"].split(".")
    collection = path[0] if len(path) >= 3 else "observation"
    key = ALIASES.get(collection, {}).get(path[-1], path[-1])
    definition = fields(collection).get(key, {})
    if definition.get("type") in {"date", "datetime-local"}:
        from types import SimpleNamespace
        from .text_analysis import find_dates
        candidates = find_dates([SimpleNamespace(page_number=reference["page"], cleaned_text=quote, raw_text=quote)])
        calendar = str(value)[:10]
        supported = any(item.get("normalized_date") == calendar and not item.get("warning") for item in candidates)
        if definition.get("type") == "datetime-local":
            supported = supported and len(str(value)) >= 16 and str(value)[11:16] in quote
        return supported
    values = value if isinstance(value, list) else [value]
    for item in values:
        literal = re.escape(_text(item))
        if not re.search(r"(?<![\w.])" + literal + r"(?![\w.])", _text(quote)):
            return False
        # A bare positive label inside an explicitly negated quote is not support.
        if re.search(r"\b(?:no|not|without)\s+" + literal + r"(?![\w.])", _text(quote)):
            return False
    return True


def validate_source_evidence(draft, pages):
    if pages is None:
        return draft
    by_page = {page.page_number: _text(page.cleaned_text or page.raw_text) for page in pages}
    for observation in draft["observations"]:
        for reference in observation["evidence_refs"]:
            if reference.get("extracted_value") in (None, "", []):
                continue
            quote = _text(reference["source_text"])
            if reference["page"] in by_page and quote and quote in by_page[reference["page"]] and _value_supported(reference):
                continue
            path = reference["field_path"].split(".")
            if len(path) < 3:
                for fact in draft.get("source_facts", []):
                    if fact.get("observation_temp_id") == observation["temp_id"] and fact.get("canonical_field") == path[-1]:
                        fact["disposition"] = "unresolved"
                        fact["reason"] = "Source page, quote or proposed value could not be verified independently."
                draft["unresolved_items"].append({"type": "unsupported_evidence", "reason": "Source page, quote or proposed value could not be verified independently.", "field_path": reference["field_path"], "observation_temp_id": observation["temp_id"]})
                continue
            collection, index, original_key = path[:3]
            records = observation.get(collection, [])
            try:
                record = records[int(index)]
            except (ValueError, IndexError):
                continue
            key = ALIASES.get(collection, {}).get(original_key, original_key)
            record["values"][key] = None
            record["state"] = "unresolved"
            resolution = record["resolutions"].get(key)
            if resolution:
                resolution["status"] = "unresolved"
                resolution["reason"] = "Verify the original evidence before selecting a canonical option."
                if "option_ids" in resolution:
                    resolution["option_ids"] = []
                else:
                    resolution["option_id"] = None
            for fact in record.get("fact_dispositions", []):
                if fact["canonical_field"] == key:
                    fact["disposition"] = "unresolved"
            for fact in draft.get("source_facts", []):
                if fact.get("record_temp_id") == record["temp_id"] and fact.get("canonical_field") == key:
                    fact["disposition"] = "unresolved"
                    fact["reason"] = "Source page, quote or proposed value could not be verified independently."
            draft["unresolved_items"].append({"type": "unsupported_evidence", "reason": "Source page, quote or proposed value could not be verified independently.", "field": key, "record_temp_id": record["temp_id"], "collection": collection})
    return draft


def immutable_review_projection(draft):
    return {
        record["temp_id"]: {key: deepcopy(record[key]) for key in ("extracted_values", "fact_dispositions") if key in record}
        for observation in draft.get("observations", [])
        for collection, records in observation.items()
        if isinstance(records, list) and collection != "evidence_refs"
        for record in records if isinstance(record, dict) and "temp_id" in record
    }


def verify_review_evidence(previous, current):
    if previous.get("source_facts") != current.get("source_facts"):
        raise ValidationError({"reviewed_data": "Original source fact accounting is read-only."})
    old = immutable_review_projection(previous)
    new = immutable_review_projection(current)
    for key in old.keys() & new.keys():
        if old[key] != new[key]:
            raise ValidationError({"reviewed_data": "Original extraction facts are read-only; change canonical values instead."})
    if any(new[key] for key in new.keys() - old.keys()):
        raise ValidationError({"reviewed_data": "New manual records cannot fabricate extraction provenance."})
    old_refs = {ref["evidence_id"]: ref for obs in previous.get("observations", []) for ref in obs.get("evidence_refs", [])}
    new_refs = {ref["evidence_id"]: ref for obs in current.get("observations", []) for ref in obs.get("evidence_refs", [])}
    if new_refs.keys() - old_refs.keys():
        raise ValidationError({"reviewed_data": "Source evidence must originate from an extraction run."})
    for key in old_refs.keys() & new_refs.keys():
        if old_refs[key] != new_refs[key]:
            raise ValidationError({"reviewed_data": "Original source evidence is read-only."})
