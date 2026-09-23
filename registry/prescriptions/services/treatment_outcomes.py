"""Extract explicitly documented treatment and outcome statements without inference."""
import re


TREATMENT = re.compile(r"^\s*(?:treatment\s+plan|regimen|protocol|chemotherapy|immunotherapy|targeted\s+therapy)\s*[:=-]\s*(?P<value>.+?)\s*$", re.IGNORECASE)
LINE = re.compile(r"\b(?P<value>(?:\d+(?:st|nd|rd|th)|first|second|third|fourth)\s*[- ]?line)\b", re.IGNORECASE)
RESPONSE = re.compile(r"^\s*(?:response|recist|irecist)\s*[:=-]\s*(?P<value>.+?)\s*$", re.IGNORECASE)
PROGRESSION = re.compile(r"^\s*(?:disease\s+)?progression\s*[:=-]\s*(?P<value>.+?)\s*$", re.IGNORECASE)
FOLLOW_UP = re.compile(r"^\s*(?:follow[ -]?up|survival\s+status|vital\s+status|death|deceased)\s*[:=-]?\s*(?P<value>.+?)\s*$", re.IGNORECASE)


def evidence(page, line, value, confidence):
    return {"value": value, "source_text": line.strip(), "page": page.page_number, "confidence": confidence}


def extract_treatment_and_outcomes(pages):
    treatments, responses, progressions, followups = [], [], [], []
    for page in pages:
        text = page.cleaned_text or page.raw_text
        for line in text.splitlines():
            treatment = TREATMENT.match(line)
            if treatment:
                line_match = LINE.search(treatment.group("value"))
                treatments.append({
                    "plan_or_regimen": evidence(page, line, treatment.group("value"), 0.93),
                    "line_of_treatment": evidence(page, line, line_match.group("value"), 0.95) if line_match else None,
                    "status": evidence(page, line, "prescribed_or_planned", 0.99),
                })
            response = RESPONSE.match(line)
            if response:
                responses.append(evidence(page, line, response.group("value"), 0.93))
            progression = PROGRESSION.match(line)
            if progression:
                progressions.append(evidence(page, line, progression.group("value"), 0.93))
            follow_up = FOLLOW_UP.match(line)
            if follow_up:
                followups.append(evidence(page, line, follow_up.group("value"), 0.93))
    return treatments, responses, progressions, followups
