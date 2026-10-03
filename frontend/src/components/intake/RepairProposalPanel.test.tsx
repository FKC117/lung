// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { adoptRepairProposal, RepairProposalPanel } from "./RepairProposalPanel";
import { emptyObservation } from "./draftWorkspace";
import type { LongitudinalIntakeDraft, PrescriptionRepairProposal, PrescriptionDraftRecord } from "../../api";
afterEach(cleanup);
const proposal: PrescriptionRepairProposal = { id: "synthetic", collection: "histopathologies", record_id: "synthetic-record", review_revision: 3, patches: { biopsy_date: { value: "2020-01-02", page: 1, source_text: "Synthetic biopsy 2020-01-02" } } };
function fixture(): LongitudinalIntakeDraft {
  const observation = emptyObservation();
  const record: PrescriptionDraftRecord = { temp_id: "synthetic-record", state: "unresolved", values: {}, resolutions: {}, evidence_refs: [] };
  record.temp_id = "synthetic-record";
  record.state = "unresolved";
  record.values.biopsy_date = "Invalid original";
  record.extracted_values = { biopsy_date: "Invalid original" };
  observation.histopathologies.push(record);
  return { schema_version: 1, document_id: 1, patient: { match_status: "unresolved", patient_id: null, values: {} }, observations: [observation], unresolved_items: [] };
}
describe("explicit repair suggestion adoption", () => {
  it("updates only the proposed form field and preserves original evidence", () => {
    const before = fixture();
    const next = adoptRepairProposal(before, proposal);
    expect(next.observations[0].histopathologies[0].values.biopsy_date).toBe("2020-01-02");
    expect(next.observations[0].histopathologies[0].extracted_values).toEqual({ biopsy_date: "Invalid original" });
    expect(before.observations[0].histopathologies[0].values.biopsy_date).toBe("Invalid original");
    expect(next.patient).toEqual(before.patient);
  });
  it("protects reviewer-edited records", () => {
    const draft = fixture();
    draft.observations[0].histopathologies[0].state = "edited";
    expect(() => adoptRepairProposal(draft, proposal)).toThrow(/changed/);
  });
  it("displays source evidence and requires an enabled explicit action", () => {
    const onAdopt = vi.fn();
    const rendered = render(<RepairProposalPanel proposals={[proposal]} disabled onAdopt={onAdopt} />);
    expect(screen.getByText(/Page 1: Synthetic biopsy/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Apply suggestion to form" }));
    expect(onAdopt).not.toHaveBeenCalled();
    rendered.rerender(<RepairProposalPanel proposals={[proposal]} disabled={false} onAdopt={onAdopt} />);
    fireEvent.click(screen.getByRole("button", { name: "Apply suggestion to form" }));
    expect(onAdopt).toHaveBeenCalledWith(proposal);
  });
});
