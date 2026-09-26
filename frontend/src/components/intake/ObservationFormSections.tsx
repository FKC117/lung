import type { ReactNode } from "react";
import { CheckCircle2, Plus, Trash2 } from "lucide-react";
import type { EntryOption, PrescriptionDraftRecord, PrescriptionObservationDraft } from "../../api";
import { observationCollections, type ObservationCollection } from "./draftWorkspace";

type Catalog = Record<string, EntryOption[]>;
const labels: Record<ObservationCollection, string> = {
  comorbidities: "Comorbidities", diagnoses: "Diagnosis", histopathologies: "Histopathology", ihc_results: "IHC results",
  pathological_staging_results: "Pathological staging details", clinical_tnm_stagings: "Clinical TNM", pathological_tnm_stagings: "Pathological TNM",
  molecular_tests: "Molecular pathology", cancer_markers: "Cancer markers", treatments: "Treatment protocols", surgeries: "Surgery",
  radiotherapies: "Radiotherapy", recist_assessments: "RECIST", irecist_assessments: "iRECIST", pathological_responses: "Pathological response",
  progression_records: "Disease progression", survival_records: "Survival follow-up",
};
const optionFields: Record<string, string> = {
  comorbidity: "comorbidities", disease_group: "diagnosis-disease-groups", disease_subgroup: "diagnosis-disease-subgroups",
  primary_site: "diagnosis-primary-sites", laterality: "diagnosis-lateralities", histopathology_details: "histopathology-details",
  histopathology_type: "histopathology-types", histopathology_site: "histopathology-sites", histopathology_grade: "histopathology-grades",
  marker: "ihc-cycles", feature: "ihc-staging-cycles", t: "tnm-t", n: "tnm-n", m: "tnm-m", stage: "tnm-stages",
  method: "molecular-methods", specimen: "molecular-specimens", gene: "molecular-genes", exon: "molecular-exons",
  alteration_type: "molecular-alteration-types", clinical_significance: "molecular-clinical-significances", panel: "molecular-panels",
  panel_version: "molecular-panel-versions", panel_target: "molecular-panel-targets", marker_name: "cancer-marker-names",
  modality: "treatment-modalities", line_of_treatment: "lines-of-treatment", protocol: "treatment-protocols", drug: "treatment-drugs",
  site: "radiotherapy-sites", intent: "radiotherapy-intents", response_category: "pathological-response-categories",
  tumor_regression_grade: "tumor-regression-grades", estimation_method: "response-estimation-methods",
};
const collectionOptionFields: Partial<Record<ObservationCollection, Record<string, string>>> = {
  surgeries: { modality: "surgery-modalities", laterality: "surgery-lateralities" },
  radiotherapies: { modality: "radiotherapy-modalities", site: "radiotherapy-sites", intent: "radiotherapy-intents" },
  ihc_results: { result: "ihc-cycle-results", reported_result: "ihc-cycle-results" },
  pathological_staging_results: { result: "ihc-staging-cycle-results" },
  molecular_tests: { result: "molecular-results", reported_result: "molecular-results" },
  recist_assessments: { target_lesion: "recist-target-lesions", non_target_lesion: "recist-non-target-lesions", new_lesion: "recist-new-lesions", overall_response: "recist-response-results" },
  irecist_assessments: { target_lesion: "irecist-target-lesions", non_target_lesion: "irecist-non-target-lesions", new_lesion: "irecist-new-lesions", overall_response: "irecist-response-results" },
  progression_records: { status: "disease-progression-statuses" },
  survival_records: { status: "survival-statuses" },
};

export interface ObservationFormSectionsProps {
  observation?: PrescriptionObservationDraft;
  catalog?: Catalog;
  disabled?: boolean;
  selectedRecords?: Set<string>;
  onToggleRecord?: (collection: ObservationCollection, tempId: string) => void;
  onChange?: (observation: PrescriptionObservationDraft) => void;
  onMoveRecord?: (collection: ObservationCollection, tempId: string, targetId: string) => void;
  moveTargets?: Array<{ id: string; label: string }>;
  children?: ReactNode;
}

function stateReady(record: PrescriptionDraftRecord) {
  return Object.values(record.resolutions).every((resolution) => resolution.status === "resolved");
}

