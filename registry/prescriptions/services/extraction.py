"""LLM extraction with a deliberately narrow, review-only output contract."""
import json
import logging
import re
from hashlib import sha256

from django.conf import settings
from django.utils import timezone

from prescriptions.models import LLMInvocation


logger = logging.getLogger("celery.tasks")


SCHEMA_VERSION = "1"

PATIENT_FIELDS = {"name", "age", "gender", "patient_identifier", "registration_no", "phone"}
CLINICAL_SOURCE_SIGNAL = re.compile(
    r"\b(diagnosis|carcinoma|adenocarcinoma|small cell|histopathology|chemotherapy|radiotherapy|metasta(?:sis|tic)|treatment)\b",
    re.IGNORECASE,
)


class GeminiRateLimitError(RuntimeError):
    """A provider quota response that must be retried by the Celery task."""

    def __init__(self, *, retry_after_seconds=None):
        super().__init__("Gemini quota is temporarily exhausted.")
        self.retry_after_seconds = retry_after_seconds


class GeminiStructuredOutputError(ValueError):
    """The provider answered, but did not honour the structured-output contract."""


def gemini_retry_after_seconds(error):
    """Read a Retry-After header when the provider SDK exposes one."""
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    value = headers.get("retry-after") or headers.get("Retry-After")
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return None
    return seconds if seconds > 0 else None


def is_gemini_rate_limit(error):
    """Handle the stable HTTP code and SDK variations without SDK internals."""
    codes = (
        getattr(error, "code", None),
        getattr(error, "status_code", None),
        getattr(getattr(error, "response", None), "status_code", None),
    )
    return 429 in codes or "RESOURCE_EXHAUSTED" in str(error).upper()

SYSTEM_INSTRUCTION = """You extract facts from oncology prescriptions for a human review queue.
Return JSON only. Never diagnose from medicine names, infer negative results, infer a death,
infer progression from a treatment change, infer administration from a prescription, or invent
an exact date. Unknown or ambiguous facts belong in unresolved_items or warnings.

The JSON object must have exactly these top-level keys: patient, observations,
unresolved_items, warnings. Every extracted clinical value must be an object with value,
source_text, page, and confidence (0 to 1). observations is a list because a document may
describe historical, current, and planned events. Keep distinct events in distinct observation
objects. Each observation must include temporal_context (historical/current/planned/unknown)
and may contain these record arrays: comorbidities, diagnoses, histopathologies, ihc_results,
pathological_staging_results, clinical_tnm_stagings, pathological_tnm_stagings, molecular_tests,
cancer_markers, treatments, surgeries, radiotherapies, recist_assessments, irecist_assessments,
pathological_responses, progression_records, and survival_records. Use page numbers supplied in
the source. Preserve wording faithfully. Never return option_id, database_id, or pk fields, and
never return prose outside JSON.

patient is an object, never one evidence value. Its only permitted keys are name, age,
gender, patient_identifier, registration_no, and phone. Each populated patient key must use
the same value/source_text/page/confidence evidence object. Leave a patient key absent when
the document does not support it.

For every diagnoses record, preserve the source wording in diagnosis_in_details. You may also
provide disease_group as an ICD-10 category-code candidate (for example C34) when the wording
supports that category. Provide disease_subgroup only as a more-specific ICD-10 code candidate
(for example C34.11) when the source explicitly supports the required primary site and
laterality. Do not infer a lobe, laterality, malignant status, or code specificity not stated
in the source. These are evidence-backed suggestions for a human reviewer, never database IDs.

Patient identifiers are safety-critical. Only identify a patient number when its label
explicitly belongs to the patient (for example HN, HN ID, MRN, UHID, Patient ID, or Hospital
Number). A doctor's BMDC registration, medical-council registration, licence, or any number
next to Dr/Doctor/Consultant is never a patient identifier. If both HN and a clinician's
registration number occur, extract the HN only; do not put the clinician number in patient.
If the label is unclear, leave the patient identifier absent and add an unresolved item.

When the source contains a diagnosis, pathology, treatment, radiotherapy, or metastasis,
observations must include the supported clinical records. Do not return a demographics-only
response for a clinical prescription; if a clinical fact cannot be extracted, describe why in
unresolved_items."""

QUALITY_RECOVERY_INSTRUCTION = """
This is a recovery extraction because the previous result was invalid or omitted
the clinical timeline. Re-read every source page. Do not return demographics
alone when the document contains clinical facts. Extract every explicitly
supported diagnosis, pathology, molecular/IHC result, cancer marker, treatment,
radiotherapy, surgery, progression, or response into observations. Preserve
uncertain facts in unresolved_items. Return only the required JSON object.
"""


