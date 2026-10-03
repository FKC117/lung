"""Safe, dependency-optional extraction for the prescription review queue."""
import re
import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from prescriptions.models import ExtractionIssue, ExtractionRun, PrescriptionDocument, PrescriptionPage
from prescriptions.services.extraction import GeminiRateLimitError, GeminiStructuredOutputError, GeminiPermanentProviderError, extract_structured_data
from prescriptions.services.intake_draft import build_intake_draft
from prescriptions.services.provider_data_policy import ProviderDataPolicyError
from prescriptions.services.text_analysis import analyze_text


def clean_text(value):
    return re.sub(r"[ \t]+", " ", value.replace("\x00", "")).strip()


def ocr_image(image_bytes):
    """Return raw OCR plus confidence; Tesseract language packs are host configuration."""
    try:
        import pytesseract
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise RuntimeError("Pillow and pytesseract are required for scanned-page OCR.") from exc
    from io import BytesIO

    if settings.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
    image = Image.open(BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image).convert("L")
    image = ImageOps.autocontrast(image)
    text = pytesseract.image_to_string(image, lang=settings.TESSERACT_LANGUAGES)
    data = pytesseract.image_to_data(
        image, lang=settings.TESSERACT_LANGUAGES, output_type=pytesseract.Output.DICT
    )
    confidences = [float(value) for value in data["conf"] if value not in {"", "-1"}]
    return text, (sum(confidences) / len(confidences) if confidences else None), {
        "method": "tesseract",
        "languages": settings.TESSERACT_LANGUAGES,
        "boxes": data,
    }


def extract_pages(document):
    """Extract embedded PDF text and fall back to OCR for scanned pages."""
    suffix = Path(document.file.name).suffix.lower()
    if suffix == ".pdf":
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise RuntimeError("PyMuPDF is required to extract PDF text.") from exc
        pages = []
        with fitz.open(document.file.path) as pdf:
            for index, page in enumerate(pdf):
                text = page.get_text("text")
                metadata = {"method": "pymupdf"}
                image_bytes = None
                confidence = None
                if len(clean_text(text)) < 20:
                    image_bytes = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).tobytes("png")
                    text, confidence, metadata = ocr_image(image_bytes)
                pages.append((index + 1, text, metadata, confidence, image_bytes))
        return pages
    if suffix in {".txt", ".csv"}:
        with document.file.open("rb") as source:
            return [(1, source.read().decode("utf-8", errors="replace"), {"method": "text"}, None, None)]
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        with document.file.open("rb") as source:
            image_bytes = source.read()
        text, confidence, metadata = ocr_image(image_bytes)
        return [(1, text, metadata, confidence, image_bytes)]
    raise RuntimeError("Only PDF, image, and plain-text uploads are supported.")


def page_artifact_version():
    configuration = {"extractor": "local-text-ocr-v1", "languages": settings.TESSERACT_LANGUAGES,
                     "tesseract_cmd": settings.TESSERACT_CMD}
    return hashlib.sha256(json.dumps(configuration, sort_keys=True).encode()).hexdigest()


def _valid_page_artifact(document, pages, version):
    return bool(pages) and [page.page_number for page in pages] == list(range(1, len(pages) + 1)) and all(
        page.ocr_metadata.get("artifact_document_sha256") == document.sha256 and
        page.ocr_metadata.get("artifact_extractor_version") == version for page in pages)


def ensure_page_artifact(document):
    """Reuse a complete, versioned local artifact; commit replacement atomically."""
    version = page_artifact_version()
    existing = list(document.pages.order_by("page_number"))
    if _valid_page_artifact(document, existing, version):
        return existing
    extracted = extract_pages(document)
    if not extracted or [item[0] for item in extracted] != list(range(1, len(extracted) + 1)):
        raise RuntimeError("Local extraction did not produce a complete ordered page artifact.")
    with transaction.atomic():
        locked = PrescriptionDocument.objects.select_for_update().get(pk=document.pk)
        if locked.sha256 != document.sha256:
            raise RuntimeError("Document identity changed during local extraction.")
        existing = list(locked.pages.order_by("page_number"))
        if _valid_page_artifact(locked, existing, version):
            return existing
        # Never destroy a prior artifact before its replacement is available.
        locked.pages.all().delete()
        stored = []
        for number, raw, metadata, confidence, image_bytes in extracted:
            page = PrescriptionPage(document=locked, page_number=number, raw_text=raw, cleaned_text=clean_text(raw),
                                    ocr_confidence=confidence, ocr_metadata={**metadata,
                                    "artifact_document_sha256": locked.sha256, "artifact_extractor_version": version})
            if image_bytes:
                page.image.save(f"{locked.pk}-page-{number}.png", ContentFile(image_bytes), save=False)
            page.save()
            stored.append(page)
        return stored


