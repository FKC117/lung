"""Conservative cross-source reconciliation: preserve events, require explicit overlap decisions."""
from .field_contract import fields


def _value(value):
    return " ".join(value.split()).casefold() if isinstance(value, str) else value


def reconcile_extracted_records(draft):
    local = next((obs for obs in draft["observations"] if obs["temp_id"] == "observation-legacy-1"), None)
    if not local:
        return draft
    for observation in draft["observations"]:
        if observation is local:
            continue
        for collection in fields_collections():
            definitions = fields(collection)
            for record in observation.get(collection, []):
                for baseline in local.get(collection, []):
                    common = [key for key in record["values"] if key in baseline["values"] and record["values"][key] not in (None,"",[]) and baseline["values"][key] not in (None,"",[])]
                    if not common:
                        continue
                    dates = [key for key in common if definitions.get(key,{}).get("type") in {"date","datetime-local"}]
                    if any(record["values"][key] != baseline["values"][key] for key in dates):
                        continue  # Explicitly different event dates stay separate.
                    equal = all(_value(record["values"][key]) == _value(baseline["values"][key]) for key in common)
                    if not equal and not dates:
                        continue  # No reliable event anchor; do not infer contradiction.
                    reason = "Possible cross-source overlap; confirm distinct events or explicitly exclude the duplicate." if equal else "Cross-source findings differ at the same explicit event date; reconcile without discarding either source."
                    record["state"] = "unresolved"
                    for key in common:
                        for fact in record.get("fact_dispositions",[]):
                            if fact.get("canonical_field") == key:
                                fact["disposition"] = "unresolved"
                        identity = (collection, record["temp_id"], key)
                        if not any((item.get("collection"),item.get("record_temp_id"),item.get("field")) == identity and item.get("type") == "fact_decision_required" for item in draft["unresolved_items"]):
                            draft["unresolved_items"].append({"type":"fact_decision_required","collection":collection,"record_temp_id":record["temp_id"],"observation_temp_id":observation["temp_id"],"field":key,"related_record_temp_id":baseline["temp_id"],"reason":reason})
    return draft


def fields_collections():
    from .field_contract import contract
    return contract()["collections"]
