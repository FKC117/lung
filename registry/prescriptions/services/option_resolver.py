"""Conservative matching of extracted medication text to approved treatment-drug options."""
import re
import unicodedata
from difflib import SequenceMatcher

from options.models import TreatmentDrug
from prescriptions.models import PrescriptionDrugAlias


def normalize(value):
    value = unicodedata.normalize("NFKD", value).casefold()
    value = "".join(character for character in value if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", "", value)


def candidate(drug, method, score=1.0):
    return {"option_id": drug.pk, "name": drug.name, "match_method": method, "score": round(score, 3)}


def resolve_drug(value):
    """Resolve only unambiguous approved values; fuzzy candidates require a reviewer."""
    name = (value or "").strip()
    if not name:
        return {"status": "unresolved", "reason": "No drug text was extracted.", "candidates": []}

    exact = list(TreatmentDrug.objects.filter(name__iexact=name).only("id", "name"))
    if len(exact) == 1:
        return {"status": "resolved", "resolution": "exact_name", "matched_option": candidate(exact[0], "exact_name"), "candidates": []}

    target = normalize(name)
    drugs = list(TreatmentDrug.objects.only("id", "name"))
    normalized = [drug for drug in drugs if normalize(drug.name) == target]
    if len(normalized) == 1:
        return {"status": "resolved", "resolution": "normalized_name", "matched_option": candidate(normalized[0], "normalized_name"), "candidates": []}

    aliases = list(PrescriptionDrugAlias.objects.select_related("drug").only("alias", "drug__id", "drug__name"))
    alias_matches = [alias.drug for alias in aliases if normalize(alias.alias) == target]
    unique_aliases = {drug.pk: drug for drug in alias_matches}
    if len(unique_aliases) == 1:
        drug = next(iter(unique_aliases.values()))
        return {"status": "resolved", "resolution": "approved_alias", "matched_option": candidate(drug, "approved_alias"), "candidates": []}

    suggestions = []
    for drug in drugs:
        score = SequenceMatcher(None, target, normalize(drug.name)).ratio()
        if score >= 0.70:
            suggestions.append(candidate(drug, "fuzzy", score))
    suggestions.sort(key=lambda item: (-item["score"], item["name"]))
    if suggestions:
        return {"status": "review_required", "reason": "Fuzzy matches are suggestions only.", "candidates": suggestions[:5]}
    return {"status": "unresolved", "reason": "No approved treatment-drug option matched this text.", "candidates": []}


def resolve_medications(medications):
    for medication in medications:
        medication["drug_match"] = resolve_drug(medication["drug"]["value"])
    return medications
