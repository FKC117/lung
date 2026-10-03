// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { ClinicalSectionFields } from "./ClinicalSectionFields";
afterEach(cleanup);

describe("unresolved controlled-field clearing", () => {
  it("clears an empty-catalog prefill while original extracted text remains visible", () => {
    const onChange = vi.fn();
    const values = { histopathology_type: "Synthetic unknown histology" };
    render(<ClinicalSectionFields fields={[{ key: "histopathology_type", label: "Histopathology type", resource: "histopathology-types" }]} values={values} extractedValues={values} onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "Clear histopathology type prefill" }));
    expect(onChange.mock.calls[0].slice(1)).toEqual(["", []]);
    expect(screen.getByText(/Synthetic unknown histology/)).toBeTruthy();
    expect(values.histopathology_type).toBe("Synthetic unknown histology");
  });

  it("clears unmatched multiselect text using an empty canonical list", () => {
    const onChange = vi.fn();
    render(<ClinicalSectionFields fields={[{ key: "sites", label: "Sites", resource: "synthetic-sites", multiple: true }]} values={{ sites: ["Synthetic site"] }} onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "Clear sites prefill" }));
    expect(onChange.mock.calls[0].slice(1)).toEqual([[], []]);
  });

  it("does not offer the action for manual entry or an already cleared field", () => {
    render(<ClinicalSectionFields fields={[{ key: "type", label: "Type", resource: "synthetic-types" }]} values={{ type: "Synthetic" }} binding="manual" onChange={() => undefined} />);
    expect(screen.queryByRole("button", { name: /Clear .* prefill/ })).toBeNull();
  });

  it("protects resolved selections and disables the action on a locked draft", () => {
    const field = { key: "type", label: "Type", resource: "synthetic-types" };
    const result = render(<ClinicalSectionFields fields={[field]} values={{ type: 1 }} resolutions={{ type: {
      status: "resolved", resource: "synthetic-types", raw_value: "Synthetic", option_id: 1, candidates: [], reason: "", match_method: "exact" } }} onChange={() => undefined} />);
    expect(screen.queryByRole("button", { name: "Clear type prefill" })).toBeNull();
    result.rerender(<ClinicalSectionFields fields={[field]} values={{ type: "Synthetic" }} disabled onChange={() => undefined} />);
    expect((screen.getByRole("button", { name: "Clear type prefill" }) as HTMLButtonElement).disabled).toBe(true);
  });
});
