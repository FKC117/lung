import type { PrescriptionDraftRecord } from "../../api";
import { draftTempId, type ObservationCollection } from "./draftWorkspace";

export type ClinicalFieldDefinition = {
  key: string;
  label: string;
  type?: "text" | "number" | "date" | "datetime-local" | "textarea" | "boolean" | "status" | "derived";
  resource?: string;
  required?: boolean;
  multiple?: boolean;
  manualMultiple?: boolean;
  readOnly?: boolean;
  manualKey?: string;
  manualLabel?: string;
  choices?: readonly { value: string; label: string }[];
  group?: "record" | "result" | "administration";
  persisted?: boolean;
};

type SectionSchema = { label: string; fields: readonly ClinicalFieldDefinition[] };

import fieldContract from "../../../../registry/prescriptions/contracts/fields.json";

export const anthropometrySectionSchema = fieldContract.anthropometry as SectionSchema;
export const observationFieldSchemas = fieldContract.collections as unknown as Record<ObservationCollection, SectionSchema>;
export const patientFieldSchema = fieldContract.patient.fields as ClinicalFieldDefinition[];
export const fieldDependencies = fieldContract.dependencies as Record<string, Record<string, Record<string, string>>>;

export function manualFieldKey(field: ClinicalFieldDefinition) { return field.manualKey ?? field.key; }

export function createBlankRecord(collection: ObservationCollection): PrescriptionDraftRecord {
  return {
    temp_id: draftTempId(collection), state: "edited",
    values: Object.fromEntries(observationFieldSchemas[collection].fields.filter((field) => !field.readOnly).map((field) => [field.key, field.multiple ? [] : field.type === "boolean" ? true : ""])),
    resolutions: {}, evidence_refs: [],
  };
}

function hasValue(value: unknown) { return Array.isArray(value) ? value.length > 0 : value !== undefined && value !== null && String(value).trim() !== ""; }

export function recordReady(collection: ObservationCollection, record: PrescriptionDraftRecord) {
  const requiredReady = observationFieldSchemas[collection].fields.filter((field) => field.required).every((field) => hasValue(record.values[field.key]));
  const selectionsReady = observationFieldSchemas[collection].fields.every((field) => !hasValue(record.values[field.key]) ||
    (field.persisted !== false && (!field.resource || record.resolutions[field.key]?.status === "resolved")));
  return record.state !== "unresolved" && requiredReady && selectionsReady && Object.values(record.resolutions).every((resolution) => resolution.status === "resolved");
}

export const authoritativeOptionResources = Array.from(new Set([
  ...Object.values(observationFieldSchemas).flatMap((section) => section.fields.flatMap((field) => field.resource ? [field.resource] : [])),
  "sexes", "districts", "thanas", "blood-groups", "economic-statuses", "patient-types",
]));
