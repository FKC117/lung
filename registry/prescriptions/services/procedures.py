"""Explicit treatment administration, surgery, radiotherapy, and marker evidence."""
import re

LABELS = {
    "administration_candidates": re.compile(r"^\s*(?:administered|given|cycle\s*\d+|day\s*\d+)\s*[:=-]\s*(.+)$", re.I),
    "surgery_candidates": re.compile(r"^\s*(?:surgery|operation|procedure)\s*[:=-]\s*(.+)$", re.I),
    "radiotherapy_candidates": re.compile(r"^\s*(?:radiotherapy|radiation\s+therapy|rt)\s*[:=-]\s*(.+)$", re.I),
    "cancer_marker_candidates": re.compile(r"^\s*(?:cea|ca[- ]?125|ca[- ]?19[- ]?9|afp|psa)\s*[:=-]\s*(.+)$", re.I),
}

def extract_procedure_evidence(pages):
    result = {key: [] for key in LABELS}
    for page in pages:
        for line in (page.cleaned_text or page.raw_text).splitlines():
            for key, pattern in LABELS.items():
                match = pattern.match(line)
                if match:
                    result[key].append({"value": match.group(1).strip(), "source_text": line.strip(), "page": page.page_number, "confidence": 0.93})
    return result
