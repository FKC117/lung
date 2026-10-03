// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { emptyObservation } from "../components/intake/draftWorkspace";
import PrescriptionCorrectionPage from "./PrescriptionCorrectionPage";
import * as api from "../api";
import type { PrescriptionReview, PrescriptionDocument, LongitudinalIntakeDraft } from "../api";
vi.mock("../api", async (original) => ({ ...await original<typeof import("../api")>(), fetchPrescriptionDocument: vi.fn(), loadLatestPrescriptionExtraction: vi.fn(), fetchPrescriptionRepairProposals: vi.fn(), fetchEntriesOptions: vi.fn(), updatePrescriptionReview: vi.fn(), approvePrescriptionReview: vi.fn(), publishPrescriptionReview: vi.fn() }));
afterEach(cleanup);
let review: PrescriptionReview;
beforeEach(() => {
  vi.clearAllMocks();
  const draft: LongitudinalIntakeDraft = { schema_version: 1, document_id: 1, patient: { match_status: "new", patient_id: null, values: { name: "Original synthetic" } }, observations: [emptyObservation()], unresolved_items: [] };
  review = { id: 1, revision: 1, approved_revision: null, status: "in_review", reviewed_data: draft, published_at: null } as unknown as PrescriptionReview;
  vi.mocked(api.fetchPrescriptionDocument).mockResolvedValue({ id: 1, original_filename: "synthetic.pdf", file: "/synthetic.pdf", extraction_runs: [], review } as unknown as PrescriptionDocument);
  vi.mocked(api.fetchEntriesOptions).mockResolvedValue({});
  vi.mocked(api.fetchPrescriptionRepairProposals).mockResolvedValue({ revision: 1, proposals: [] });
});
function open() {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={["/prescriptions/1/correct"]}><Routes><Route path="/prescriptions/:documentId/correct" element={<PrescriptionCorrectionPage />} /><Route path="/prescriptions" element={<p>Queue</p>} /></Routes></MemoryRouter></QueryClientProvider>);
}
describe("saved revision final confirmation", () => {
  it("saves edited form values before approval and publishes the returned revision", async () => {
    let finishSave: (value: PrescriptionReview) => void = () => undefined;
    vi.mocked(api.updatePrescriptionReview).mockImplementation(() => new Promise((resolve) => { finishSave = resolve; }));
    vi.mocked(api.approvePrescriptionReview).mockImplementation(async (_id, revision) => ({ ...review, revision: revision!, approved_revision: revision!, status: "approved" }));
    open();
    const input = await screen.findByRole("textbox", { name: "Patient name" });
    fireEvent.change(input, { target: { value: "Corrected synthetic" } });
    expect(input).toHaveProperty("value", "Corrected synthetic");
    fireEvent.click(screen.getByRole("button", { name: /Approve/ }));
    await waitFor(() => expect(api.updatePrescriptionReview).toHaveBeenCalledTimes(1));
    expect(api.approvePrescriptionReview).not.toHaveBeenCalled();
    const submitted = vi.mocked(api.updatePrescriptionReview).mock.calls[0][1];
    expect(submitted.expected_revision).toBe(1);
    expect(submitted.reviewed_data?.patient.values.name).toBe("Corrected synthetic");
    finishSave({ ...review, revision: 2, reviewed_data: submitted.reviewed_data! });
    await waitFor(() => expect(api.approvePrescriptionReview).toHaveBeenCalledWith(1, 2));
    fireEvent.click(await screen.findByRole("button", { name: /Publish/ }));
    await waitFor(() => expect(api.publishPrescriptionReview).toHaveBeenCalledWith(1, 2));
  });
  it("keeps dirty values and does not approve when save fails", async () => {
    vi.mocked(api.updatePrescriptionReview).mockRejectedValue(new Error("Synthetic save failure"));
    open();
    const input = await screen.findByRole("textbox", { name: "Patient name" });
    fireEvent.change(input, { target: { value: "Unsaved synthetic" } });
    fireEvent.click(screen.getByRole("button", { name: /Approve/ }));
    await screen.findByText("Synthetic save failure");
    expect(input).toHaveProperty("value", "Unsaved synthetic");
    expect(api.approvePrescriptionReview).not.toHaveBeenCalled();
    expect(api.publishPrescriptionReview).not.toHaveBeenCalled();
  });
});


