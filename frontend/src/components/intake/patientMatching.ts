import type { EntriesPatientMatch, LongitudinalIntakeDraft } from "../../api";

type PatientDraft = LongitudinalIntakeDraft["patient"];

export function applyPatientMatch(patient: PatientDraft, match: EntriesPatientMatch): PatientDraft {
  return {
    ...patient,
    match_status: "existing",
    patient_id: match.id,
    values: { ...patient.values, patient_id: match.patient_id, name: match.name, phone: match.phone, registration_no: match.registration_no },
  };
}
