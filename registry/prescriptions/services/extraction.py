"""LLM extraction with a deliberately narrow, review-only output contract."""
import json

from django.conf import settings


SCHEMA_VERSION = "1.0"

SYSTEM_INSTRUCTION = """You extract facts from oncology prescriptions for a human review queue.
Return JSON only. Never diagnose from medicine names, infer negative results, infer a death,
infer progression from a treatment change, infer administration from a prescription, or invent
an exact date. Unknown or ambiguous facts belong in unresolved_items or warnings.

The JSON object must have exactly these top-level keys: patient, observations,
unresolved_items, warnings. Every extracted clinical value must be an object with value,
source_text, page, and confidence (0 to 1). observations is a list because a document may
describe historical, current, and planned events. Each observation must include event_type,
temporal_context (historical/current/planned/uncertain), and evidence. Use page numbers supplied
in the source. Preserve wording faithfully; do not return database IDs or prose outside JSON."""


def empty_extraction():
    return {"patient": {}, "observations": [], "unresolved_items": [], "warnings": []}


def build_contents(pages):
    parts = []
    for page in pages:
        parts.append(f"--- PAGE {page.page_number} ---\n{page.cleaned_text or page.raw_text}")
    return "\n\n".join(parts)


def validate_extraction(data):
    if not isinstance(data, dict):
        raise ValueError("The extractor did not return a JSON object.")
    expected = {"patient", "observations", "unresolved_items", "warnings"}
    missing = expected - set(data)
    if missing:
        raise ValueError(f"The extractor response is missing required keys: {', '.join(sorted(missing))}.")
    if not isinstance(data["patient"], dict) or not isinstance(data["observations"], list):
        raise ValueError("The extractor response has invalid patient or observations sections.")
    if not isinstance(data["unresolved_items"], list) or not isinstance(data["warnings"], list):
        raise ValueError("The extractor response has invalid warnings sections.")
    return {key: data[key] for key in ("patient", "observations", "unresolved_items", "warnings")}


def extract_structured_data(pages):
    """Call Gemini and return both immutable raw output and validated review data."""
    if not settings.GOOGLE_API_KEY or not settings.PRESCRIPTION_EXTRACTION_MODEL:
        data = empty_extraction()
        missing = []
        if not settings.GOOGLE_API_KEY:
            missing.append("GOOGLE_API_KEY")
        if not settings.PRESCRIPTION_EXTRACTION_MODEL:
            missing.append("PRESCRIPTION_EXTRACTION_MODEL")
        data["unresolved_items"].append({"type": "structured_extraction", "reason": f"Missing configuration: {', '.join(missing)}."})
        data["warnings"].append("Structured extraction is unavailable until its provider and model are configured.")
        return data, "", "unconfigured", ""

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    response = client.models.generate_content(
        model=settings.PRESCRIPTION_EXTRACTION_MODEL,
        contents=build_contents(pages),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            temperature=0,
        ),
    )
    raw_response = response.text or ""
    if not raw_response:
        raise ValueError("The extractor returned an empty response.")
    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError("The extractor returned invalid JSON.") from exc
    return validate_extraction(data), raw_response, settings.PRESCRIPTION_EXTRACTION_PROMPT_VERSION, settings.PRESCRIPTION_EXTRACTION_MODEL
