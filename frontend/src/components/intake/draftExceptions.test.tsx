// @vitest-environment jsdom
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { LongitudinalIntakeDraft, PrescriptionDocument } from "../../api";
import { emptyObservation, moveRecord } from "./draftWorkspace";
import { draftExceptions } from "./draftExceptions";
import { LongitudinalDraftWorkspace } from "./LongitudinalDraftWorkspace";
afterEach(cleanup);

function fixture(): LongitudinalIntakeDraft {
  const first = emptyObservation();
  const second = emptyObservation();
  second.histopathologies.push({ temp_id: "synthetic-pathology", state: "unresolved", values: {},
    extracted_values: { histopathology_type: "Synthetic histology" }, fact_dispositions: [], evidence_refs: ["synthetic-quote"],
    resolutions: { histopathology_type: { status: "ambiguous", resource: "histopathology-types", raw_value: "Synthetic histology", option_id: null,
      match_method: null, candidates: [{ option_id: 1, label: "Synthetic choice", match_method: "fuzzy", score: 0.8 }], reason: "Choose the matching histology." } } });
  second.evidence_refs.push({ evidence_id: "synthetic-quote", field_path: "histopathologies.0.histopathology_type", source_text: "Synthetic source quote", page: 2, confidence: 0.9 });
  return { schema_version: 1, document_id: 1, patient: { match_status: "unresolved", patient_id: null, values: {} }, observations: [first, second], unresolved_items: [] };
}

describe("grouped prescription exceptions", () => {
  it("includes fields from unselected observations with original text and suggestions", () => {
    const issues = draftExceptions(fixture());
    expect(issues).toHaveLength(1);
    expect(issues[0].rawValue).toBe("Synthetic histology");
    expect(issues[0].source).toContain("p. 2: Synthetic source quote");
    expect(issues[0].candidates).toEqual(["Synthetic choice"]);
  });

  it("follows stable record identity after moving between observations", () => {
    const draft = fixture();
    draft.unresolved_items.push({ record_temp_id: "synthetic-pathology", observation_temp_id: draft.observations[1].temp_id, collection: "histopathologies", field: "histopathology_type", reason: "Synthetic mapping issue" });
    const moved = moveRecord(draft, draft.observations[1].temp_id, draft.observations[0].temp_id, { collection: "histopathologies", tempId: "synthetic-pathology" });
    expect(draftExceptions(moved).every((item) => item.observationId === draft.observations[0].temp_id)).toBe(true);
  });

  it("opens the actual section and focuses its dropdown", () => {
    const draft = fixture();
    const document = { original_filename: "synthetic.pdf", file: "/synthetic.pdf", extraction_runs: [] } as unknown as PrescriptionDocument;
    render(<LongitudinalDraftWorkspace document={document} draft={draft} catalog={{}} onChange={() => undefined} onSave={() => undefined} />);
    fireEvent.click(screen.getByRole("button", { name: "Review in form" }));
    expect(window.document.activeElement?.tagName).toBe("SELECT");
    expect(window.document.activeElement?.closest("article")?.getAttribute("data-record-id")).toBe("synthetic-pathology");
  });
});


it("recovers record field and immutable evidence when issue omits its collection", () => {
  const draft = fixture();
  draft.unresolved_items.push({record_temp_id: "synthetic-pathology", field: "histopathology_type", reason: "Synthetic evidence check"});
  const issue = draftExceptions(draft).find((item) => item.id === "issue:0")!;
  expect(issue.collection).toBe("histopathologies");
  expect(issue.rawValue).toBe("Synthetic histology");
  expect(issue.source).toContain("Synthetic source quote");
  expect(issue.action).toContain("save");
});

it("opens the selected observation context and focuses the actual date field", () => {
  const draft = fixture();
  draft.observations[1].histopathologies = [];
  draft.unresolved_items.push({observation_temp_id: draft.observations[1].temp_id, field_path: "observations.1.prescription_date", reason: "Confirm the synthetic date"});
  const document = { original_filename: "synthetic.pdf", file: "/synthetic.pdf", extraction_runs: [] } as unknown as PrescriptionDocument;
  render(<LongitudinalDraftWorkspace document={document} draft={draft} catalog={{}} onChange={() => undefined} onSave={() => undefined} />);
  fireEvent.click(screen.getByRole("button",{name:"Review in form"}));
  expect(window.document.activeElement?.getAttribute("type")).toBe("date");
  expect(window.document.activeElement?.closest("label")?.getAttribute("data-intake-label")).toBe("Prescription date");
});
