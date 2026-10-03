"""Gemini Batch submission plumbing for historical prescription backfills.

This module never creates clinical records.  It sends page-wise OCR text and
stores provider correlation data; completed output still goes through review.
"""
import hashlib
import json
import tempfile
from copy import deepcopy

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from prescriptions.models import ExtractionRun, LLMInvocation, PrescriptionBatchItem, PrescriptionBatchJob, PrescriptionDocument
from prescriptions.services.extraction import SYSTEM_INSTRUCTION, build_contents, validate_extraction, validate_provider_completion
from prescriptions.services.field_contract import extraction_schema
from prescriptions.services.intake_draft import build_intake_draft
from prescriptions.services.provider_data_policy import require_approved_gemini_input
from prescriptions.services.provider_failures import audit_failure_category


def _request_for(document):
    pages = list(document.pages.order_by("page_number"))
    if not pages:
        raise ValueError(f"Document {document.pk} has no extracted pages.")
    input_text = build_contents(pages)
    require_approved_gemini_input(input_text)
    return {
        "key": f"prescription-{document.pk}-{document.sha256[:12]}",
        "request": {
            "contents": [{"role": "user", "parts": [{"text": input_text}]}],
            "config": {
                "system_instruction": SYSTEM_INSTRUCTION,
                "response_mime_type": "application/json",
                "temperature": 0,
                **({"max_output_tokens": settings.PRESCRIPTION_PROVIDER_MAX_OUTPUT_TOKENS} if settings.PRESCRIPTION_PROVIDER_BUDGET_ENABLED and settings.PRESCRIPTION_PROVIDER_MAX_OUTPUT_TOKENS > 0 else {}),
            },
        },
    }


def create_batch_job(*, document_ids, user, display_name):
    if not settings.GOOGLE_API_KEY or not settings.PRESCRIPTION_EXTRACTION_MODEL:
        raise ValueError("Configure GOOGLE_API_KEY and PRESCRIPTION_EXTRACTION_MODEL before creating a Gemini batch.")
    documents = list(
        PrescriptionDocument.objects.filter(
            id__in=document_ids, status=PrescriptionDocument.Status.READY_FOR_REVIEW
        ).prefetch_related("pages")
    )
    if len(documents) != len(set(document_ids)):
        raise ValueError("Every batch document must be ready for review with extracted pages.")
    # Reject the entire batch before creating jobs/audits or uploading any text.
    prepared_requests = {document.pk: _request_for(document) for document in documents}
    from prescriptions.services.provider_budget import reserve_provider_budget
    reserve_provider_budget([request["request"]["contents"][0]["parts"][0]["text"] for request in prepared_requests.values()], system_instruction=SYSTEM_INSTRUCTION)
    job = PrescriptionBatchJob.objects.create(
        display_name=display_name,
        model_name=settings.PRESCRIPTION_EXTRACTION_MODEL,
        schema_version="1",
        prompt_version=settings.PRESCRIPTION_EXTRACTION_PROMPT_VERSION,
        submitted_by=user,
    )
    try:
        rows = []
        request_inputs = {}
        items = []
        for document in documents:
            request = prepared_requests[document.pk]
            serialized = json.dumps(request, separators=(",", ":"), ensure_ascii=False)
            rows.append(serialized)
            request_inputs[document.pk] = request["request"]["contents"][0]["parts"][0]["text"]
            items.append(PrescriptionBatchItem(
                batch_job=job, document=document, request_key=request["key"],
                input_sha256=hashlib.sha256(request_inputs[document.pk].encode("utf-8")).hexdigest(),
            ))
        PrescriptionBatchItem.objects.bulk_create(items)
        batch_items = {
            item.document_id: item
            for item in PrescriptionBatchItem.objects.filter(batch_job=job)
        }
        LLMInvocation.objects.bulk_create([
            LLMInvocation(
                document=document,
                batch_item=batch_items[document.pk],
                provider="gemini",
                request_kind="batch_generate_content",
                model_name=settings.PRESCRIPTION_EXTRACTION_MODEL,
                prompt_version=settings.PRESCRIPTION_EXTRACTION_PROMPT_VERSION,
                system_instruction=SYSTEM_INSTRUCTION,
                input_text=request_inputs[document.pk],
                input_sha256=hashlib.sha256(request_inputs[document.pk].encode("utf-8")).hexdigest(),
                input_characters=len(request_inputs[document.pk]),
                status=LLMInvocation.Status.QUEUED,
            )
            for document in documents
        ])
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", encoding="utf-8", delete=True) as source:
            source.write("\n".join(rows))
            source.flush()
            uploaded = client.files.upload(file=source.name, config=types.UploadFileConfig(mime_type="application/jsonl"))
        provider_job = client.batches.create(
            model=settings.PRESCRIPTION_EXTRACTION_MODEL,
            src=uploaded.name,
            config={"display_name": display_name},
        )
        job.provider_job_name = provider_job.name or ""
        job.status = PrescriptionBatchJob.Status.SUBMITTED
        job.submitted_at = timezone.now()
        job.save(update_fields=["provider_job_name", "status", "submitted_at", "updated_at"])
        LLMInvocation.objects.filter(batch_item__batch_job=job).update(status=LLMInvocation.Status.RUNNING)
    except Exception as exc:
        job.status = PrescriptionBatchJob.Status.FAILED
        job.error = f"Gemini batch submission failed [{audit_failure_category(exc)}]."
        job.save(update_fields=["status", "error", "updated_at"])
        LLMInvocation.objects.filter(batch_item__batch_job=job).update(
            status=LLMInvocation.Status.FAILED,
            error=job.error,
            completed_at=timezone.now(),
        )
        raise RuntimeError(job.error) from None
    return job


