"""Evidence-only extraction of explicitly documented histopathology findings."""
import re


PATHOLOGY_LINE = re.compile(
    r"^\s*(?:histopathology|histology|hpe|pathology|biopsy(?:\s+report)?)\s*[:=-]\s*(?P<value>.+?)\s*$",
    re.IGNORECASE,
)
GRADE = re.compile(r"\b(?:grade\s*(?P<number>[1-4]|[ivx]{1,3})|(?P<description>well|moderately|poorly)\s*differentiated)\b", re.IGNORECASE)


def evidence(page, line, value, confidence):
    return {"value": value, "source_text": line.strip(), "page": page.page_number, "confidence": confidence}


def extract_histopathology(pages):
    findings = []
    for page in pages:
        text = page.cleaned_text or page.raw_text
        for line in text.splitlines():
            pathology = PATHOLOGY_LINE.match(line)
            if not pathology:
                continue
            value = pathology.group("value")
            findings.append({
                "finding": evidence(page, line, value, 0.93),
                "grades": [evidence(page, line, grade.group(0), 0.95) for grade in GRADE.finditer(value)],
            })
    return findings
