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

const courseStatuses = [{ value: "planned", label: "Planned" }, { value: "active", label: "Active" }, { value: "completed", label: "Completed" }, { value: "stopped", label: "Stopped" }, { value: "held", label: "Held" }] as const;
const administrationStatuses = [{ value: "planned", label: "Planned" }, { value: "given", label: "Given" }, { value: "delayed", label: "Delayed" }, { value: "held", label: "Held" }, { value: "cancelled", label: "Cancelled" }] as const;
const surgeryStatuses = [{ value: "planned", label: "Planned" }, { value: "performed", label: "Performed" }, { value: "cancelled", label: "Cancelled" }] as const;
const radiotherapyStatuses = [...courseStatuses, { value: "cancelled", label: "Cancelled" }] as const;
const assessmentTimepoints = [{ value: "baseline", label: "Baseline" }, { value: "on_treatment", label: "On treatment" }, { value: "post_treatment", label: "Post treatment" }, { value: "confirmatory", label: "Confirmatory" }] as const;

export const anthropometrySectionSchema: SectionSchema = {
  label: "Anthropometry",
  fields: [
    { key: "height_cm", label: "Height (cm)", type: "number" },
    { key: "weight_kg", label: "Weight (kg)", type: "number" },
    { key: "bmi", label: "BMI", type: "derived", readOnly: true },
    { key: "bsa", label: "BSA", type: "derived", readOnly: true },
  ],
};

