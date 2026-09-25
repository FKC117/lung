import type { LongitudinalIntakeDraft, PrescriptionDraftRecord, PrescriptionObservationDraft } from "../../api";

export const observationCollections = [
  "comorbidities", "diagnoses", "histopathologies", "ihc_results",
  "pathological_staging_results", "clinical_tnm_stagings", "pathological_tnm_stagings",
  "molecular_tests", "cancer_markers", "treatments", "surgeries", "radiotherapies",
  "recist_assessments", "irecist_assessments", "pathological_responses",
  "progression_records", "survival_records",
] as const;

export type ObservationCollection = (typeof observationCollections)[number];
export type RecordRef = { collection: ObservationCollection; tempId: string };

let sequence = 0;
export function draftTempId(prefix: string) {
  sequence += 1;
  return `${prefix}-${Date.now().toString(36)}-${sequence.toString(36)}`;
}

export function emptyObservation(source?: PrescriptionObservationDraft): PrescriptionObservationDraft {
  return {
    temp_id: draftTempId("observation"),
    observed_at: source?.observed_at ?? null,
    prescription_date: source?.prescription_date ?? null,
    temporal_context: source?.temporal_context ?? "unknown",
    anthropometry: source?.anthropometry ? structuredClone(source.anthropometry) : null,
    comorbidities: [], diagnoses: [], histopathologies: [], ihc_results: [],
    pathological_staging_results: [], clinical_tnm_stagings: [], pathological_tnm_stagings: [],
    molecular_tests: [], cancer_markers: [], treatments: [], surgeries: [], radiotherapies: [],
    recist_assessments: [], irecist_assessments: [], pathological_responses: [],
    progression_records: [], survival_records: [], evidence_refs: [],
  };
}

function referencedEvidence(observation: PrescriptionObservationDraft, records: PrescriptionDraftRecord[]) {
  const ids = new Set(records.flatMap((record) => record.evidence_refs));
  return observation.evidence_refs.filter((evidence) => ids.has(evidence.evidence_id));
}

function withoutOrphanedEvidence(observation: PrescriptionObservationDraft) {
  const used = new Set(observationCollections.flatMap((collection) => observation[collection].flatMap((record) => record.evidence_refs)));
  return { ...observation, evidence_refs: observation.evidence_refs.filter((evidence) => used.has(evidence.evidence_id)) };
}

export function moveRecord(draft: LongitudinalIntakeDraft, sourceId: string, targetId: string, ref: RecordRef) {
  if (sourceId === targetId) return draft;
  const next = structuredClone(draft);
  const source = next.observations.find((item) => item.temp_id === sourceId);
  const target = next.observations.find((item) => item.temp_id === targetId);
  if (!source || !target) return draft;
  const record = source[ref.collection].find((item) => item.temp_id === ref.tempId);
  if (!record) return draft;
  source[ref.collection] = source[ref.collection].filter((item) => item.temp_id !== ref.tempId);
  target[ref.collection].push(record);
  const evidence = referencedEvidence(source, [record]);
  const existing = new Set(target.evidence_refs.map((item) => item.evidence_id));
  target.evidence_refs.push(...evidence.filter((item) => !existing.has(item.evidence_id)));
  Object.assign(source, withoutOrphanedEvidence(source));
  return next;
}

export function splitObservation(draft: LongitudinalIntakeDraft, sourceId: string, refs: RecordRef[]) {
  if (!refs.length) return draft;
  let next = structuredClone(draft);
  const source = next.observations.find((item) => item.temp_id === sourceId);
  if (!source) return draft;
  const created = emptyObservation(source);
  next.observations.push(created);
  for (const ref of refs) next = moveRecord(next, sourceId, created.temp_id, ref);
  return next;
}

export function mergeObservations(draft: LongitudinalIntakeDraft, sourceId: string, targetId: string) {
  if (sourceId === targetId || draft.observations.length < 2) return draft;
  let next = structuredClone(draft);
  const source = next.observations.find((item) => item.temp_id === sourceId);
  if (!source || !next.observations.some((item) => item.temp_id === targetId)) return draft;
  const refs = observationCollections.flatMap((collection) => source[collection].map((record) => ({ collection, tempId: record.temp_id })));
  for (const ref of refs) next = moveRecord(next, sourceId, targetId, ref);
  next.observations = next.observations.filter((item) => item.temp_id !== sourceId);
  return next;
}

export function deleteObservation(draft: LongitudinalIntakeDraft, observationId: string) {
  if (draft.observations.length <= 1) return draft;
  return { ...draft, observations: draft.observations.filter((item) => item.temp_id !== observationId) };
}

export function recordCount(observation: PrescriptionObservationDraft) {
  return observationCollections.reduce((total, collection) => total + observation[collection].length, 0);
}
