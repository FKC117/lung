"""Deterministic, evidence-only text analysis for the prescription review queue."""
import re
from datetime import date

from django.conf import settings

from prescriptions.services.chronology import validate_chronology
from prescriptions.services.diagnosis import extract_diagnosis_and_staging
from prescriptions.services.field_tracking import track_fields
from prescriptions.services.histopathology import extract_histopathology
from prescriptions.services.molecular import extract_molecular_and_ihc
from prescriptions.services.option_resolver import resolve_medications
from prescriptions.services.patient_resolver import find_patient_candidates
from prescriptions.services.treatment_outcomes import extract_treatment_and_outcomes
from prescriptions.services.procedures import extract_procedure_evidence
from prescriptions.services.form_fields import extract_form_fields


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
    r"\b(?P<label>h\.?\s*n\.?|registration|reg(?:istration)?\s*(?:no|number)?|patient\s*(?:id|no|number)?|mrn|uhid)(?:\s*(?:no|number))?\s*[:#-]?\s*(?P<value>[A-Z0-9][A-Z0-9/-]{2,})\b",
    re.IGNORECASE,
)
PHONE = re.compile(r"(?<!\d)(?P<value>(?:\+?880[ -]?|0)1\d(?:[ -]?\d){8})(?!\d)")
DOCTOR_LINE = re.compile(r"^\s*(?:consultant\s+)?dr\.?\s*(?P<name>[A-Za-z][A-Za-z .'-]{2,80})\s*$", re.IGNORECASE)
MEDICATION_LINE = re.compile(
    r"^\s*(?:(?P<form>tab(?:let)?|cap(?:sule)?|inj(?:ection)?|syp(?:rup)?|drop(?:s)?|neb(?:uliser)?)\.?\s+)?"
    r"(?P<drug>[A-Za-z][A-Za-z0-9()'/-]*(?:\s+[A-Za-z][A-Za-z0-9()'/-]*){0,4}?)\s+"
    r"(?P<strength>\d+(?:\.\d+)?\s*(?:mcg|mg|g|ml|iu|units?))\b(?P<instructions>.*)$",
    re.IGNORECASE,
)
FREQUENCY = re.compile(r"\b(?:od|bd|tds|qid|hs|sos|stat|once\s+(?:a\s+)?daily|twice\s+(?:a\s+)?daily|three\s+times\s+(?:a\s+)?daily|every\s+\d+\s*(?:h|hr|hours?))\b|\b\d\s*[+x]\s*\d\s*[+x]\s*\d(?:\s*[+x]\s*\d)?\b", re.IGNORECASE)


def evidence_excerpt(text, start, end, radius=140):
    """Return a bounded, readable excerpt without cutting words in half."""
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    if left:
        while left < start and not text[left].isspace():
            left += 1
    if right < len(text):
        while right > end and not text[right - 1].isspace():
            right -= 1
    excerpt = text[left:right].strip()
    return f"{'… ' if left else ''}{excerpt}{' …' if right < len(text) else ''}"


def evidence(page, text, start, end, value, confidence):
    return {
        "value": value,
        "source_text": evidence_excerpt(text, start, end),
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
    identifiers, phones, doctors, medications = [], [], [], []
    for page in pages:
        text = page.cleaned_text or page.raw_text
        for match in IDENTIFIER.finditer(text):
            item = evidence(page.page_number, text, match.start("value"), match.end("value"), match.group("value"), 0.98)
            label = match.group("label").lower().replace(".", "").replace(" ", "")
            item["identifier_type"] = "hn" if label == "hn" else ("registration_no" if label.startswith("reg") else label)
            if item["identifier_type"] in {"hn", "registration_no"}:
                item["patient_field"] = "registration_no"
            identifiers.append(item)
        for match in PHONE.finditer(text):
            phones.append(evidence(page.page_number, text, match.start("value"), match.end("value"), match.group("value"), 0.96))
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
    return identifiers, phones, doctors, medications


def analyze_text(pages):
    """Return explicit dates and their sortable order; no clinical meaning is inferred."""
    dates = find_dates(pages)
    identifiers, phones, doctors, medications = find_explicit_entities(pages)
    resolve_medications(medications)
    patient_candidates = find_patient_candidates(identifiers, phones)
    diagnoses, staging = extract_diagnosis_and_staging(pages)
    histopathology = extract_histopathology(pages)
    molecular, ihc, molecular_warnings = extract_molecular_and_ihc(pages)
    treatments, responses, progressions, followups = extract_treatment_and_outcomes(pages)
    procedures = extract_procedure_evidence(pages)
    form_fields = extract_form_fields(pages)
    resolved = sorted((item for item in dates if item["normalized_date"]), key=lambda item: (item["normalized_date"], item["page"]))
    warnings = [item["warning"] for item in dates if item.get("warning")]
    if resolved:
        warnings.append("Chronology orders explicit document dates only; it does not infer treatment, administration, diagnosis, progression, or event meaning.")
    result = {
        "patient": {"identifiers": identifiers, "phones": phones, "match_candidates": patient_candidates},
        "observations": [],
        "prescriber_candidates": doctors,
        "medications": medications,
        "diagnosis_candidates": diagnoses,
        "staging_candidates": staging,
        "histopathology_candidates": histopathology,
        "molecular_candidates": molecular,
        "ihc_candidates": ihc,
        "treatment_candidates": treatments,
        "response_candidates": responses,
        "progression_candidates": progressions,
        "survival_candidates": followups,
        **procedures,
        "form_field_candidates": form_fields,
        "date_candidates": dates,
        "chronology": [{"sequence": index + 1, **item} for index, item in enumerate(resolved)],
        "unresolved_items": [],
        "warnings": warnings + molecular_warnings + (["Medication lines describe prescriptions only; they do not prove drug administration."] if medications else []) + (["Patient candidates are suggestions only; a reviewer must confirm the patient."] if patient_candidates else []),
    }
    result = track_fields(validate_chronology(result))
    return result
