"""Record completeness uses the same declarative fields as the actual form."""
from prescriptions.services.field_contract import fields, contract


def populated(value):
    return bool(value.strip()) if isinstance(value, str) else value not in (None, "", [])


def record_issues(collection, record):
    issues = []
    values = record.get("values", {})
    for key, definition in fields(collection).items():
        value = values.get(key)
        if definition.get("required") and not populated(value):
            issues.append(f"{key} is required.")
        if populated(value) and definition.get("persisted") is False:
            issues.append(f"{key} has no canonical persistence destination.")
        if populated(value) and definition.get("resource"):
            resolution = record.get("resolutions", {}).get(key, {})
            if resolution.get("status") != "resolved":
                issues.append(f"{key} requires a canonical selection.")
    for key, resolution in record.get("resolutions", {}).items():
        if resolution.get("status") != "resolved" and not any(issue.startswith(f"{key} ") for issue in issues):
            issues.append(f"{key} requires a canonical selection.")
    return issues


def mark_ready_records(draft):
    for observation in draft.get("observations", []):
        for collection in contract()["collections"]:
            for record in observation.get(collection, []):
                # Mapping/evidence exceptions must be dealt with separately.
                if record.get("state") != "unresolved" and not record_issues(collection, record):
                    record["state"] = "validated"
    return draft
