import { CheckCircle2, Plus, Trash2 } from "lucide-react";
import type { EntryOption, PrescriptionDraftRecord, PrescriptionObservationDraft } from "../../api";
import { observationCollections, type ObservationCollection } from "./draftWorkspace";
import { anthropometrySectionSchema, createBlankRecord, observationFieldSchemas, recordReady, type ClinicalFieldDefinition } from "./observationFieldSchema";
import { IntakeTextField } from "./SharedIntakeFields";
import { ClinicalSectionFields } from "./ClinicalSectionFields";

type Catalog = Record<string, EntryOption[]>;

export interface ObservationFormSectionsProps {
  observation: PrescriptionObservationDraft;
  catalog?: Catalog;
  disabled?: boolean;
  selectedRecords?: Set<string>;
  onToggleRecord?: (collection: ObservationCollection, tempId: string) => void;
  onChange: (observation: PrescriptionObservationDraft) => void;
  onMoveRecord?: (collection: ObservationCollection, tempId: string, targetId: string) => void;
  moveTargets?: Array<{ id: string; label: string }>;
  collections?: readonly ObservationCollection[];
}

function scopedOptions(field: ClinicalFieldDefinition, record: PrescriptionDraftRecord, catalog: Catalog) {
  let options = catalog[field.resource ?? ""] ?? [];
  const resolved = (key: string) => record.resolutions[key]?.option_id;
  if (field.key === "disease_subgroup" && resolved("disease_group")) options = options.filter((option) => Number(option.disease_group) === resolved("disease_group"));
  if (field.key === "exon" && resolved("gene")) options = options.filter((option) => Number(option.gene) === resolved("gene"));
  if (field.key === "panel_version" && resolved("panel")) options = options.filter((option) => Number(option.panel) === resolved("panel"));
  return options;
}

function scopedCatalog(record: PrescriptionDraftRecord, catalog: Catalog) {
  return Object.fromEntries(Object.entries(catalog).map(([resource, options]) => {
    const key = resource === "diagnosis-disease-subgroups" ? "disease_subgroup" : resource === "molecular-exons" ? "exon" : resource === "molecular-panel-versions" ? "panel_version" : "";
    return [resource, key ? scopedOptions({ key, label: "", resource }, record, { [resource]: options }) : options];
  }));
}

