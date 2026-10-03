// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PreviewDraftAction } from "./PreviewDraftAction";
import { emptyObservation } from "./draftWorkspace";
import * as api from "../../api";
vi.mock("../../api", async (original) => ({ ...await original<typeof import("../../api")>(), fetchPrescriptionDocument: vi.fn(), loadLatestPrescriptionExtraction: vi.fn(), startPrescriptionReview: vi.fn(), fetchEntriesOptions: vi.fn(), updatePrescriptionReview: vi.fn() }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
it("saves existing mapped items without duplicating records or publishing", async () => {
 const observation = emptyObservation();
 observation.diagnoses = [{ temp_id: "record-one", state: "unresolved", values: { primary_site: "Lung" }, resolutions: {}, evidence_refs: [], extracted_values: { primary_site: "Lung" } }];
 const reviewed_data = { schema_version: 1, document_id: 1, patient: { match_status: "unresolved", patient_id: null, values: {} }, observations: [observation], unresolved_items: [], source_facts: [{ fact_id: "fact-one", source_path: "observations.0.diagnoses.0.primary_site", record_temp_id: "record-one", raw_value: "Lung", disposition: "mapped" }] } as api.LongitudinalIntakeDraft;
 const review = { revision: 3, status: "in_review", reviewed_data } as api.PrescriptionReview;
 vi.mocked(api.startPrescriptionReview).mockResolvedValue(review);
 vi.mocked(api.fetchPrescriptionDocument).mockResolvedValue({ review: null } as unknown as api.PrescriptionDocument);
 vi.mocked(api.fetchEntriesOptions).mockResolvedValue({});
 vi.mocked(api.updatePrescriptionReview).mockResolvedValue({ ...review, revision: 4 });
 render(<QueryClientProvider client={new QueryClient()}><PreviewDraftAction documentId={1} collection="diagnoses" eventIndex={0} /></QueryClientProvider>);
 expect(api.startPrescriptionReview).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole("button", { name: "Correct" }));
 fireEvent.click(await screen.findByRole("button", { name: "Correct — save to draft" }));
 await waitFor(() => expect(api.updatePrescriptionReview).toHaveBeenCalledTimes(1));
 const submitted = vi.mocked(api.updatePrescriptionReview).mock.calls[0][1];
 expect(submitted.expected_revision).toBe(3);
 expect(submitted.reviewed_data?.observations[0].diagnoses).toHaveLength(1);
 expect(await screen.findByText("Confirmed in draft")).toBeTruthy();
});
it("does not guess a source event when the saved draft has no mapped records", async () => {
 vi.mocked(api.startPrescriptionReview).mockResolvedValue({ status: "in_review", reviewed_data: { observations: [emptyObservation()], source_facts: [] } } as unknown as api.PrescriptionReview);
 render(<QueryClientProvider client={new QueryClient()}><PreviewDraftAction documentId={1} collection="diagnoses" eventIndex={1} /></QueryClientProvider>);
 fireEvent.click(screen.getByRole("button", { name: "Correct" }));
 expect(await screen.findByRole("alert")).toHaveProperty("textContent", expect.stringContaining("No editable extraction"));
 expect(api.updatePrescriptionReview).not.toHaveBeenCalled();
});

it("shows existing-draft choices without starting or saving a review", async () => {
 const observation = emptyObservation();
 observation.diagnoses = [{ temp_id: "mapped", state: "unresolved", values: {}, resolutions: {}, evidence_refs: [] }];
 const review = { revision: 2, status: "in_review", reviewed_data: { observations: [observation], source_facts: [{ fact_id: "mapped", source_path: "observations.0.diagnoses.0.primary_site", record_temp_id: "mapped", raw_value: "Lung", disposition: "mapped" }] } } as unknown as api.PrescriptionReview;
 vi.mocked(api.fetchPrescriptionDocument).mockResolvedValue({ review } as unknown as api.PrescriptionDocument);
 vi.mocked(api.fetchEntriesOptions).mockResolvedValue({});
 render(<QueryClientProvider client={new QueryClient()}><PreviewDraftAction documentId={1} collection="diagnoses" eventIndex={0} /></QueryClientProvider>);
 expect(await screen.findByRole("button", { name: "Correct — save to draft" })).toBeTruthy();
 expect(screen.getAllByRole("combobox").length).toBeGreaterThan(0);
 expect(api.startPrescriptionReview).not.toHaveBeenCalled();
 expect(api.updatePrescriptionReview).not.toHaveBeenCalled();
});

it("Modify replaces the segment preview with local fields", async () => {
 const observation = emptyObservation();
 observation.diagnoses = [{ temp_id: "mapped", state: "unresolved", values: { diagnosed_on: "2024-01-02" }, resolutions: {}, evidence_refs: [] }];
 const review = { revision: 2, status: "in_review", reviewed_data: { observations: [observation], source_facts: [{ fact_id: "mapped", source_path: "observations.0.diagnoses.0.diagnosed_on", record_temp_id: "mapped", raw_value: "2024-01-02", disposition: "mapped" }] } } as unknown as api.PrescriptionReview;
 vi.mocked(api.fetchPrescriptionDocument).mockResolvedValue({ review } as unknown as api.PrescriptionDocument);
 vi.mocked(api.fetchEntriesOptions).mockResolvedValue({});
 render(<QueryClientProvider client={new QueryClient()}><PreviewDraftAction documentId={1} collection="diagnoses" eventIndex={0}>{(editing) => editing ? null : <p>Original segment preview</p>}</PreviewDraftAction></QueryClientProvider>);
 await screen.findByRole("button", { name: "Correct — save to draft" });
 fireEvent.click(screen.getByRole("button", { name: "Modify" }));
 expect(screen.queryByText("Original segment preview")).toBeNull();
 expect(screen.getByLabelText(/Diagnosed on/i)).toBeTruthy();
 expect(api.updatePrescriptionReview).not.toHaveBeenCalled();
});
it("opens latest mapped segment without loading it until Save", async () => {
 const observation = emptyObservation();
 observation.diagnoses = [{ temp_id: "latest", state: "unresolved", values: {}, resolutions: {}, evidence_refs: [] }];
 const latest = { observations: [observation], source_facts: [{ fact_id: "latest", source_path: "observations.0.diagnoses.0.primary_site", record_temp_id: "latest", raw_value: "Lung", disposition: "mapped" }] } as unknown as api.LongitudinalIntakeDraft;
 const old = { revision: 1, status: "in_review", reviewed_data: { observations: [emptyObservation()], source_facts: [] } } as unknown as api.PrescriptionReview;
 vi.mocked(api.fetchPrescriptionDocument).mockResolvedValue({ review: old, extraction_runs: [{ id: 10, status: "completed", structured_data: { canonical_draft: latest } }] } as unknown as api.PrescriptionDocument);
 vi.mocked(api.startPrescriptionReview).mockResolvedValue(old);
 vi.mocked(api.fetchEntriesOptions).mockResolvedValue({});
 vi.mocked(api.loadLatestPrescriptionExtraction).mockResolvedValue({ ...old, revision: 2, reviewed_data: latest });
 vi.mocked(api.updatePrescriptionReview).mockResolvedValue({ ...old, revision: 3, reviewed_data: latest });
 render(<QueryClientProvider client={new QueryClient()}><PreviewDraftAction documentId={1} collection="diagnoses" eventIndex={0} /></QueryClientProvider>);
 fireEvent.click(screen.getByRole("button", { name: "Modify" }));
 await screen.findByRole("button", { name: "Save modifications" });
 expect(api.loadLatestPrescriptionExtraction).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole("button", { name: "Save modifications" }));
 await waitFor(() => expect(api.updatePrescriptionReview).toHaveBeenCalledTimes(1));
 expect(api.loadLatestPrescriptionExtraction).toHaveBeenCalledWith(1, 1, 10);
 expect(vi.mocked(api.updatePrescriptionReview).mock.calls[0][1].expected_revision).toBe(2);
});
