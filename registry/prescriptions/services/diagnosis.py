"""Explicit diagnosis and staging extraction without clinical inference."""
import re


DIAGNOSIS_LINE = re.compile(r"^\s*(?:diagnosis|dx|impression|assessment)\s*[:=-]\s*(?P<value>.+?)\s*$", re.IGNORECASE)
TNM = re.compile(
    r"(?<![A-Za-z0-9])(?P<prefix>[cp])?\s*T(?P<t>is|[0-4](?:[a-c])?)\s*N(?P<n>[0-3](?:[a-c])?)\s*M(?P<m>[01](?:[a-c])?)(?![A-Za-z0-9])",
    re.IGNORECASE,
)
STAGE = re.compile(r"\b(?:stage|stg)\s*(?P<value>(?:[IVX]{1,4}|[1-4])(?:[ABC])?)\b", re.IGNORECASE)


def evidence(page, line, value, confidence):
    return {"value": value, "source_text": line.strip(), "page": page.page_number, "confidence": confidence}


def extract_diagnosis_and_staging(pages):
    diagnoses, staging = [], []
    for page in pages:
        text = page.cleaned_text or page.raw_text
        for line in text.splitlines():
            diagnosis = DIAGNOSIS_LINE.match(line)
            if diagnosis:
                diagnoses.append(evidence(page, line, diagnosis.group("value"), 0.93))
            for match in TNM.finditer(line):
                prefix = (match.group("prefix") or "").lower()
                staging.append({
                    "staging_type": {"c": "clinical", "p": "pathological"}.get(prefix, "not_stated"),
                    "t": evidence(page, line, f"T{match.group('t')}", 0.98),
                    "n": evidence(page, line, f"N{match.group('n')}", 0.98),
                    "m": evidence(page, line, f"M{match.group('m')}", 0.98),
                    "stage": None,
                })
            for match in STAGE.finditer(line):
                staging.append({
                    "staging_type": "not_stated",
                    "t": None,
                    "n": None,
                    "m": None,
                    "stage": evidence(page, line, f"Stage {match.group('value').upper()}", 0.96),
                })
    return diagnoses, staging
