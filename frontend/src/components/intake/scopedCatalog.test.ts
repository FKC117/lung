import { describe, expect, it } from "vitest";
import { scopedCatalog } from "./ObservationFormSections";
import type { PrescriptionDraftRecord } from "../../api";

const record = (): PrescriptionDraftRecord => ({ temp_id: "synthetic", state: "edited", values: {}, resolutions: {}, evidence_refs: [] });
const selected = (id: number) => ({ status: "resolved" as const, resource: "synthetic", raw_value: "Synthetic", option_id: id, candidates: [], reason: "", match_method: "manual" });

describe("parent-scoped actual form catalogs", () => {
  it("requires all panel target parents and hides unrelated targets", () => {
    const item = record();
    const catalog = { "molecular-panel-targets": [{ id: 1, display: "Synthetic target", panel_version: 2, gene: 3, alteration_type: 4 }] };
    expect(scopedCatalog(item, catalog)["molecular-panel-targets"]).toEqual([]);
    item.resolutions = { panel_version: selected(2), gene: selected(3), alteration_type: selected(4) };
    expect(scopedCatalog(item, catalog)["molecular-panel-targets"]).toHaveLength(1);
    item.resolutions.gene = selected(5);
    expect(scopedCatalog(item, catalog)["molecular-panel-targets"]).toEqual([]);
  });
  it("limits protocol drugs and membership choices to resolved parents", () => {
    const item = record();
    item.values.protocol = "Synthetic protocol";
    const catalog = { "treatment-drugs": [{ id: 2, display: "Synthetic allowed" }, { id: 3, display: "Synthetic other" }],
      "treatment-protocol-drugs": [{ id: 8, display: "Synthetic membership", protocol: 1, drug: 2 }] };
    expect(scopedCatalog(item, catalog)["treatment-drugs"]).toEqual([]);
    item.resolutions.protocol = selected(1);
    expect(scopedCatalog(item, catalog)["treatment-drugs"].map((item) => item.id)).toEqual([2]);
    expect(scopedCatalog(item, catalog)["treatment-protocol-drugs"]).toEqual([]);
    item.resolutions.drug = selected(2);
    expect(scopedCatalog(item, catalog)["treatment-protocol-drugs"]).toHaveLength(1);
    item.resolutions.protocol = selected(9);
    expect(scopedCatalog(item, catalog)["treatment-drugs"]).toEqual([]);
  });
});

