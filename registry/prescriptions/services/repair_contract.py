"""Narrow repair proposals over verified source sections; no writes or provider calls."""
from copy import deepcopy
from hashlib import sha256
import json
import re
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from .field_contract import fields
from .draft_schema import _validate_date

REPAIRABLE_ISSUES = {"unsupported_evidence", "invalid_field_value", "conflicting_alias"}


def _text(value):
    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def _record(draft, collection, record_id):
    for observation in draft["observations"]:
        for record in observation.get(collection, []):
            if record["temp_id"] == record_id:
                return observation, record
    raise ValidationError({"repair": "Choose an existing clinical record."})


def prepare_repair_request(draft, *, collection, record_id, field_names, source_sections, pages, revision, document_sha256):
    definitions = fields(collection)
    if collection in {"patient", "observation", "anthropometry"} or not definitions:
        raise ValidationError({"repair": "Repair must target an existing supported clinical record section."})
    if not isinstance(field_names, list) or not field_names or any(not isinstance(key, str) for key in field_names) or len(set(field_names)) != len(field_names):
        raise ValidationError({"repair": "Choose distinct affected fields."})
    observation, record = _record(draft, collection, record_id)
    if record["state"] == "edited":
        raise ValidationError({"repair": "Reviewer-owned record values are protected."})
    affected = {issue.get("field") for issue in draft["unresolved_items"] if issue.get("record_temp_id") == record_id and issue.get("type") in REPAIRABLE_ISSUES}
    affected.update(item.get("canonical_field") for item in record.get("fact_dispositions", []) if item.get("disposition") == "unresolved")
    for key in field_names:
        definition = definitions.get(key)
        if not definition or definition.get("readOnly") or definition.get("persisted") is False or key not in affected:
            raise ValidationError({"repair": "Only supported affected fields may be proposed for repair."})
        if definition.get("type") == "boolean":
            raise ValidationError({"repair": "Boolean clinical interpretations require an explicit reviewer decision."})
    refs = [ref for ref in observation["evidence_refs"] if ref["evidence_id"] in record["evidence_refs"]]
    associated_pages = {ref["page"] for ref in refs if ref.get("page") is not None}
    page_text = {page.page_number: _text(page.cleaned_text or page.raw_text) for page in pages}
    if not isinstance(source_sections, list) or not 1 <= len(source_sections) <= 4:
        raise ValidationError({"repair": "Choose one to four bounded source sections."})
    for section in source_sections:
        if not isinstance(section, dict) or set(section) != {"page", "source_text"}:
            raise ValidationError({"repair": "Source sections require page and source_text only."})
        page, quote = section["page"], section["source_text"]
        if not isinstance(page, int) or isinstance(page, bool) or page not in associated_pages or not isinstance(quote, str) or not quote.strip() or len(quote) > 3000 or _text(quote) not in page_text.get(page, ""):
            raise ValidationError({"repair": "Each bounded section must be verified on a page associated with this record."})
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1 or not isinstance(document_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", document_sha256):
        raise ValidationError({"repair": "A saved revision and immutable source identity are required."})
    request = {"schema_version": "targeted-repair-1", "document_id": draft["document_id"], "collection": collection, "record_id": record_id,
               "fields": field_names, "source_sections": source_sections, "review_revision": revision, "document_sha256": document_sha256,
               "original_values": {key: deepcopy(record["values"].get(key)) for key in field_names}}
    request = deepcopy(request)
    request["request_sha256"] = sha256(json.dumps(request, sort_keys=True, default=str).encode()).hexdigest()
    return request


def validate_repair_proposal(request, payload, *, current_draft, current_revision, document_sha256):
    snapshot = {key: value for key, value in request.items() if key != "request_sha256"}
    if sha256(json.dumps(snapshot, sort_keys=True, default=str).encode()).hexdigest() != request.get("request_sha256"):
        raise ValidationError({"repair": "Repair request snapshot changed."})
    if current_revision != request["review_revision"] or document_sha256 != request["document_sha256"] or current_draft["document_id"] != request["document_id"]:
        raise ValidationError({"repair": "Document or saved review revision changed; discard this proposal."})
    _, record = _record(current_draft, request["collection"], request["record_id"])
    if record["state"] == "edited" or any(record["values"].get(key) != value for key, value in request["original_values"].items()):
        raise ValidationError({"repair": "Reviewer-owned values changed; discard this proposal."})
    if not isinstance(payload, dict) or set(payload) != {"patches"} or not isinstance(payload["patches"], dict) or not payload["patches"] or set(payload["patches"]) - set(request["fields"]):
        raise ValidationError({"repair": "Proposal may contain only allowlisted affected field patches."})
    definitions = fields(request["collection"])
    for key, evidence in payload["patches"].items():
        if not isinstance(evidence, dict) or set(evidence) != {"value", "page", "source_text"}:
            raise ValidationError({"repair": "Each patch requires value, page and source_text only."})
        value, page, quote = evidence["value"], evidence["page"], evidence["source_text"]
        if not isinstance(page, int) or isinstance(page, bool) or not isinstance(quote, str) or not quote.strip() or not any(section["page"] == page and _text(quote) in _text(section["source_text"]) for section in request["source_sections"]):
            raise ValidationError({"repair": "Repair evidence must come from the bounded submitted sections."})
        definition = definitions[key]
        kind = definition.get("type")
        if kind in {"date", "datetime-local"}:
            _validate_date(value, key, date_time=kind == "datetime-local")
        if kind == "number":
            try:
                valid = not isinstance(value, bool) and Decimal(str(value)).is_finite()
            except (ValueError, InvalidOperation):
                valid = False
            if not valid:
                raise ValidationError({"repair": "Repair numeric values must be finite."})
        elif not isinstance(value, str) or not value.strip():
            raise ValidationError({"repair": "Repair values must be populated text, never provider-selected IDs."})
        if definition.get("choices") and value not in {item["value"] for item in definition["choices"]}:
            raise ValidationError({"repair": "Choose a supported status."})
        # Conservative literal support: paraphrases/interpretations remain manual exceptions.
        if not re.search(r"(?<![\w.])" + re.escape(_text(value)) + r"(?![\w.])", _text(quote)):
            raise ValidationError({"repair": "The proposed value must be literally supported by its source quote."})
    return {"request_sha256": request["request_sha256"], "review_revision": request["review_revision"], "patches": deepcopy(payload["patches"])}
