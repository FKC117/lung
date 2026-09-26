import type { EntryOption, PrescriptionDraftRecord } from "../../api";
import { IntakeSelectField, IntakeTextArea, IntakeTextField } from "./SharedIntakeFields";
import { manualFieldKey, type ClinicalFieldDefinition } from "./observationFieldSchema";

type Catalog = Record<string, EntryOption[]>;
type Resolution = PrescriptionDraftRecord["resolutions"][string];

export interface ClinicalSectionFieldsProps {
  fields: readonly ClinicalFieldDefinition[];
  values: Record<string, unknown>;
  catalog?: Catalog;
  resolutions?: PrescriptionDraftRecord["resolutions"];
  binding?: "canonical" | "manual";
  disabled?: boolean;
  group?: ClinicalFieldDefinition["group"];
  onChange: (field: ClinicalFieldDefinition, value: unknown, options?: EntryOption[]) => void;
}

function optionIds(value: unknown, resolution: Resolution | undefined) {
  if (resolution?.option_ids) return resolution.option_ids.map(String);
  if (Array.isArray(value)) return value.filter((item) => Number.isInteger(Number(item))).map(String);
  return [];
}

function derivedValue(field: ClinicalFieldDefinition, values: Record<string, unknown>, catalog: Catalog, binding: "canonical" | "manual", resolutions: PrescriptionDraftRecord["resolutions"]) {
  const get = (key: string) => values[key];
  const numeric = (value: unknown) => { const parsed = Number(value); return Number.isFinite(parsed) && parsed > 0 ? parsed : null; };
  if (field.key === "bmi" || field.key === "bsa") {
    const height = numeric(get("height_cm")); const weight = numeric(get("weight_kg"));
    if (!height || !weight) return "";
    return field.key === "bmi" ? (weight / ((height / 100) ** 2)).toFixed(2) : Math.sqrt((height * weight) / 3600).toFixed(2);
  }
  if (field.key === "unit") {
    const markerKey = binding === "manual" ? "marker_name" : "marker";
    const markerId = binding === "canonical" ? resolutions.marker?.option_id : get(markerKey);
    const marker = catalog["cancer-marker-names"]?.find((option) => String(option.id) === String(markerId ?? ""));
    return String(marker?.unit ?? "");
  }
  if (field.key === "planned_total_dose_cgy") {
    const dose = numeric(get(binding === "manual" ? "fraction_dose" : "dose_per_fraction_cgy"));
    const count = numeric(get(binding === "manual" ? "fraction_count" : "planned_fractions"));
    return dose && count ? String(dose * count) : "";
  }
  if (field.key === "delivered_total_dose_cgy") {
    const dose = numeric(get(binding === "manual" ? "fraction_dose" : "dose_per_fraction_cgy"));
    const count = numeric(get("completed_fractions"));
    return dose && count ? String(dose * count) : "";
  }
  return String(get(binding === "manual" ? manualFieldKey(field) : field.key) ?? "");
}

export function ClinicalSectionFields({ fields, values, catalog = {}, resolutions = {}, binding = "canonical", disabled, group, onChange }: ClinicalSectionFieldsProps) {
  return <div className="entry-grid" data-clinical-schema-binding={binding}>
    {fields.filter((field) => !group || field.group === group).map((field) => {
      const valueKey = binding === "manual" ? manualFieldKey(field) : field.key;
      const raw = values[valueKey];
      const resolution = resolutions[field.key];
      if (field.readOnly || field.type === "derived") return <IntakeTextField key={field.key} label={field.label} value={derivedValue(field, values, catalog, binding, resolutions)} onChange={() => undefined} readOnly disabled={disabled} />;
      if ((field.multiple || (binding === "manual" && field.manualMultiple)) && field.resource) {
        const selected = optionIds(raw, resolution);
        return <label className="filter-field entry-span-full" key={field.key} data-clinical-field={field.key}><span>{field.label}{field.required ? " *" : ""}</span><select multiple className="filter-select entry-multiselect" disabled={disabled} value={selected} onChange={(event) => { const ids = Array.from(event.currentTarget.selectedOptions).map((option) => Number(option.value)); const options = (catalog[field.resource ?? ""] ?? []).filter((option) => ids.includes(option.id)); onChange(field, ids, options); }}>{(catalog[field.resource] ?? []).map((option) => <option key={option.id} value={option.id}>{option.name ?? option.display}</option>)}</select></label>;
      }
      if (field.resource) {
        const options = catalog[field.resource] ?? [];
        const selected = binding === "canonical" ? resolution?.option_id ?? "" : String(raw ?? "");
        return <IntakeSelectField key={field.key} label={field.label} required={field.required} disabled={disabled} options={options} value={selected} placeholder={raw && binding === "canonical" ? String(raw) : `Select ${field.label.toLowerCase()}`} onChange={(value, option) => onChange(field, option ? option.id : value, option ? [option] : [])} />;
      }
      if (field.type === "status" || field.type === "boolean") {
        const choices = field.type === "boolean" ? [{ value: "true", label: "Yes" }, { value: "false", label: "No" }] : field.choices ?? [];
        return <label className="filter-field" key={field.key} data-clinical-field={field.key}><span>{field.label}{field.required ? " *" : ""}</span><select className="filter-select" disabled={disabled} value={String(raw ?? "")} onChange={(event) => onChange(field, field.type === "boolean" ? event.target.value === "true" : event.target.value)}><option value="">Select…</option>{choices.map((choice) => <option key={choice.value} value={choice.value}>{choice.label}</option>)}</select></label>;
      }
      if (field.type === "textarea") return <IntakeTextArea key={field.key} label={field.label} disabled={disabled} value={String(raw ?? "")} onChange={(value) => onChange(field, value)} />;
      return <IntakeTextField key={field.key} label={field.label} type={field.type} required={field.required} disabled={disabled} value={String(raw ?? "")} onChange={(value) => onChange(field, value)} />;
    })}
  </div>;
}
