"""Evidence-only chronology validation; it deliberately does not infer clinical events."""
def validate_chronology(result):
    """Attach transparent validation output to a deterministic extraction proposal."""
    dates = result.get("date_candidates", [])
    chronology = result.get("chronology", [])
    issues = []

    for item in dates:
        if item.get("warning"):
            issues.append({"code": "ambiguous_or_invalid_date", "severity": "warning", "message": item["warning"], "page": item["page"]})

    ordered_dates = [item["normalized_date"] for item in chronology]
    if ordered_dates != sorted(ordered_dates):
        issues.append({"code": "chronology_sort_error", "severity": "error", "message": "The proposed chronology is not date ordered."})
    if dates and not chronology:
        issues.append({"code": "no_resolved_dates", "severity": "warning", "message": "Dates were found but none can be safely ordered until date format is confirmed."})
    if not dates:
        issues.append({"code": "no_dates_found", "severity": "info", "message": "No explicit calendar date was found in the extracted text."})

    result["validation"] = {"chronology_status": "review_required", "issues": issues}
    return result