export const observationFieldSchemas: Record<ObservationCollection, SectionSchema> = {
  comorbidities: { label: "Comorbidities", fields: [
    { key: "comorbidity", label: "Comorbidity", resource: "comorbidities", required: true },
    { key: "diagnosed_on", label: "Diagnosed on", type: "date" },
    { key: "is_active", label: "Active", type: "boolean" },
    { key: "notes", label: "Notes", type: "textarea" },
  ] },
  diagnoses: { label: "Diagnosis", fields: [
    { key: "diagnosed_on", label: "Diagnosed on", type: "date" },
    { key: "disease_group", label: "Disease group", resource: "diagnosis-disease-groups" },
    { key: "disease_subgroup", label: "Disease subgroup", resource: "diagnosis-disease-subgroups" },
    { key: "primary_site", label: "Primary site", resource: "diagnosis-primary-sites" },
    { key: "laterality", label: "Laterality", resource: "diagnosis-lateralities" },
    { key: "metastatic_sites", label: "Metastatic sites", resource: "diagnosis-metastatic-sites", multiple: true },
    { key: "diagnosis_in_details", label: "Diagnosis details", type: "textarea" },
  ] },
  histopathologies: { label: "Histopathology", fields: [
    { key: "biopsy_date", label: "Biopsy date", type: "date" },
    { key: "report_date", label: "Report date", type: "date" },
    { key: "histopathology_details", label: "Histopathology details", resource: "histopathology-details" },
    { key: "histopathology_type", label: "Histopathology type", resource: "histopathology-types" },
    { key: "histopathology_site", label: "Histopathology site", resource: "histopathology-sites" },
    { key: "histopathology_grade", label: "Histopathology grade", resource: "histopathology-grades" },
    { key: "report_summary", label: "Report summary", type: "textarea" },
    { key: "any_known_mutation", label: "Any known mutation", type: "textarea", manualKey: "any_known_mutations", manualLabel: "Known mutations" },
  ] },
  ihc_results: { label: "IHC results", fields: [
    { key: "tested_at", label: "Tested at", type: "date" },
    { key: "marker", label: "Marker", resource: "ihc-cycles", required: true, manualKey: "cycle" },
    { key: "result", label: "Result", resource: "ihc-cycle-results", required: true },
    { key: "percentage", label: "Percentage", type: "number" },
    { key: "notes", label: "Notes", type: "textarea" },
  ] },
  pathological_staging_results: { label: "Pathological staging details", fields: [
    { key: "assessed_at", label: "Assessed at", type: "date", manualKey: "tested_at" },
    { key: "feature", label: "Feature", resource: "ihc-staging-cycles", required: true, manualKey: "cycle" },
    { key: "result", label: "Result", resource: "ihc-staging-cycle-results", required: true },
    { key: "percentage", label: "Percentage", type: "number" },
    { key: "notes", label: "Notes", type: "textarea" },
  ] },
  clinical_tnm_stagings: { label: "Clinical TNM", fields: [
    { key: "t", label: "T", resource: "tnm-t" }, { key: "n", label: "N", resource: "tnm-n" },
    { key: "m", label: "M", resource: "tnm-m" }, { key: "stage", label: "Stage", resource: "tnm-stages" },
    { key: "staged_on", label: "Staged on", type: "date", manualKey: "staged_at" }, { key: "notes", label: "Notes", type: "textarea" },
  ] },
  pathological_tnm_stagings: { label: "Pathological TNM", fields: [
    { key: "t", label: "T", resource: "tnm-t" }, { key: "n", label: "N", resource: "tnm-n" },
    { key: "m", label: "M", resource: "tnm-m" }, { key: "stage", label: "Stage", resource: "tnm-stages" },
    { key: "staged_on", label: "Staged on", type: "date", manualKey: "staged_at" }, { key: "notes", label: "Notes", type: "textarea" },
  ] },
  molecular_tests: { label: "Molecular pathology", fields: [
    { key: "panel", label: "Panel", resource: "molecular-panels", group: "record", persisted: false },
    { key: "panel_version", label: "Panel version", resource: "molecular-panel-versions", group: "record" },
    { key: "method", label: "Method", resource: "molecular-methods", group: "record" },
    { key: "specimen", label: "Specimen", resource: "molecular-specimens", group: "record" },
    { key: "specimen_collected_on", label: "Specimen collected on", type: "date", group: "record" },
    { key: "tested_on", label: "Tested on", type: "date", manualKey: "tested_at", group: "record" },
    { key: "reported_on", label: "Reported on", type: "date", group: "record" },
    { key: "qc_status", label: "QC status", type: "status", choices: [{ value: "pending", label: "Pending" }, { value: "passed", label: "Passed" }, { value: "partial", label: "Partially passed" }, { value: "failed", label: "Failed" }], group: "record" },
    { key: "laboratory", label: "Laboratory", group: "record" }, { key: "accession_number", label: "Accession number", group: "record" },
    { key: "notes", label: "Test notes", type: "textarea", group: "record" },
    { key: "panel_target", label: "Panel target", resource: "molecular-panel-targets", group: "result" },
    { key: "gene", label: "Gene", resource: "molecular-genes", required: true, group: "result" },
    { key: "exon", label: "Exon", resource: "molecular-exons", group: "result" },
    { key: "alteration_type", label: "Alteration type", resource: "molecular-alteration-types", required: true, group: "result" },
    { key: "result", label: "Result", resource: "molecular-results", required: true, group: "result" },
    { key: "partner_gene", label: "Partner gene", resource: "molecular-genes", group: "result" },
    { key: "clinical_significance", label: "Clinical significance", resource: "molecular-clinical-significances", group: "result" },
    { key: "dna_change", label: "DNA change", group: "result" }, { key: "protein_change", label: "Protein change", group: "result" },
    { key: "common_name", label: "Common name", group: "result" }, { key: "variant_allele_frequency", label: "Variant allele frequency", type: "number", group: "result" },
    { key: "copy_number", label: "Copy number", type: "number", group: "result" },
    { key: "origin", label: "Origin", type: "status", choices: [{ value: "explicit", label: "Explicitly reported" }, { value: "derived", label: "Automatically derived" }, { value: "manual", label: "Manually entered" }], group: "result" },
    { key: "result_notes", label: "Result notes", type: "textarea", manualKey: "notes", group: "result" },
  ] },
  cancer_markers: { label: "Cancer markers", fields: [
    { key: "marker", label: "Marker", resource: "cancer-marker-names", required: true, manualKey: "marker_name" },
    { key: "value", label: "Value", type: "number", manualKey: "marker_value" },
    { key: "unit", label: "Unit", type: "derived", readOnly: true, manualKey: "marker_unit" },
    { key: "tested_on", label: "Tested on", type: "date", manualKey: "tested_at" }, { key: "notes", label: "Notes", type: "textarea" },
  ] },
  treatments: { label: "Treatment", fields: [
    { key: "modality", label: "Modality", resource: "treatment-modalities", required: true, manualKey: "modalities", manualMultiple: true, group: "record" },
    { key: "line_of_treatment", label: "Line of treatment", resource: "lines-of-treatment", group: "record" },
    { key: "protocol", label: "Protocol", resource: "treatment-protocols", required: true, manualKey: "treatment_protocol", group: "record" },
    { key: "started_on", label: "Started on", type: "date", manualKey: "started_at", group: "record" }, { key: "ended_on", label: "Ended on", type: "date", manualKey: "ended_at", group: "record" },
    { key: "status", label: "Course status", type: "status", choices: courseStatuses, group: "record" },
    { key: "reason_for_stopping", label: "Reason for stopping", type: "textarea", group: "record" }, { key: "notes", label: "Course notes", type: "textarea", manualKey: "course_notes", group: "record" },
    { key: "drug", label: "Drug", resource: "treatment-drugs", required: true, group: "administration" },
    { key: "administered_on", label: "Administered on", type: "date", group: "administration" }, { key: "cycle_number", label: "Cycle number", type: "number", group: "administration" },
    { key: "day_number", label: "Day number", type: "number", group: "administration" }, { key: "dose", label: "Dose", type: "number", group: "administration" },
    { key: "dose_unit", label: "Dose unit", group: "administration" }, { key: "administration_status", label: "Administration status", type: "status", choices: administrationStatuses, manualKey: "status", group: "administration" },
    { key: "administration_notes", label: "Administration notes", type: "textarea", manualKey: "notes", group: "administration" },
  ] },
  surgeries: { label: "Surgery", fields: [
    { key: "modality", label: "Surgery modality", resource: "surgery-modalities", required: true, manualKey: "surgery_modality" },
    { key: "laterality", label: "Surgical laterality", resource: "surgery-lateralities", manualKey: "lateralities", manualMultiple: true },
    { key: "surgery_date", label: "Surgery date", type: "date" }, { key: "status", label: "Surgery status", type: "status", choices: surgeryStatuses },
    { key: "procedure_details", label: "Procedure details", type: "textarea" }, { key: "operative_findings", label: "Operative findings", type: "textarea" },
    { key: "complications", label: "Complications", type: "textarea" }, { key: "notes", label: "Surgery notes", type: "textarea" },
  ] },
  radiotherapies: { label: "Radiotherapy", fields: [
    { key: "site", label: "Radiotherapy site", resource: "radiotherapy-sites", required: true, manualKey: "sites", manualMultiple: true },
    { key: "intent", label: "Radiotherapy intent", resource: "radiotherapy-intents", required: true, manualKey: "radiotherapy_intent" },
    { key: "modality", label: "Radiotherapy modality", resource: "radiotherapy-modalities", required: true, manualKey: "modalities", manualMultiple: true },
    { key: "started_on", label: "Radiotherapy start", type: "date", manualKey: "started_at" }, { key: "ended_on", label: "Radiotherapy end", type: "date", manualKey: "ended_at" },
    { key: "dose_per_fraction_cgy", label: "Dose per fraction (cGy)", type: "number", manualKey: "fraction_dose" },
    { key: "planned_fractions", label: "Planned fractions", type: "number", manualKey: "fraction_count" }, { key: "completed_fractions", label: "Completed fractions", type: "number" },
    { key: "planned_total_dose_cgy", label: "Planned total dose (cGy)", type: "derived", readOnly: true, manualKey: "total_dose" },
    { key: "delivered_total_dose_cgy", label: "Delivered total dose (cGy)", type: "derived", readOnly: true },
    { key: "status", label: "Radiotherapy status", type: "status", choices: radiotherapyStatuses },
    { key: "reason_for_stopping", label: "Reason for stopping", type: "textarea" }, { key: "notes", label: "Radiotherapy notes", type: "textarea" },
  ] },
  recist_assessments: { label: "RECIST", fields: [
    { key: "assessed_on", label: "Assessed on", type: "date", required: true, manualKey: "assessed_at" }, { key: "timepoint", label: "Timepoint", type: "status", choices: assessmentTimepoints },
    { key: "target_lesion", label: "Target lesion", resource: "recist-target-lesions" }, { key: "non_target_lesion", label: "Non-target lesion", resource: "recist-non-target-lesions" },
    { key: "new_lesion", label: "New lesion", resource: "recist-new-lesions" }, { key: "overall_response", label: "Overall response", resource: "recist-response-results", required: true, manualKey: "response_result" },
    { key: "estimation_method", label: "Estimation method", resource: "response-estimation-methods" }, { key: "notes", label: "Notes", type: "textarea" },
  ] },
  irecist_assessments: { label: "iRECIST", fields: [
    { key: "assessed_on", label: "Assessed on", type: "date", required: true, manualKey: "assessed_at" }, { key: "timepoint", label: "Timepoint", type: "status", choices: assessmentTimepoints },
    { key: "target_lesion", label: "Target lesion", resource: "irecist-target-lesions" }, { key: "non_target_lesion", label: "Non-target lesion", resource: "irecist-non-target-lesions" },
    { key: "new_lesion", label: "New lesion", resource: "irecist-new-lesions" }, { key: "overall_response", label: "Overall response", resource: "irecist-response-results", required: true, manualKey: "response_result" },
    { key: "estimation_method", label: "Estimation method", resource: "response-estimation-methods" }, { key: "notes", label: "Notes", type: "textarea" },
  ] },
  pathological_responses: { label: "Pathological response", fields: [
    { key: "assessed_on", label: "Assessed on", type: "date", required: true, manualKey: "assessed_at" }, { key: "timepoint", label: "Timepoint", type: "status", choices: assessmentTimepoints },
    { key: "response_category", label: "Response category", resource: "pathological-response-categories" },
    { key: "residual_viable_tumor_percentage", label: "Residual viable tumour (%)", type: "number" },
    { key: "tumor_regression_grade", label: "Tumour regression grade", resource: "tumor-regression-grades" },
    { key: "estimation_method", label: "Estimation method", resource: "response-estimation-methods" }, { key: "notes", label: "Notes", type: "textarea" },
  ] },
  progression_records: { label: "Disease progression", fields: [
    { key: "status", label: "Progression status", resource: "disease-progression-statuses", required: true },
    { key: "assessed_on", label: "Assessed on", type: "date", required: true }, { key: "progression_date", label: "Progression date", type: "date" },
    { key: "progression_sites", label: "Progression sites", resource: "progression-sites", multiple: true },
    { key: "estimation_method", label: "Estimation method", resource: "response-estimation-methods" }, { key: "notes", label: "Progression notes", type: "textarea" },
  ] },
  survival_records: { label: "Survival follow-up", fields: [
    { key: "status", label: "Survival status", resource: "survival-statuses", required: true },
    { key: "followed_up_on", label: "Followed up on", type: "date", required: true }, { key: "death_date", label: "Death date", type: "date" },
    { key: "cause_of_death", label: "Cause of death" }, { key: "notes", label: "Follow-up notes", type: "textarea" },
  ] },
};

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
  return requiredReady && Object.values(record.resolutions).every((resolution) => resolution.status === "resolved");
}

export const authoritativeOptionResources = Array.from(new Set([
  ...Object.values(observationFieldSchemas).flatMap((section) => section.fields.flatMap((field) => field.resource ? [field.resource] : [])),
  "sexes", "districts", "thanas", "blood-groups", "economic-statuses", "patient-types",
]));
