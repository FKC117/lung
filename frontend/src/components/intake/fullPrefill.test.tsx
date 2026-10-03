// @vitest-environment jsdom
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render } from "@testing-library/react";
import { ClinicalSectionFields } from "./ClinicalSectionFields";
import { observationCollections } from "./draftWorkspace";
import { observationFieldSchemas, recordReady, createBlankRecord } from "./observationFieldSchema";
import type { EntryOption, PrescriptionDraftRecord } from "../../api";
afterEach(cleanup);
describe("actual form prefill across every clinical section", () => {
  for (const collection of observationCollections) it(`prefills and shows originals for ${collection}`, () => {
    const fields = observationFieldSchemas[collection].fields;
    const values: Record<string, unknown> = {};
    const originals: Record<string, unknown> = {};
    const resolutions: PrescriptionDraftRecord["resolutions"] = {};
    const catalog: Record<string, EntryOption[]> = {};
    for (const field of fields) {
      let value: unknown = field.type === "number" ? 12 : field.type === "boolean" ? false : field.type === "date" ? "2020-01-02" : field.type === "datetime-local" ? "2020-01-02T03:04" : field.choices?.[0]?.value ?? `Synthetic ${field.key}`;
      if (field.resource) {
        value = field.multiple ? [7] : 7;
        catalog[field.resource] = [{ id: 7, display: "Synthetic choice", name: "Synthetic choice" }];
        resolutions[field.key] = { status: "resolved", resource: field.resource, raw_value: "Synthetic original choice", option_id: field.multiple ? null : 7, ...(field.multiple ? { option_ids: [7] } : {}), match_method: "exact_name", candidates: [], reason: "" };
      }
      values[field.key] = value;
      originals[field.key] = { value: `Original ${field.key}`, source_text: "Synthetic source", page: 1 };
    }
    const { container } = render(<ClinicalSectionFields fields={fields} values={values} extractedValues={originals} resolutions={resolutions} catalog={catalog} onChange={() => undefined} />);
    for (const field of fields) {
      const shell = container.querySelector(`[data-clinical-field="${field.key}"]`)!;
      expect(shell.querySelector(".clinical-extracted-value")?.textContent).toContain(`Original ${field.key}`);
      const input = shell.querySelector("input,select,textarea") as HTMLInputElement | HTMLSelectElement;
      expect(input).toBeTruthy();
      if (!field.readOnly && field.type !== "derived") expect(input.value).toBe(String(field.multiple ? 7 : values[field.key]));
    }
  });
  it("keeps record uncertainty blocking while optional blanks remain ready", () => {
    const optional = createBlankRecord("histopathologies");
    optional.values.report_summary = "   ";
    expect(recordReady("histopathologies", optional)).toBe(true);
    optional.state = "unresolved";
    expect(recordReady("histopathologies", optional)).toBe(false);
    optional.state = "edited";
    optional.resolutions.histopathology_type = { status: "unresolved", resource: "histopathology-types", raw_value: "Synthetic", option_id: null, match_method: null, candidates: [], reason: "Synthetic exception" };
    expect(recordReady("histopathologies", optional)).toBe(false);
  });
});
