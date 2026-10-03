"""Synthetic-only evaluation and read-only graph comparison; no persistence tools."""
from copy import deepcopy
from types import SimpleNamespace
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from .corpus import cases
from prescriptions.services.intake_draft import build_intake_draft
from prescriptions.services.draft_schema import normalize_extraction, COLLECTIONS
from prescriptions.services.draft_evidence import validate_source_evidence


class ShadowState(TypedDict, total=False):
    payload: dict
    pages: list
    draft: dict


def _normalize(state):
    return {"draft": normalize_extraction({"gemini_extraction": state["payload"]}, document_id=1)}


def _evidence(state):
    return {"draft": validate_source_evidence(state["draft"], state["pages"])}


def shadow_graph():
    graph = StateGraph(ShadowState)
    graph.add_node("normalize", _normalize)
    graph.add_node("evidence", _evidence)
    graph.add_edge(START, "normalize")
    graph.add_edge("normalize", "evidence")
    graph.add_edge("evidence", END)
    return graph.compile()


def _value(draft, path):
    collection, index, field = path.split(".")
    records = draft.get("observations", [{}])[0].get(collection, [])
    return records[int(index)].get("values", {}).get(field) if int(index) < len(records) else None


def comparison_projection(draft):
    """Canonicalize generated identities while preserving their reference relationships."""
    identities = {}
    def collect(value):
        if isinstance(value, dict):
            for key, entry in value.items():
                if key in {"temp_id", "evidence_id"} and isinstance(entry, str):
                    identities.setdefault(entry, f"identity-{len(identities)}")
                collect(entry)
        elif isinstance(value, list):
            for entry in value:
                collect(entry)
    collect(draft)
    def project(value):
        if isinstance(value, dict):
            return {key: project(entry) for key, entry in value.items()}
        if isinstance(value, list):
            return [project(entry) for entry in value]
        if isinstance(value, str):
            for identity, stable in identities.items():
                value = value.replace(identity, stable)
        return value
    return project(draft)


def evaluate_synthetic(*, shadow=False):
    results, metrics = [], {}
    graph = shadow_graph() if shadow else None
    for case in cases():
        if not all("SYNTHETIC FIXTURE ONLY" in page for page in case["pages"]):
            raise ValueError("Only committed synthetic fixtures may enter this runner.")
        pages = [SimpleNamespace(page_number=i+1, cleaned_text=text, raw_text=text) for i, text in enumerate(case["pages"])]
        original = deepcopy(case["payload"])
        draft = build_intake_draft({"gemini_extraction": deepcopy(original)}, document_id=1, resolve_options=False, pages=pages)
        fields = []
        for path, expected in case["expected"].items():
            actual = _value(draft, path)
            correct = actual == expected
            omitted = actual is None or actual == ""
            field = path.split(".")[0] + "." + path.split(".")[-1]
            aggregate = metrics.setdefault(field, {"expected": 0, "correct": 0, "omitted": 0, "incorrect": 0})
            aggregate["expected"] += 1
            aggregate["correct"] += int(correct)
            aggregate["omitted"] += int(not correct and omitted)
            aggregate["incorrect"] += int(not correct and not omitted)
            fields.append({"path": path, "correct": correct, "omitted": not correct and omitted})
        missing_exceptions = set(case["exceptions"]) - {issue["type"] for issue in draft["unresolved_items"]}
        facts = [fact for observation in draft["observations"] for name in COLLECTIONS for record in observation[name] for fact in record.get("fact_dispositions", [])]
        expected_facts = sum(len(record) for records in original["observations"][0].values() if isinstance(records, list) for record in records)
        absent_ok = all(_value(draft, path) in (None, "", []) for path in case.get("absent", []))
        parity = comparison_projection(graph.invoke({"payload": deepcopy(original), "pages": pages})["draft"]) == comparison_projection(draft) if graph else None
        unchanged = original == case["payload"]
        passed = all(field["correct"] for field in fields) and not missing_exceptions and len(facts) == expected_facts and absent_ok and unchanged and parity is not False
        results.append({"case": case["id"], "fields": fields, "accounted_facts": len(facts), "expected_facts": expected_facts, "missing_exception_types": sorted(missing_exceptions), "exception_count": len(draft["unresolved_items"]), "baseline_parity": parity, "passed": passed})
    for metric in metrics.values():
        metric["accuracy"] = metric["correct"] / metric["expected"]
    return {"synthetic_only": True, "mode": "shadow" if shadow else "mapping", "provider_calls": 0, "clinical_writes": 0, "field_metrics": metrics, "cases": results, "passed": all(case["passed"] for case in results),
            "unmeasured": ["provider extraction accuracy", "catalog auto-selection accuracy", "observed reviewer corrections and time", "production failure rate"],
            "limitations": "Hand-annotated engineering fixtures; shadow parity compares orchestration using shared services, not an independent clinical truth set. Production clinical thresholds remain owner gates."}
