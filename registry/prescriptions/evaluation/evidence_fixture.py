"""Evidence wrappers for synthetic mapper fixtures that model supported facts."""
from copy import deepcopy
from prescriptions.services.field_contract import ALIASES, fields


def evidence_backed_fixture(source):
    source = deepcopy(source)
    gemini = source.get("gemini_extraction", {})
    for observation in gemini.get("observations", []):
        for collection, records in observation.items():
            if not isinstance(records, list):
                continue
            for record in records:
                if not isinstance(record, dict):
                    continue
                for key, value in list(record.items()):
                    canonical = ALIASES.get(collection, {}).get(key, key)
                    if canonical in fields(collection) and value is not None and not isinstance(value, dict):
                        record[key] = {"value": value, "page": 1, "source_text": "Synthetic fixture " + str(value), "confidence": 1.0}
    return source