def empty_extraction():
    return {"patient": {}, "observations": [], "unresolved_items": [], "warnings": []}


def build_contents(pages):
    parts = []
    for page in pages:
        parts.append(f"--- PAGE {page.page_number} ---\n{page.cleaned_text or page.raw_text}")
    return "\n\n".join(parts)


def has_clinical_observation(data):
    """A clinical prescription must not be accepted as demographics-only JSON."""
    return any(
        any(key != "temporal_context" and bool(value) for key, value in observation.items())
        for observation in data.get("observations", [])
        if isinstance(observation, dict)
    )


def source_has_clinical_signal(pages):
    return any(CLINICAL_SOURCE_SIGNAL.search(page.cleaned_text or page.raw_text or "") for page in pages)


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

    patient = data["patient"]
    unknown_patient_fields = set(patient) - PATIENT_FIELDS
    if unknown_patient_fields:
        raise ValueError(f"The extractor response has unsupported patient fields: {', '.join(sorted(unknown_patient_fields))}.")
    for field, evidence in patient.items():
        if not isinstance(evidence, dict) or not {"value", "source_text", "page", "confidence"} <= set(evidence):
            raise ValueError(f"The extractor patient field '{field}' must include value, source_text, page, and confidence.")
        if not isinstance(evidence["page"], int) or evidence["page"] < 1:
            raise ValueError(f"The extractor patient field '{field}' has an invalid page.")
        if not isinstance(evidence["confidence"], (int, float)) or not 0 <= evidence["confidence"] <= 1:
            raise ValueError(f"The extractor patient field '{field}' has an invalid confidence.")
    for observation in data["observations"]:
        if not isinstance(observation, dict):
            raise ValueError("Every extractor observation must be an object.")
        temporal_context = observation.get("temporal_context", "unknown")
        if temporal_context not in {"historical", "current", "planned", "unknown"}:
            raise ValueError("An extractor observation has an invalid temporal context.")

    def reject_database_ids(value):
        if isinstance(value, dict):
            forbidden = {"option_id", "database_id", "pk"} & set(value)
            if forbidden:
                raise ValueError("The extractor response attempted to provide database IDs.")
            for item in value.values():
                reject_database_ids(item)
        elif isinstance(value, list):
            for item in value:
                reject_database_ids(item)

    reject_database_ids(data)
    return {key: data[key] for key in ("patient", "observations", "unresolved_items", "warnings")}


def _text_hash(value):
    return sha256(value.encode("utf-8")).hexdigest()


def _usage_details(response):
    """Extract stable Gemini usage fields without persisting opaque SDK objects."""
    usage = getattr(response, "usage_metadata", None)
    if not usage:
        return {}, None, None, None
    values = {}
    for source, target in (
        ("prompt_token_count", "input_tokens"),
        ("candidates_token_count", "output_tokens"),
        ("total_token_count", "total_tokens"),
    ):
        value = getattr(usage, source, None)
        if isinstance(value, int):
            values[target] = value
    return values, values.get("input_tokens"), values.get("output_tokens"), values.get("total_tokens")


def _finish_invocation(invocation, *, status, output_text="", error="", response=None):
    if not invocation:
        return
    usage_metadata, input_tokens, output_tokens, total_tokens = _usage_details(response) if response else ({}, None, None, None)
    invocation.status = status
    invocation.output_text = output_text
    invocation.output_sha256 = _text_hash(output_text) if output_text else ""
    invocation.output_characters = len(output_text)
    invocation.input_tokens = input_tokens
    invocation.output_tokens = output_tokens
    invocation.total_tokens = total_tokens
    invocation.usage_metadata = usage_metadata
    invocation.provider_request_id = str(getattr(response, "response_id", "") or "") if response else ""
    invocation.error = str(error)[:10_000]
    invocation.completed_at = timezone.now()
    invocation.save(update_fields=[
        "status", "output_text", "output_sha256", "output_characters", "input_tokens", "output_tokens",
        "total_tokens", "usage_metadata", "provider_request_id", "error", "completed_at",
    ])