it("adopts a saved repair into the actual form and saves only on explicit request", async () => {
  review.reviewed_data.observations[0].histopathologies.push({ temp_id: "synthetic-repair", state: "unresolved", values: { biopsy_date: null }, extracted_values: { biopsy_date: "Invalid original" }, resolutions: {}, evidence_refs: [] });
  vi.mocked(api.fetchPrescriptionRepairProposals).mockResolvedValue({ revision: 1, proposals: [{ id: "synthetic", collection: "histopathologies", record_id: "synthetic-repair", review_revision: 1, patches: { biopsy_date: { value: "2020-01-02", page: 1, source_text: "Synthetic biopsy 2020-01-02" } } }] });
  vi.mocked(api.updatePrescriptionReview).mockImplementation(async (_id, payload) => ({ ...review, revision: 2, reviewed_data: payload.reviewed_data! }));
  open();
  fireEvent.click(await screen.findByRole("button", { name: "Apply suggestion to form" }));
  expect(screen.getByText("Unsaved changes")).toBeTruthy();
  expect(api.updatePrescriptionReview).not.toHaveBeenCalled();
  expect(api.approvePrescriptionReview).not.toHaveBeenCalled();
  expect(api.publishPrescriptionReview).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
  await waitFor(() => expect(api.updatePrescriptionReview).toHaveBeenCalledTimes(1));
  const payload = vi.mocked(api.updatePrescriptionReview).mock.calls[0][1];
  const record = payload.reviewed_data!.observations[0].histopathologies[0];
  expect(record.values.biopsy_date).toBe("2020-01-02");
  expect(record.extracted_values?.biopsy_date).toBe("Invalid original");
  expect(payload.expected_revision).toBe(1);
});

function newerExtraction() {
  review.reviewed_data.patient.match_status = "unresolved";
  review.created_at = "2026-01-01T00:00:00Z";
  review.changes = [];
  vi.mocked(api.fetchPrescriptionDocument).mockResolvedValue({ id: 1, original_filename: "synthetic.pdf", file: "/synthetic.pdf", status: "ready_for_review", extraction_runs: [{ id: 7, status: "completed", created_at: "2026-01-02T00:00:00Z", structured_data: {} }], review } as unknown as PrescriptionDocument);
}

it("loads a newer extraction into the actual form only after explicit action", async () => {
  newerExtraction();
  const next = structuredClone(review.reviewed_data); next.patient.values.name = "New extracted synthetic";
  vi.mocked(api.loadLatestPrescriptionExtraction).mockResolvedValue({ ...review, revision: 2, reviewed_data: next });
  open();
  const load = await screen.findByRole("button", { name: "Load latest extraction" });
  expect(api.loadLatestPrescriptionExtraction).not.toHaveBeenCalled();
  fireEvent.click(load);
  await waitFor(() => expect(screen.getByRole("textbox", { name: "Patient name" })).toHaveProperty("value", "New extracted synthetic"));
  expect(api.loadLatestPrescriptionExtraction).toHaveBeenCalledWith(1, 1, 7);
  expect(api.approvePrescriptionReview).not.toHaveBeenCalled();
  expect(api.publishPrescriptionReview).not.toHaveBeenCalled();
});

it("protects unsaved form edits from extraction refresh", async () => {
  newerExtraction(); open();
  const load = await screen.findByRole("button", { name: "Load latest extraction" });
  fireEvent.change(screen.getByRole("textbox", { name: "Patient name" }), { target: { value: "Unsaved synthetic" } });
  expect(load).toHaveProperty("disabled", true);
  expect(api.loadLatestPrescriptionExtraction).not.toHaveBeenCalled();
});
