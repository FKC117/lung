import { describe, expect, it } from "vitest";
import type { LongitudinalIntakeDraft, PrescriptionDraftRecord } from "../../api";
import { deleteObservation, emptyObservation, mergeObservations, moveRecord, splitObservation } from "./draftWorkspace";

function record(tempId: string, evidenceId: string): PrescriptionDraftRecord {
  return { temp_id: tempId, state: "unresolved", values: { diagnosis_in_details: "Example" }, resolutions: {}, evidence_refs: [evidenceId] };
}

function draft(): LongitudinalIntakeDraft {
  const first = emptyObservation();
  const second = emptyObservation();
  first.diagnoses.push(record("diagnosis-1", "evidence-1"));
  first.treatments.push(record("treatment-1", "evidence-2"));
  first.evidence_refs.push(
    { evidence_id: "evidence-1", field_path: "diagnoses.0", source_text: "Diagnosis", page: 1, confidence: .9 },
    { evidence_id: "evidence-2", field_path: "treatments.0", source_text: "Treatment", page: 2, confidence: .8 },
    { evidence_id: "evidence-date", field_path: "observed_at", source_text: "Visit date", page: 1, confidence: .95 },
    { evidence_id: "evidence-context", field_path: "temporal_context", source_text: "Previous treatment", page: 1, confidence: .82 },
    { evidence_id: "evidence-anthropometry", field_path: "anthropometry.weight", source_text: "Weight 62 kg", page: 1, confidence: .91 },
  );
  return { schema_version: 1, document_id: 7, patient: { match_status: "unresolved", patient_id: null, values: {} }, observations: [first, second], unresolved_items: [] };
}

describe("longitudinal draft operations", () => {
  it("moves a record and its evidence without mutating the input", () => {
    const source = draft();
    const [first, second] = source.observations;
    const moved = moveRecord(source, first.temp_id, second.temp_id, { collection: "diagnoses", tempId: "diagnosis-1" });
    expect(source.observations[0].diagnoses).toHaveLength(1);
    expect(moved.observations[0].diagnoses).toHaveLength(0);
    expect(moved.observations[0].evidence_refs.map((item) => item.evidence_id)).toEqual(["evidence-2", "evidence-date", "evidence-context", "evidence-anthropometry"]);
    expect(moved.observations[1].diagnoses[0].temp_id).toBe("diagnosis-1");
    expect(moved.observations[1].evidence_refs[0].evidence_id).toBe("evidence-1");
  });

  it("splits selected records into a new observation with linked evidence", () => {
    const source = draft();
    const split = splitObservation(source, source.observations[0].temp_id, [{ collection: "treatments", tempId: "treatment-1" }]);
    expect(split.observations).toHaveLength(3);
    expect(split.observations[0].diagnoses).toHaveLength(1);
    expect(split.observations[0].treatments).toHaveLength(0);
    expect(split.observations[2].treatments[0].temp_id).toBe("treatment-1");
    expect(split.observations[2].evidence_refs.map((item) => item.evidence_id)).toEqual(["evidence-date", "evidence-context", "evidence-anthropometry", "evidence-2"]);
    expect(split.observations[0].evidence_refs.map((item) => item.evidence_id)).toContain("evidence-date");
  });

  it("merges every record and removes only the source observation", () => {
    const source = draft();
    const [first, second] = source.observations;
    const merged = mergeObservations(source, first.temp_id, second.temp_id);
    expect(merged.observations).toHaveLength(1);
    expect(merged.observations[0].diagnoses).toHaveLength(1);
    expect(merged.observations[0].treatments).toHaveLength(1);
    expect(merged.observations[0].evidence_refs.map((item) => item.evidence_id)).toEqual(expect.arrayContaining(["evidence-1", "evidence-2", "evidence-date", "evidence-context", "evidence-anthropometry"]));
  });

  it("never deletes the final observation", () => {
    const source = draft();
    const one = { ...source, observations: [source.observations[0]] };
    expect(deleteObservation(one, one.observations[0].temp_id)).toBe(one);
    expect(deleteObservation(source, source.observations[0].temp_id).observations).toHaveLength(1);
  });
});
