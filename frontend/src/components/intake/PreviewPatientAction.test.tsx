// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PreviewPatientAction } from "./PreviewPatientAction";
import * as api from "../../api";
vi.mock("../../api", async (original) => ({ ...await original<typeof import("../../api")>(), startPrescriptionReview: vi.fn(), fetchEntriesOptions: vi.fn(), updatePrescriptionReview: vi.fn() }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
it("confirms profile details without selecting a registry patient", async () => {
 const review = { revision: 2, status: "in_review", reviewed_data: { patient: { match_status: "unresolved", patient_id: null, values: { name: "Synthetic Person", age: 62 } }, observations: [] } } as unknown as api.PrescriptionReview;
 vi.mocked(api.startPrescriptionReview).mockResolvedValue(review);
 vi.mocked(api.fetchEntriesOptions).mockResolvedValue({});
 vi.mocked(api.updatePrescriptionReview).mockResolvedValue({ ...review, revision: 3 });
 render(<QueryClientProvider client={new QueryClient()}><PreviewPatientAction documentId={1} /></QueryClientProvider>);
 expect(api.startPrescriptionReview).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole("button", { name: "Correct — save to draft" }));
 await waitFor(() => expect(api.updatePrescriptionReview).toHaveBeenCalledTimes(1));
 const payload = vi.mocked(api.updatePrescriptionReview).mock.calls[0][1];
 expect(payload.expected_revision).toBe(2);
 expect(payload.reviewed_data?.patient.match_status).toBe("unresolved");
 expect(payload.reviewed_data?.patient.patient_id).toBeNull();
 expect(await screen.findByText("Confirmed in draft")).toBeTruthy();
});
it("opens inline fields and saves modifications", async () => {
 const review = { revision: 2, status: "in_review", reviewed_data: { patient: { match_status: "unresolved", patient_id: null, values: { name: "Synthetic Person" } }, observations: [] } } as unknown as api.PrescriptionReview;
 vi.mocked(api.startPrescriptionReview).mockResolvedValue(review);
 vi.mocked(api.fetchEntriesOptions).mockResolvedValue({});
 vi.mocked(api.updatePrescriptionReview).mockResolvedValue({ ...review, revision: 3 });
 render(<QueryClientProvider client={new QueryClient()}><PreviewPatientAction documentId={1} /></QueryClientProvider>);
 fireEvent.click(screen.getByRole("button", { name: "Modify" }));
 fireEvent.change(await screen.findByRole("textbox", { name: "Patient name" }), { target: { value: "Corrected Synthetic" } });
 fireEvent.click(screen.getByRole("button", { name: "Save modifications" }));
 await waitFor(() => expect(api.updatePrescriptionReview).toHaveBeenCalledTimes(1));
 expect(vi.mocked(api.updatePrescriptionReview).mock.calls[0][1].reviewed_data?.patient.values.name).toBe("Corrected Synthetic");
});