def _response_text(response):
    """Read a GenerateContentResponse from Gemini's JSONL batch output."""
    candidates = response.get("candidates", []) if isinstance(response, dict) else []
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))


def _store_batch_invocation_result(item, response, *, output_text="", error="", succeeded=False):
    invocation = item.llm_invocations.order_by("-id").first()
    if not invocation:
        return
    usage = response.get("usageMetadata", response.get("usage_metadata", {})) if isinstance(response, dict) else {}
    usage = usage if isinstance(usage, dict) else {}
    input_tokens = usage.get("promptTokenCount", usage.get("prompt_token_count"))
    output_tokens = usage.get("candidatesTokenCount", usage.get("candidates_token_count"))
    total_tokens = usage.get("totalTokenCount", usage.get("total_token_count"))
    invocation.status = LLMInvocation.Status.SUCCEEDED if succeeded else LLMInvocation.Status.FAILED
    invocation.output_text = output_text
    invocation.output_sha256 = hashlib.sha256(output_text.encode("utf-8")).hexdigest() if output_text else ""
    invocation.output_characters = len(output_text)
    invocation.input_tokens = input_tokens if isinstance(input_tokens, int) else None
    invocation.output_tokens = output_tokens if isinstance(output_tokens, int) else None
    invocation.total_tokens = total_tokens if isinstance(total_tokens, int) else None
    invocation.usage_metadata = {key: value for key, value in usage.items() if isinstance(value, (str, int, float, bool, type(None)))}
    invocation.provider_request_id = str(response.get("responseId", response.get("response_id", ""))) if isinstance(response, dict) else ""
    invocation.error = str(error)[:10_000]
    invocation.completed_at = timezone.now()
    invocation.save(update_fields=[
        "status", "output_text", "output_sha256", "output_characters", "input_tokens", "output_tokens",
        "total_tokens", "usage_metadata", "provider_request_id", "error", "completed_at",
    ])


