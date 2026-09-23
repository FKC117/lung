"""Gemini Batch submission plumbing for historical prescription backfills.

This module never creates clinical records.  It sends page-wise OCR text and
stores provider correlation data; completed output still goes through review.
"""
import hashlib
import json
import tempfile

from django.conf import settings
from django.utils import timezone

from prescriptions.models import PrescriptionBatchItem, PrescriptionBatchJob, PrescriptionDocument
from prescriptions.services.extraction import SYSTEM_INSTRUCTION, build_contents, validate_extraction


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
        prompt_version=settings.PRESCRIPTION_EXTRACTION_PROMPT_VERSION,
        submitted_by=user,
    )
    try:
        rows = []
        items = []
        for document in documents:
            request = _request_for(document)
            serialized = json.dumps(request, separators=(",", ":"), ensure_ascii=False)
            rows.append(serialized)
            items.append(PrescriptionBatchItem(
                batch_job=job, document=document, request_key=request["key"],
                input_sha256=hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
            ))
        PrescriptionBatchItem.objects.bulk_create(items)
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
    except Exception as exc:
        job.status = PrescriptionBatchJob.Status.FAILED
        job.error = str(exc)
        job.save(update_fields=["status", "error", "updated_at"])
        raise
    return job


def _response_text(response):
    """Read a GenerateContentResponse from Gemini's JSONL batch output."""
    candidates = response.get("candidates", []) if isinstance(response, dict) else []
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))


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
        else:
            raw = _response_text(row.get("response", {}))
            item.raw_response = raw
            try:
                data = validate_extraction(json.loads(raw))
                run = item.document.extraction_runs.filter(status="completed").first()
                if run:
                    structured = dict(run.structured_data)
                    structured["gemini_extraction"] = data
                    structured.setdefault("warnings", []).extend(str(value) for value in data.get("warnings", []))
                    run.structured_data = structured
                    run.raw_response = raw
                    run.ai_model = job.model_name
                    run.prompt_version = job.prompt_version
                    run.save(update_fields=["structured_data", "raw_response", "ai_model", "prompt_version"])
                item.status = PrescriptionBatchItem.Status.COMPLETED
            except (ValueError, json.JSONDecodeError) as exc:
                item.status = PrescriptionBatchItem.Status.FAILED
                item.error = f"Invalid structured extraction: {exc}"
        item.completed_at = timezone.now()
        item.save(update_fields=["status", "raw_response", "error", "attempts", "completed_at"])
    job.status = PrescriptionBatchJob.Status.COMPLETED
    job.completed_at = timezone.now()
    job.save(update_fields=["status", "completed_at", "updated_at"])
    return job
