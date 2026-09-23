"""Conservative patient-candidate lookup from explicit HN/registration and phone evidence."""
import re

from records.models import Patient


def normalize_phone(value):
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("880") and len(digits) == 13:
        return "0" + digits[2:]
    return digits


def patient_summary(patient, signals):
    return {
        "patient_id": patient.pk,
        "registry_identifier": patient.patient_id,
        "registration_no": patient.registration_no,
        "phone": patient.phone,
        "match_signals": sorted(signals),
    }


def find_patient_candidates(identifiers, phones):
    """Return candidates only; a reviewer must select the patient explicitly."""
    matches = {}
    for identifier in identifiers:
        if identifier.get("identifier_type") not in {"hn", "registration_no"}:
            continue
        for patient in Patient.objects.filter(registration_no__iexact=identifier["value"]).only("id", "patient_id", "registration_no", "phone"):
            matches.setdefault(patient.pk, [patient, set()])[1].add("hn_registration_no")
    normalized_phones = {normalize_phone(item["value"]) for item in phones}
    normalized_phones.discard("")
    if normalized_phones:
        for patient in Patient.objects.exclude(phone="").only("id", "patient_id", "registration_no", "phone"):
            if normalize_phone(patient.phone) in normalized_phones:
                matches.setdefault(patient.pk, [patient, set()])[1].add("phone")
    candidates = [patient_summary(patient, signals) for patient, signals in matches.values()]
    candidates.sort(key=lambda item: (-len(item["match_signals"]), item["patient_id"]))
    return candidates