export function ObservationFormSections({ observation, catalog = {}, disabled, selectedRecords = new Set(), onToggleRecord, onChange, onMoveRecord, moveTargets = [], collections = observationCollections }: ObservationFormSectionsProps) {
  const updateRecord = (collection: ObservationCollection, tempId: string, updater: (record: PrescriptionDraftRecord) => PrescriptionDraftRecord) => onChange({ ...observation, [collection]: observation[collection].map((record) => record.temp_id === tempId ? updater(record) : record) });
  const removeRecord = (collection: ObservationCollection, tempId: string) => onChange({ ...observation, [collection]: observation[collection].filter((record) => record.temp_id !== tempId) });
  const addRecord = (collection: ObservationCollection) => onChange({ ...observation, [collection]: [...observation[collection], createBlankRecord(collection)] });
  const updateAnthropometry = (key: string, value: string) => onChange({ ...observation, anthropometry: { ...(observation.anthropometry ?? {}), [key]: value } });

  return <div className="intake-observation-form">
    <section className="panel entry-block intake-form-section"><div className="panel-heading"><div><p className="eyebrow">Observation-level draft</p><h3>Observation context</h3></div></div><div className="entry-grid">
      <IntakeTextField label="Observed at" type="datetime-local" disabled={disabled} value={observation.observed_at?.slice(0, 16) ?? ""} onChange={(value) => onChange({ ...observation, observed_at: value || null })} />
      <IntakeTextField label="Prescription date" type="date" disabled={disabled} value={observation.prescription_date ?? ""} onChange={(value) => onChange({ ...observation, prescription_date: value || null })} />
      <label className="filter-field"><span>Temporal context</span><select className="filter-select" disabled={disabled} value={observation.temporal_context} onChange={(event) => onChange({ ...observation, temporal_context: event.target.value as PrescriptionObservationDraft["temporal_context"] })}><option value="current">Current</option><option value="historical">Historical</option><option value="planned">Planned</option><option value="unknown">Unknown</option></select></label>
    </div><ClinicalSectionFields fields={anthropometrySectionSchema.fields} values={observation.anthropometry ?? {}} catalog={catalog} disabled={disabled} onChange={(field, value) => updateAnthropometry(field.key, String(value))} /></section>
    {collections.map((collection) => {
      const schema = observationFieldSchemas[collection];
      return <details className="panel entry-block intake-record-section" key={collection} open={observation[collection].length > 0}>
        <summary className="panel-heading"><div><p className="eyebrow">New Entry section</p><h3>{schema.label}</h3></div><span>{observation[collection].length} record{observation[collection].length === 1 ? "" : "s"}</span></summary>
        <button type="button" className="secondary-button" disabled={disabled} onClick={() => addRecord(collection)}><Plus size={15} />Add {schema.label}</button>
        {!observation[collection].length ? <p className="hero-text">No {schema.label.toLowerCase()} recorded.</p> : null}
        {observation[collection].map((record, index) => <article className={`intake-record-card intake-record-${record.state}`} key={record.temp_id}>
          <div className="intake-record-heading"><label><input type="checkbox" checked={selectedRecords.has(`${collection}:${record.temp_id}`)} onChange={() => onToggleRecord?.(collection, record.temp_id)} /><strong>{schema.label} {index + 1}</strong></label><span className={`intake-state intake-state-${record.state}`}>{record.state}</span></div>
          <ClinicalSectionFields fields={schema.fields} values={record.values} resolutions={record.resolutions} catalog={scopedCatalog(record, catalog)} disabled={disabled} onChange={(field, value, options = []) => {
            const option = options[0];
            updateRecord(collection, record.temp_id, (current) => {
              const resolutions = { ...current.resolutions };
              if (field.resource) resolutions[field.key] = field.multiple
                ? { status: options.length || !(value as number[]).length ? "resolved" : "unresolved", resource: field.resource, raw_value: options.map((item) => item.name ?? item.display), option_id: null, option_ids: options.map((item) => item.id), match_method: "reviewer_selected", candidates: [], reason: options.length || !(value as number[]).length ? "" : "Selection required." }
                : option
                ? { status: "resolved", resource: field.resource, raw_value: option.name ?? option.display, option_id: option.id, match_method: "reviewer_selected", candidates: [], reason: "" }
                : { status: "unresolved", resource: field.resource, raw_value: value, option_id: null, match_method: null, candidates: [], reason: "Selection required." };
              // Canonical draft values carry validated option IDs.  Display text
              // stays in the resolution/evidence layer and is never mistaken for
              // a persisted clinical value.
              const canonicalValue = field.resource
                ? field.multiple ? options.map((item) => item.id) : option ? option.id : value
                : value;
              return { ...current, state: "edited", values: { ...current.values, [field.key]: canonicalValue }, resolutions };
            });
          }} />
          <div className="intake-record-actions"><button type="button" className="secondary-button" disabled={disabled || !recordReady(collection, record)} onClick={() => updateRecord(collection, record.temp_id, (current) => ({ ...current, state: "validated" }))}><CheckCircle2 size={15} />Mark validated</button>{moveTargets.length ? <select className="filter-select" disabled={disabled} value="" aria-label="Move record" onChange={(event) => { if (event.target.value) onMoveRecord?.(collection, record.temp_id, event.target.value); }}><option value="">Move to observation…</option>{moveTargets.map((target) => <option key={target.id} value={target.id}>{target.label}</option>)}</select> : null}<button type="button" className="text-button danger-button" disabled={disabled} onClick={() => removeRecord(collection, record.temp_id)}><Trash2 size={15} />Remove</button></div>
        </article>)}
      </details>;
    })}
  </div>;
}
