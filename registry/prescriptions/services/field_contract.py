"""Shared form/extraction field vocabulary; the JSON is consumed by React too."""

from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path


@lru_cache(maxsize=1)
def contract():
    return json.loads((Path(__file__).resolve().parents[1] / "contracts" / "fields.json").read_text(encoding="utf-8"))


def fields(collection):
    section = contract()["collections"].get(collection) or contract().get(collection)
    return {field["key"]: field for field in section["fields"]} if section else {}


ALIASES = {
    "diagnoses": {"value": "diagnosis_in_details"},
    "patient": {"gender": "sex", "patient_identifier": "registration_no"},
    "histopathologies": {"histopathology": "report_summary", "finding": "report_summary", "histology_term": "histopathology_type", "specimen_site": "histopathology_site"},
    "ihc_results": {"reported_result": "result", "cycle": "marker"},
    "pathological_staging_results": {"cycle": "feature", "tested_at": "assessed_at"},
    "cancer_markers": {"marker_name": "marker"},
    "molecular_tests": {"reported_result": "result"},
}


DEPENDENCIES = contract()["dependencies"]


def option_fields():
    result = {name: {key: field["resource"] for key, field in fields(name).items() if field.get("resource")} for name in contract()["collections"]}
    # Backward-compatible validator vocabulary; normalization uses canonical keys.
    for name, aliases in ALIASES.items():
        for alias, canonical in aliases.items():
            if name in result and canonical in result[name]:
                result[name][alias] = result[name][canonical]
    return result


def _evidence_schema(field):
    if field.get("resource") or field.get("type") not in {"number", "boolean"}:
        value = {"type": ["string", "null"]}
    else:
        value = {"type": ["number" if field["type"] == "number" else "boolean", "null"]}
    if field.get("multiple"):
        value = {"type": ["array", "null"], "items": {"type": "string"}}
    if field.get("choices"):
        value = {"type": ["string", "null"], "enum": [choice["value"] for choice in field["choices"]] + [None]}
    return {"type": "object", "properties": {"value": value, "source_text": {"type": "string"}, "page": {"type": "integer", "minimum": 1}, "confidence": {"type": "number", "minimum": 0, "maximum": 1}}, "required": ["value", "source_text", "page", "confidence"], "additionalProperties": False}


def extraction_schema():
    observation = {key: _evidence_schema(field) for key, field in fields("observation").items()}
    observation["temporal_context"] = {"type": "string", "enum": ["historical", "current", "planned", "unknown"]}
    observation["anthropometry"] = {"type": "object", "properties": {key: _evidence_schema(field) for key, field in fields("anthropometry").items() if not field.get("readOnly")}, "additionalProperties": False}
    for name in contract()["collections"]:
        observation[name] = {"type": "array", "items": {"type": "object", "properties": {key: _evidence_schema(field) for key, field in fields(name).items() if not field.get("readOnly")}, "additionalProperties": False}}
    return {"type": "object", "properties": {
        "patient": {"type": "object", "properties": {key: _evidence_schema(field) for key, field in fields("patient").items()}, "additionalProperties": False},
        "observations": {"type": "array", "items": {"type": "object", "properties": observation, "required": ["temporal_context"], "additionalProperties": False}},
        "warnings": {"type": "array", "items": {"type": "string"}},
        "unresolved_items": {"type": "array", "items": {"type": "object", "properties": {"type": {"type": "string"}, "reason": {"type": "string"}}, "required": ["type", "reason"], "additionalProperties": False}},
    }, "required": ["patient", "observations", "warnings", "unresolved_items"], "additionalProperties": False}


def normalize_aliases(collection, values):
    result = deepcopy(values)
    conflicts = []
    for alias, target in ALIASES.get(collection, {}).items():
        if alias not in result:
            continue
        value = result.pop(alias)
        if result.get(target) not in (None, "", []) and result[target] != value:
            conflicts.append({"code": "conflicting_alias", "field": target, "alias": alias, "raw_value": value, "reason": "Conflicting extracted field names require review."})
        elif value not in (None, "", []):
            result[target] = value
    return result, conflicts