@transaction.atomic
def import_batch_row(job, item_id, row):
    """One atomic, replay-safe import; completed extraction evidence is immutable."""
    item = PrescriptionBatchItem.objects.select_for_update().select_related("document").get(pk=item_id, batch_job=job)
    if item.status in {PrescriptionBatchItem.Status.COMPLETED, PrescriptionBatchItem.Status.FAILED}:
        return item
    item.attempts += 1
    provider_response = row.get("response", {})
    if row.get("error"):
        item.status = PrescriptionBatchItem.Status.FAILED
        item.error = "Gemini batch item failed."
        _store_batch_invocation_result(item, provider_response, error=item.error)
    else:
        raw = _response_text(provider_response)
        item.raw_response = raw
        try:
            current_input = build_contents(list(item.document.pages.order_by("page_number")))
            source_digest = hashlib.sha256(current_input.encode()).hexdigest()
            invocation = item.llm_invocations.order_by("-id").first()
            # Older submissions hashed the full request envelope on the item.
            # Its immutable invocation still records the original source digest.
            expected_digest = invocation.input_sha256 if invocation else item.input_sha256
            if source_digest != expected_digest:
                raise ValueError("Batch input pages changed after submission; create a new batch.")
            validate_provider_completion(provider_response)
            data = validate_extraction(json.loads(raw))
            previous = item.document.extraction_runs.filter(status="completed").first()
            if not previous:
                raise ValueError("The batch source extraction is unavailable.")
            structured = deepcopy(previous.structured_data)
            structured.pop("canonical_draft", None)
            structured["gemini_extraction"] = data
            structured["gemini_status"] = "available"
            structured.setdefault("warnings", []).extend(str(value) for value in data.get("warnings", []))
            structured["batch_item_id"] = item.pk
            structured["source_extraction_run_id"] = previous.pk
            structured["canonical_draft"] = build_intake_draft(
                structured, document_id=item.document_id, linked_patient_id=item.document.patient_id,
                pages=list(item.document.pages.all()))
            ExtractionRun.objects.create(
                document=item.document, schema_version=previous.schema_version,
                structured_data=structured, raw_response=raw, ai_model=job.model_name,
                prompt_version=job.prompt_version, status=ExtractionRun.Status.COMPLETED,
                completed_at=timezone.now())
            item.status = PrescriptionBatchItem.Status.COMPLETED
            _store_batch_invocation_result(item, provider_response, output_text=raw, succeeded=True)
        except (ValueError, json.JSONDecodeError) as exc:
            item.status = PrescriptionBatchItem.Status.FAILED
            item.error = f"Invalid structured extraction [{audit_failure_category(exc)}]."
            _store_batch_invocation_result(item, provider_response, output_text=raw, error=item.error)
    item.completed_at = timezone.now()
    item.save(update_fields=["status", "raw_response", "error", "attempts", "completed_at"])
    return item


def sync_batch_job(job):
    """Import completed batch output into review-only extraction runs."""
    if not job.provider_job_name:
        raise ValueError("This batch has not been submitted to Gemini.")
    from google import genai

    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    provider_job = client.batches.get(name=job.provider_job_name)
    state = getattr(getattr(provider_job, "state", None), "name", str(getattr(provider_job, "state", "")))
    if state in {"JOB_STATE_QUEUED", "JOB_STATE_PENDING", "JOB_STATE_RUNNING"}:
        job.status = PrescriptionBatchJob.Status.RUNNING
        job.save(update_fields=["status", "updated_at"])
        return job
    if state != "JOB_STATE_SUCCEEDED":
        job.status = PrescriptionBatchJob.Status.CANCELLED if state == "JOB_STATE_CANCELLED" else PrescriptionBatchJob.Status.FAILED
        job.error = "Gemini batch did not succeed [provider_batch_failure]."
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error", "completed_at", "updated_at"])
        return job
    destination = getattr(provider_job, "dest", None)
    file_name = getattr(destination, "file_name", None)
    if not file_name:
        raise ValueError("Gemini returned no output file for this batch.")
    content = client.files.download(file=file_name)
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    items = {item.request_key: item for item in job.items.select_related("document")}
    for line in str(content).splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        item = items.get(row.get("key"))
        if not item:
            continue
        import_batch_row(job, item.pk, row)
    for missing in job.items.filter(status=PrescriptionBatchItem.Status.QUEUED):
        import_batch_row(job, missing.pk, {"error": "Provider output omitted this item."})
    failed = job.items.filter(status=PrescriptionBatchItem.Status.FAILED).exists()
    job.status = PrescriptionBatchJob.Status.FAILED if failed else PrescriptionBatchJob.Status.COMPLETED
    job.error = "One or more batch items failed; inspect item errors." if failed else ""
    job.completed_at = timezone.now()
    job.save(update_fields=["status", "error", "completed_at", "updated_at"])
    return job
