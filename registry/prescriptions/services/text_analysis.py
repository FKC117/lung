"""Deterministic, evidence-only text analysis for the prescription review queue."""
import re
from datetime import date

from django.conf import settings

from prescriptions.services.chronology import validate_chronology
from prescriptions.services.option_resolver import resolve_medications


MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
ISO_DATE = re.compile(r"(?<!\d)(?P<year>20\d{2})[-/.](?P<month>0?[1-9]|1[0-2])[-/.](?P<day>0?[1-9]|[12]\d|3[01])(?!\d)")
NUMERIC_DATE = re.compile(r"(?<!\d)(?P<first>0?[1-9]|[12]\d|3[01])[-/.](?P<second>0?[1-9]|[12]\d|3[01])[-/.](?P<year>20\d{2})(?!\d)")
NAMED_DATE = re.compile(
    r"(?<!\w)(?P<day>0?[1-9]|[12]\d|3[01])\s+(?P<month>Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?[,]?\s+(?P<year>20\d{2})(?!\d)",
    re.IGNORECASE,
)
IDENTIFIER = re.compile(
    r"\b(?P<label>registration|reg(?:istration)?\s*(?:no|number)?|patient\s*(?:id|no|number)?|mrn|uhid)\s*[:#-]?\s*(?P<value>[A-Z0-9][A-Z0-9/-]{2,})\b",
    re.IGNORECASE,
)
DOCTOR_LINE = re.compile(r"^\s*(?:consultant\s+)?dr\.?\s*(?P<name>[A-Za-z][A-Za-z .'-]{2,80})\s*$", re.IGNORECASE)
MEDICATION_LINE = re.compile(
    r"^\s*(?:(?P<form>tab(?:let)?|cap(?:sule)?|inj(?:ection)?|syp(?:rup)?|drop(?:s)?|neb(?:uliser)?)\.?\s+)?"
    r"(?P<drug>[A-Za-z][A-Za-z0-9()'/-]*(?:\s+[A-Za-z][A-Za-z0-9()'/-]*){0,4}?)\s+"
    r"(?P<strength>\d+(?:\.\d+)?\s*(?:mcg|mg|g|ml|iu|units?))\b(?P<instructions>.*)$",
    re.IGNORECASE,
)
FREQUENCY = re.compile(r"\b(?:od|bd|tds|qid|hs|sos|stat|once\s+(?:a\s+)?daily|twice\s+(?:a\s+)?daily|three\s+times\s+(?:a\s+)?daily|every\s+\d+\s*(?:h|hr|hours?))\b|\b\d\s*[+x]\s*\d\s*[+x]\s*\d(?:\s*[+x]\s*\d)?\b", re.IGNORECASE)


def evidence(page, text, start, end, value, confidence):
    return {
        "value": value,
        "source_text": text[max(0, start - 80):min(len(text), end + 80)].strip(),
        "page": page,
        "confidence": confidence,
    }


def iso_value(year, month, day):
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def find_dates(pages):
    candidates = []
    for page in pages:
        text = page.cleaned_text or page.raw_text
        consumed = set()
        for pattern, kind in ((ISO_DATE, "iso"), (NAMED_DATE, "named"), (NUMERIC_DATE, "numeric")):
            for match in pattern.finditer(text):
                span = set(range(match.start(), match.end()))
                if span & consumed:
                    continue
                consumed.update(span)
                groups = match.groupdict()
                if kind == "iso":
                    value = iso_value(int(groups["year"]), int(groups["month"]), int(groups["day"]))
                    confidence, issue = 0.99, None
                elif kind == "named":
                    value = iso_value(int(groups["year"]), MONTHS[groups["month"].lower().rstrip(".")], int(groups["day"]))
                    confidence, issue = 0.98, None
                else:
                    first, second, year = int(groups["first"]), int(groups["second"]), int(groups["year"])
                    order = settings.PRESCRIPTION_DATE_ORDER
                    if order == "DMY" or (not order and first > 12):
                        value, confidence, issue = iso_value(year, second, first), 0.95, None
                    elif order == "MDY" or (not order and second > 12):
                        value, confidence, issue = iso_value(year, first, second), 0.95, None
                    else:
                        value, confidence = None, 0.45
                        issue = "Ambiguous numeric date; confirm date order before using it in chronology."
                candidate = evidence(page.page_number, text, match.start(), match.end(), value or match.group(0), confidence)
                candidate["raw_value"] = match.group(0)
                candidate["normalized_date"] = value
                candidate["kind"] = kind
                if issue:
                    candidate["warning"] = issue
                elif not value:
                    candidate["warning"] = "Invalid calendar date."
                candidates.append(candidate)
    return candidates


def line_evidence(page, line, value, confidence):
    return {"value": value, "source_text": line.strip(), "page": page.page_number, "confidence": confidence}


def find_explicit_entities(pages):
    identifiers, doctors, medications = [], [], []
    for page in pages:
        text = page.cleaned_text or page.raw_text
        for match in IDENTIFIER.finditer(text):
            item = evidence(page.page_number, text, match.start("value"), match.end("value"), match.group("value"), 0.98)
            item["identifier_type"] = match.group("label").lower()
            identifiers.append(item)
        for line in text.splitlines():
            doctor = DOCTOR_LINE.match(line)
            if doctor:
                doctors.append(line_evidence(page, line, doctor.group("name").strip(), 0.90))
            medication = MEDICATION_LINE.match(line)
            if not medication:
                continue
            form = medication.group("form")
            instructions = medication.group("instructions").strip()
            frequency = FREQUENCY.search(instructions)
            item = {
                "drug": line_evidence(page, line, medication.group("drug").strip(), 0.90 if form else 0.65),
                "strength": line_evidence(page, line, medication.group("strength").strip(), 0.97),
                "form": line_evidence(page, line, form.lower(), 0.95) if form else None,
                "frequency": line_evidence(page, line, frequency.group(0), 0.93) if frequency else None,
                "instructions": line_evidence(page, line, instructions, 0.90) if instructions else None,
                "order_status": line_evidence(page, line, "prescribed", 0.99),
            }
            medications.append(item)
    return identifiers, doctors, medications


def analyze_text(pages):
    """Return explicit dates and their sortable order; no clinical meaning is inferred."""
    dates = find_dates(pages)
    identifiers, doctors, medications = find_explicit_entities(pages)
    resolve_medications(medications)
    resolved = sorted((item for item in dates if item["normalized_date"]), key=lambda item: (item["normalized_date"], item["page"]))
    warnings = [item["warning"] for item in dates if item.get("warning")]
    if resolved:
        warnings.append("Chronology orders explicit document dates only; it does not infer treatment, administration, diagnosis, progression, or event meaning.")
    result = {
        "patient": {"identifiers": identifiers},
        "observations": [],
        "prescriber_candidates": doctors,
        "medications": medications,
        "date_candidates": dates,
        "chronology": [{"sequence": index + 1, **item} for index, item in enumerate(resolved)],
        "unresolved_items": [],
        "warnings": warnings + (["Medication lines describe prescriptions only; they do not prove drug administration."] if medications else []),
    }
    return validate_chronology(result)
