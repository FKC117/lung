"""Gemini Batch submission plumbing for historical prescription backfills.

This module never creates clinical records.  It sends page-wise OCR text and
stores provider correlation data; completed output still goes through review.
"""
import hashlib
import json
import tempfile

from django.conf import settings
from django.utils import timezone

from prescriptions.models import LLMInvocation, PrescriptionBatchItem, PrescriptionBatchJob, PrescriptionDocument
from prescriptions.services.extraction import SYSTEM_INSTRUCTION, build_contents, validate_extraction
from prescriptions.services.intake_draft import build_intake_draft


def _request_for(document):
    pages = list(document.pages.order_by("page_number"))
    if not pages:
        raise ValueError(f"Document {document.pk} has no extracted pages.")
    return {
        "key": f"prescription-{document.pk}-{document.sha256[:12]}",
        "request": {
            "contents": [{"role": "user", "parts": [{"text": build_contents(pages)}]}],
            "config": {
                "system_instruction": SYSTEM_INSTRUCTION,
                "response_mime_type": "application/json",
                "temperature": 0,
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
            request = _request_for(document)
            serialized = json.dumps(request, separators=(",", ":"), ensure_ascii=False)
            rows.append(serialized)
            request_inputs[document.pk] = request["request"]["contents"][0]["parts"][0]["text"]
            items.append(PrescriptionBatchItem(
                batch_job=job, document=document, request_key=request["key"],
                input_sha256=hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
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
        job.error = str(exc)
        job.save(update_fields=["status", "error", "updated_at"])
        LLMInvocation.objects.filter(batch_item__batch_job=job).update(
            status=LLMInvocation.Status.FAILED,
            error="Gemini batch submission failed; see Celery log for traceback.",
            completed_at=timezone.now(),
        )
        raise
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
        job.error = str(getattr(provider_job, "error", "Gemini batch did not succeed."))
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
        item.attempts += 1
        if row.get("error"):
            item.status = PrescriptionBatchItem.Status.FAILED
            item.error = json.dumps(row["error"])
            _store_batch_invocation_result(item, row.get("response", {}), error="Gemini batch item failed.")
        else:
            provider_response = row.get("response", {})
            raw = _response_text(provider_response)
            item.raw_response = raw
            try:
                data = validate_extraction(json.loads(raw))
                run = item.document.extraction_runs.filter(status="completed").first()
                if run:
                    structured = dict(run.structured_data)
                    structured["gemini_extraction"] = data
                    structured.setdefault("warnings", []).extend(str(value) for value in data.get("warnings", []))
                    structured["canonical_draft"] = build_intake_draft(
                        structured,
                        document_id=item.document_id,
                        linked_patient_id=item.document.patient_id,
                    )
                    run.structured_data = structured
                    run.raw_response = raw
                    run.ai_model = job.model_name
                    run.prompt_version = job.prompt_version
                    run.save(update_fields=["structured_data", "raw_response", "ai_model", "prompt_version"])
                item.status = PrescriptionBatchItem.Status.COMPLETED
                _store_batch_invocation_result(item, provider_response, output_text=raw, succeeded=True)
            except (ValueError, json.JSONDecodeError) as exc:
                item.status = PrescriptionBatchItem.Status.FAILED
                item.error = f"Invalid structured extraction: {exc}"
                _store_batch_invocation_result(item, provider_response, output_text=raw, error=item.error)
        item.completed_at = timezone.now()
        item.save(update_fields=["status", "raw_response", "error", "attempts", "completed_at"])
    job.status = PrescriptionBatchJob.Status.COMPLETED
    job.completed_at = timezone.now()
    job.save(update_fields=["status", "completed_at", "updated_at"])
    return job