def process_document(document, *, retry_invalid_structured_output=False, quality_recovery=False):
    """Create immutable extraction output and review issues; never touch clinical records."""
    document.status = PrescriptionDocument.Status.PROCESSING
    document.processing_started_at = timezone.now()
    document.save(update_fields=["status", "processing_started_at"])
    run = ExtractionRun.objects.create(document=document, schema_version="1")
    try:
        stored_pages = ensure_page_artifact(document)
        result = analyze_text(stored_pages)
        result["source_page_artifact"] = {
            "document_sha256": document.sha256, "extractor_version": page_artifact_version(),
            "pages": [{"page_number": page.page_number, "page_id": page.pk,
                       "raw_text": page.raw_text, "cleaned_text": page.cleaned_text} for page in stored_pages],
        }
        result = enrich_extraction(run, stored_pages, result, retry_invalid_structured_output=retry_invalid_structured_output, quality_recovery=quality_recovery)
        result["canonical_draft"] = build_intake_draft(
            result,
            document_id=document.pk,
            linked_patient_id=document.patient_id,
            pages=list(stored_pages),
        )
        run.structured_data = result
        run.status = ExtractionRun.Status.COMPLETED
        run.completed_at = timezone.now()
        run.save(update_fields=["prompt_version", "ai_model", "raw_response", "structured_data", "status", "completed_at"])
        for warning in result["warnings"]:
            ExtractionIssue.objects.create(document=document, extraction_run=run, code="extraction_warning", severity=ExtractionIssue.Severity.WARNING, message=str(warning))
        for issue in result.get("validation", {}).get("issues", []):
            ExtractionIssue.objects.create(
                document=document,
                extraction_run=run,
                code=issue["code"],
                severity=issue["severity"],
                message=issue["message"],
                page_number=issue.get("page"),
            )
        document.page_count = len(stored_pages)
        document.status = PrescriptionDocument.Status.READY_FOR_REVIEW
        document.processed_at = timezone.now()
        document.save(update_fields=["page_count", "status", "processed_at"])
    except GeminiRateLimitError as exc:
        # Keep the document in processing while Celery schedules its next
        # quota-aware attempt.  Marking it failed here would let a user launch
        # another extraction while the scheduled retry is still pending.
        run.status = ExtractionRun.Status.FAILED
        run.error = str(exc)
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "error", "completed_at"])
        raise
    except GeminiStructuredOutputError as exc:
        # The task will make its short retry before retaining the deterministic
        # extraction.  Keep this document unavailable for manual re-queueing
        # while that retry is pending.
        run.status = ExtractionRun.Status.FAILED
        run.error = str(exc)
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "error", "completed_at"])
        raise
    except Exception as exc:
        run.status = ExtractionRun.Status.FAILED
        run.error = str(exc)
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "error", "completed_at"])
        document.status = PrescriptionDocument.Status.FAILED
        document.processed_at = timezone.now()
        document.save(update_fields=["status", "processed_at"])
        ExtractionIssue.objects.create(document=document, extraction_run=run, code="processing_failed", severity=ExtractionIssue.Severity.ERROR, message=str(exc))
    return run


def enrich_extraction(run, stored_pages, result, *, retry_invalid_structured_output=False, quality_recovery=False):
    # Deterministic evidence remains the baseline. Gemini enriches the
    # review-only payload and can never block OCR or create clinical data.
    try:
        gemini_data, raw_response, prompt_version, model_name = extract_structured_data(
            stored_pages,
            extraction_run=run,
            quality_recovery=quality_recovery,
        )
        result["gemini_extraction"] = gemini_data
        result["gemini_status"] = "available"
        if gemini_data.get("warnings"):
            result["warnings"].extend(str(warning) for warning in gemini_data["warnings"])
        run.raw_response = raw_response
        run.prompt_version = prompt_version
        run.ai_model = model_name
    except ProviderDataPolicyError as exc:
        reason = str(exc)
        result["gemini_extraction"] = {"unresolved_items": [{"type": "provider_data_policy", "reason": reason}]}
        result["gemini_status"] = "policy_blocked"
        result["gemini_error"] = reason
        result["warnings"].append(reason)
        run.prompt_version = "deterministic-text-v1"
    except GeminiRateLimitError:
        # Let Celery own delayed quota retries; local artifacts remain reusable.
        raise
    except GeminiStructuredOutputError as exc:
        if retry_invalid_structured_output:
            raise
        reason = str(exc)
        result["gemini_extraction"] = {"unresolved_items": [{"type": "structured_extraction", "reason": reason}]}
        result["gemini_status"] = "unavailable"
        result["gemini_error"] = f"{reason} Deterministic OCR evidence is available for review."
        result["warnings"].append(result["gemini_error"])
        run.prompt_version = "deterministic-text-v1"
    except GeminiPermanentProviderError as exc:
        result["gemini_extraction"] = {"unresolved_items": [{"type": "provider_" + exc.category, "reason": str(exc)}]}
        result["gemini_status"] = "unavailable"
        result["gemini_error"] = str(exc)
        result["warnings"].append("Provider unavailable; saved local evidence remains available.")
        run.prompt_version = "deterministic-text-v1"
    except Exception as exc:
        result["gemini_extraction"] = {"unresolved_items": [{"type": "structured_extraction", "reason": "Gemini enrichment failed; local evidence remains available."}]}
        result["gemini_status"] = "unavailable"
        result["gemini_error"] = "Gemini enrichment failed. Deterministic OCR evidence is available for review."
        result["warnings"].append("Gemini enrichment failed; deterministic extraction is available for review.")
        run.prompt_version = "deterministic-text-v1"
    return result