export function ObservationFormSections({ observation, catalog = {}, disabled, selectedRecords = new Set(), onToggleRecord, onChange, onMoveRecord, moveTargets = [], children }: ObservationFormSectionsProps) {
  if (!observation || !onChange) return <>{children}</>;
  const updateRecord = (collection: ObservationCollection, tempId: string, updater: (record: PrescriptionDraftRecord) => PrescriptionDraftRecord) => onChange({ ...observation, [collection]: observation[collection].map((record) => record.temp_id === tempId ? updater(record) : record) });
  const removeRecord = (collection: ObservationCollection, tempId: string) => onChange({ ...observation, [collection]: observation[collection].filter((record) => record.temp_id !== tempId) });
  const addRecord = (collection: ObservationCollection) => onChange({ ...observation, [collection]: [...observation[collection], { temp_id: `${collection}-${crypto.randomUUID()}`, state: "edited", values: {}, resolutions: {}, evidence_refs: [] }] });
  return <div className="intake-observation-form">
    <section className="panel entry-block intake-form-section"><div className="panel-heading"><div><p className="eyebrow">Observation-level draft</p><h3>Observation context</h3></div></div><div className="entry-grid">
      <label className="filter-field"><span>Observed at</span><input className="auth-input" type="datetime-local" disabled={disabled} value={observation.observed_at?.slice(0, 16) ?? ""} onChange={(event) => onChange({ ...observation, observed_at: event.target.value || null })} /></label>
      <label className="filter-field"><span>Prescription date</span><input className="auth-input" type="date" disabled={disabled} value={observation.prescription_date ?? ""} onChange={(event) => onChange({ ...observation, prescription_date: event.target.value || null })} /></label>
      <label className="filter-field"><span>Temporal context</span><select className="filter-select" disabled={disabled} value={observation.temporal_context} onChange={(event) => onChange({ ...observation, temporal_context: event.target.value as PrescriptionObservationDraft["temporal_context"] })}><option value="current">Current</option><option value="historical">Historical</option><option value="planned">Planned</option><option value="unknown">Unknown</option></select></label>
    </div></section>
    {observationCollections.map((collection) => observation[collection].length ? <section className="panel entry-block intake-record-section" key={collection}><div className="panel-heading"><div><p className="eyebrow">New Entry section</p><h3>{labels[collection]}</h3></div><button type="button" className="secondary-button" disabled={disabled} onClick={() => addRecord(collection)}><Plus size={15} />Add record</button></div>{observation[collection].map((record, index) => <article className={`intake-record-card intake-record-${record.state}`} key={record.temp_id}><div className="intake-record-heading"><label><input type="checkbox" checked={selectedRecords.has(`${collection}:${record.temp_id}`)} onChange={() => onToggleRecord?.(collection, record.temp_id)} /><strong>{labels[collection]} {index + 1}</strong></label><span className={`intake-state intake-state-${record.state}`}>{record.state}</span></div><div className="entry-grid">{Object.entries(record.values).map(([field, raw]) => {
        const resource = collectionOptionFields[collection]?.[field] ?? optionFields[field];
        let options = catalog[resource] ?? [];
        if (field === "disease_subgroup") { const group = record.resolutions.disease_group?.option_id; if (group) options = options.filter((option) => Number(option.disease_group) === group); }
        if (field === "exon") { const gene = record.resolutions.gene?.option_id; if (gene) options = options.filter((option) => Number(option.gene) === gene); }
        const selectedId = record.resolutions[field]?.option_id;
        const setValue = (value: unknown, option?: EntryOption) => updateRecord(collection, record.temp_id, (current) => ({ ...current, state: option ? "edited" : "unresolved", values: { ...current.values, [field]: value }, resolutions: option ? { ...current.resolutions, [field]: { status: "resolved", resource, raw_value: value, option_id: option.id, match_method: "reviewer_selected", candidates: [], reason: "" } } : current.resolutions }));
        return resource ? <label className="filter-field" key={field}><span>{field.replaceAll("_", " ")}</span><select className="filter-select" disabled={disabled} value={selectedId ?? ""} onChange={(event) => { const option = options.find((item) => String(item.id) === event.target.value); if (option) setValue(option.name ?? option.display ?? String(option.id), option); }}><option value="">{String(raw || "Select option")}</option>{options.map((option) => <option key={option.id} value={option.id}>{option.name ?? option.display}</option>)}</select></label> : <label className="filter-field" key={field}><span>{field.replaceAll("_", " ")}</span><input className="auth-input" disabled={disabled} value={raw == null ? "" : String(raw)} onChange={(event) => setValue(event.target.value)} /></label>;
      })}</div><div className="intake-record-actions"><button type="button" className="secondary-button" disabled={disabled || !stateReady(record)} onClick={() => updateRecord(collection, record.temp_id, (current) => ({ ...current, state: "validated" }))}><CheckCircle2 size={15} />Mark validated</button>{moveTargets.length ? <select className="filter-select" disabled={disabled} value="" aria-label="Move record" onChange={(event) => { if (event.target.value) onMoveRecord?.(collection, record.temp_id, event.target.value); }}><option value="">Move to observation…</option>{moveTargets.map((target) => <option key={target.id} value={target.id}>{target.label}</option>)}</select> : null}<button type="button" className="text-button danger-button" disabled={disabled} onClick={() => removeRecord(collection, record.temp_id)}><Trash2 size={15} />Remove</button></div></article>)}</section> : null)}
    {children}
  </div>;
}
