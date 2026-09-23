"""Evidence-only molecular and IHC extraction with conservative handling of negatives."""
import re


GENE = re.compile(r"\b(EGFR|ALK|ROS1|BRAF|KRAS|MET|RET|ERBB2|HER2|NTRK(?:1|2|3)?)\b", re.IGNORECASE)
EXON = re.compile(r"\bexon\s*(\d+)\b", re.IGNORECASE)
VARIANT = re.compile(r"\b(?:del(?:etion)?\s*\d+|[A-Z]\d{2,5}[A-Z*]|ins(?:ertion)?\s*\d*)\b", re.IGNORECASE)
RESULT = re.compile(r"\b(positive|negative|detected|not\s+detected|wild\s*type|mutated|amplified|rearranged)\b", re.IGNORECASE)
IHC_MARKER = re.compile(r"\b(TTF[- ]?1|Napsin\s*A|p40|p63|CK7|CK5/6|PD[- ]?L1|ALK)\b", re.IGNORECASE)
TPS = re.compile(r"\bTPS\s*[:=]?\s*(\d{1,3}(?:\.\d+)?)\s*%", re.IGNORECASE)


def evidence(page, line, value, confidence):
    return {"value": value, "source_text": line.strip(), "page": page.page_number, "confidence": confidence}


def extract_molecular_and_ihc(pages):
    molecular, ihc, warnings = [], [], []
    for page in pages:
        text = page.cleaned_text or page.raw_text
        for line in text.splitlines():
            genes = list(GENE.finditer(line))
            result = RESULT.search(line)
            if "ihc" not in line.casefold():
                for gene in genes:
                    item = {
                        "gene": evidence(page, line, gene.group(0).upper(), 0.97),
                        "exon": evidence(page, line, f"Exon {EXON.search(line).group(1)}", 0.95) if EXON.search(line) else None,
                        "variant": evidence(page, line, VARIANT.search(line).group(0), 0.88) if VARIANT.search(line) else None,
                        "reported_result": evidence(page, line, result.group(0), 0.94) if result else None,
                    }
                    molecular.append(item)
                    if result and result.group(0).lower() in {"negative", "not detected", "wild type"}:
                        warnings.append("A molecular negative/not-detected result was extracted as text and requires reviewer confirmation of a finalized panel.")
            if "ihc" not in line.casefold():
                continue
            for marker in IHC_MARKER.finditer(line):
                marker_name = marker.group(0).upper().replace(" ", "-") if marker.group(0).upper().startswith("PD") else marker.group(0)
                segment = re.split(r"[,;]", line[marker.end():], maxsplit=1)[0]
                marker_result = RESULT.search(segment)
                tps = TPS.search(segment)
                ihc.append({
                    "marker": evidence(page, line, marker_name, 0.96),
                    "reported_result": evidence(page, line, marker_result.group(0), 0.93) if marker_result else None,
                    "tps": evidence(page, line, f"{tps.group(1)}%", 0.96) if marker_name == "PD-L1" and tps else None,
                })
    return molecular, ihc, sorted(set(warnings))
