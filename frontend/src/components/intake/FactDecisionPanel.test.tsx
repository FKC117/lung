// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { LongitudinalIntakeDraft } from "../../api";
import { emptyObservation } from "./draftWorkspace";
import { FactDecisionPanel } from "./FactDecisionPanel";
afterEach(cleanup);

describe("source fact decisions", () => {
  it("includes supported source fields whose dropdown is still unresolved", () => {
    const observation = emptyObservation();
    observation.histopathologies.push({ temp_id: "synthetic-record", state: "unresolved", values: { histopathology_type: "Synthetic unknown" }, evidence_refs: [], resolutions: {
      histopathology_type: { status: "unresolved", resource: "histopathology-types", raw_value: "Synthetic unknown", option_id: null, candidates: [], reason: "Empty catalog", match_method: null } } });
    const draft: LongitudinalIntakeDraft = { schema_version: 1, document_id: 1, patient: { match_status: "unresolved", patient_id: null, values: {} }, observations: [observation], unresolved_items: [],
      source_facts: [{ fact_id: "observations.0.histopathologies.0.histopathology_type", source_path: "observations.0.histopathologies.0.histopathology_type", raw_value: "Synthetic unknown", disposition: "mapped", reason: "", collection: "histopathologies", record_temp_id: "synthetic-record", canonical_field: "histopathology_type" }] };
    render(<FactDecisionPanel draft={draft} onChange={() => undefined} />);
    expect(screen.getByRole("button", { name: "Record decision" })).toBeTruthy();
    expect(screen.getByText(/Original extracted value: Synthetic unknown/)).toBeTruthy();
  });
  it("shows removed mapped facts so their exclusion can be recorded", () => {
    const draft: LongitudinalIntakeDraft = { schema_version: 1, document_id: 1, patient: { match_status: "unresolved", patient_id: null, values: {} }, observations: [emptyObservation()], unresolved_items: [],
      source_facts: [{ fact_id: "original.summary", source_path: "original.summary", raw_value: "Synthetic removed summary", disposition: "mapped", reason: "", collection: "histopathologies", record_temp_id: "removed-record", canonical_field: "report_summary" }] };
    const onChange = vi.fn();
    render(<FactDecisionPanel draft={draft} onChange={onChange} />);
    expect(screen.getByText(/Original extracted value: Synthetic removed summary/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Reason for original.summary"), { target: { value: "Synthetic duplicate record" } });
    fireEvent.change(screen.getByLabelText("Decision for original.summary"), { target: { value: "exclude" } });
    fireEvent.click(screen.getByRole("button", { name: "Record decision" }));
    expect(onChange.mock.calls[0][0].fact_decisions[0].action).toBe("exclude");
    expect(onChange.mock.calls[0][0].source_facts).toEqual(draft.source_facts);
  });
  it("requires a reason and preserves original evidence while recording a decision", () => {
    const draft: LongitudinalIntakeDraft = { schema_version: 1, document_id: 1, patient: { match_status: "unresolved", patient_id: null, values: {} },
      observations: [emptyObservation()], unresolved_items: [], source_facts: [{ fact_id: "patient.unknown", source_path: "patient.unknown", raw_value: "Synthetic original", disposition: "unresolved", reason: "Needs placement" }] };
    const onChange = vi.fn();
    render(<FactDecisionPanel draft={draft} onChange={onChange} />);
    const button = screen.getByRole("button", { name: "Record decision" }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("Reason for patient.unknown"), { target: { value: "Synthetic duplicate" } });
    fireEvent.change(screen.getByLabelText("Decision for patient.unknown"), { target: { value: "exclude" } });
    fireEvent.click(button);
    const result = onChange.mock.calls[0][0];
    expect(result.fact_decisions).toEqual([{ fact_id: "patient.unknown", action: "exclude", reason: "Synthetic duplicate" }]);
    expect(result.source_facts).toEqual(draft.source_facts);
    expect(draft.fact_decisions).toBeUndefined();
    expect(result.patient.match_status).toBe("unresolved");
  });
});