def extract_structured_data(pages, *, extraction_run=None, quality_recovery=False):
    """Call Gemini and return both immutable raw output and validated review data."""
    page_list = list(pages)
    document_id = getattr(page_list[0], "document_id", None) if page_list else getattr(extraction_run, "document_id", None)
    contents = build_contents(page_list)
    system_instruction = SYSTEM_INSTRUCTION + (QUALITY_RECOVERY_INSTRUCTION if quality_recovery else "")
    prompt_version = settings.PRESCRIPTION_EXTRACTION_PROMPT_VERSION + ("-quality-recovery" if quality_recovery else "")
    invocation = None
    if extraction_run:
        invocation = LLMInvocation.objects.create(
            document_id=document_id,
            extraction_run=extraction_run,
            provider="gemini",
            request_kind="generate_content",
            model_name=settings.PRESCRIPTION_EXTRACTION_MODEL,
            prompt_version=prompt_version,
            system_instruction=system_instruction,
            input_text=contents,
            input_sha256=_text_hash(contents),
            input_characters=len(contents),
            status=LLMInvocation.Status.RUNNING,
        )
    if not settings.GOOGLE_API_KEY or not settings.PRESCRIPTION_EXTRACTION_MODEL:
        data = empty_extraction()
        missing = []
        if not settings.GOOGLE_API_KEY:
            missing.append("GOOGLE_API_KEY")
        if not settings.PRESCRIPTION_EXTRACTION_MODEL:
            missing.append("PRESCRIPTION_EXTRACTION_MODEL")
        data["unresolved_items"].append({"type": "structured_extraction", "reason": f"Missing configuration: {', '.join(missing)}."})
        data["warnings"].append("Structured extraction is unavailable until its provider and model are configured.")
        _finish_invocation(invocation, status=LLMInvocation.Status.SKIPPED, error=f"Missing configuration: {', '.join(missing)}.")
        return data, "", "unconfigured", ""

    logger.info(
        "Gemini extraction request started document_id=%s pages=%s model=%s input_characters=%s",
        document_id,
        len(page_list),
        settings.PRESCRIPTION_EXTRACTION_MODEL,
        len(contents),
    )

    from google import genai
    from google.genai import types

    try:
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        response = client.models.generate_content(
            model=settings.PRESCRIPTION_EXTRACTION_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                temperature=0,
            ),
        )
    except Exception as exc:
        # Do not log prompt content, response content, credentials, or patient
        # data.  The exception trace and identifiers are enough to diagnose a
        # provider outage or configuration problem.
        logger.exception(
            "Gemini extraction request failed document_id=%s pages=%s model=%s",
            document_id,
            len(page_list),
            settings.PRESCRIPTION_EXTRACTION_MODEL,
        )
        _finish_invocation(invocation, status=LLMInvocation.Status.FAILED, error="Gemini provider request failed; see Celery log for traceback.")
        if is_gemini_rate_limit(exc):
            raise GeminiRateLimitError(retry_after_seconds=gemini_retry_after_seconds(exc)) from exc
        raise
    raw_response = response.text or ""
    if not raw_response:
        logger.error(
            "Gemini extraction returned an empty response document_id=%s pages=%s model=%s",
            document_id,
            len(page_list),
            settings.PRESCRIPTION_EXTRACTION_MODEL,
        )
        _finish_invocation(invocation, status=LLMInvocation.Status.FAILED, response=response, error="Gemini returned an empty response.")
        raise GeminiStructuredOutputError("Gemini returned an empty structured response.")
    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        logger.exception(
            "Gemini extraction returned invalid JSON document_id=%s pages=%s model=%s response_characters=%s",
            document_id,
            len(page_list),
            settings.PRESCRIPTION_EXTRACTION_MODEL,
            len(raw_response),
        )
        _finish_invocation(invocation, status=LLMInvocation.Status.FAILED, output_text=raw_response, response=response, error="Gemini returned invalid JSON.")
        raise GeminiStructuredOutputError("Gemini returned invalid structured JSON.") from exc
    try:
        validated = validate_extraction(data)
    except Exception as exc:
        _finish_invocation(invocation, status=LLMInvocation.Status.FAILED, output_text=raw_response, response=response, error=str(exc))
        raise GeminiStructuredOutputError("Gemini returned JSON that did not match the extraction contract.") from exc
    if source_has_clinical_signal(page_list) and not has_clinical_observation(validated):
        _finish_invocation(
            invocation,
            status=LLMInvocation.Status.FAILED,
            output_text=raw_response,
            response=response,
            error="Gemini returned no clinical observations for a clinical prescription.",
        )
        raise GeminiStructuredOutputError("Gemini returned no clinical observations for a clinical prescription.")
    _finish_invocation(invocation, status=LLMInvocation.Status.SUCCEEDED, output_text=raw_response, response=response)
    logger.info(
        "Gemini extraction request completed document_id=%s pages=%s model=%s response_characters=%s observations=%s",
        document_id,
        len(page_list),
        settings.PRESCRIPTION_EXTRACTION_MODEL,
        len(raw_response),
        len(validated["observations"]),
    )
    return validated, raw_response, prompt_version, settings.PRESCRIPTION_EXTRACTION_MODEL
