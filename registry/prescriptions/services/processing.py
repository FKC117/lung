"""Safe, dependency-optional extraction for the prescription review queue."""
import re
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from prescriptions.models import ExtractionIssue, ExtractionRun, PrescriptionDocument, PrescriptionPage
from prescriptions.services.extraction import extract_structured_data
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


def process_document(document):
    """Create immutable extraction output and review issues; never touch clinical records."""
    document.status = PrescriptionDocument.Status.PROCESSING
    document.processing_started_at = timezone.now()
    document.save(update_fields=["status", "processing_started_at"])
    run = ExtractionRun.objects.create(document=document)
    try:
        pages = extract_pages(document)
        PrescriptionPage.objects.filter(document=document).delete()
        for number, raw, metadata, confidence, image_bytes in pages:
            page = PrescriptionPage(document=document, page_number=number, raw_text=raw, cleaned_text=clean_text(raw), ocr_confidence=confidence, ocr_metadata=metadata)
            if image_bytes:
                page.image.save(f"{document.pk}-page-{number}.png", ContentFile(image_bytes), save=False)
            page.save()
        stored_pages = PrescriptionPage.objects.filter(document=document).order_by("page_number")
        result = analyze_text(stored_pages)
        # Deterministic evidence remains the baseline. Gemini enriches the
        # review-only payload and can never block OCR or create clinical data.
        try:
            gemini_data, raw_response, prompt_version, model_name = extract_structured_data(stored_pages)
            result["gemini_extraction"] = gemini_data
            if gemini_data.get("warnings"):
                result["warnings"].extend(str(warning) for warning in gemini_data["warnings"])
            run.raw_response = raw_response
            run.prompt_version = prompt_version
            run.ai_model = model_name
        except Exception as exc:
            result["gemini_extraction"] = {"unresolved_items": [{"type": "structured_extraction", "reason": str(exc)}]}
            result["warnings"].append("Gemini enrichment failed; deterministic extraction is available for review.")
            run.prompt_version = "deterministic-text-v1"
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
        document.page_count = len(pages)
        document.status = PrescriptionDocument.Status.READY_FOR_REVIEW
        document.processed_at = timezone.now()
        document.save(update_fields=["page_count", "status", "processed_at"])
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
