import { CheckCircle2, Plus, Trash2 } from "lucide-react";
import type { EntryOption, PrescriptionDraftRecord, PrescriptionObservationDraft } from "../../api";
import { observationCollections, type ObservationCollection } from "./draftWorkspace";
import { createBlankRecord, observationFieldSchemas, recordReady, type ObservationField } from "./observationFieldSchema";
import { IntakeSelectField, IntakeTextArea, IntakeTextField } from "./SharedIntakeFields";

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
}

function hasValue(value: unknown) {
  return Array.isArray(value) ? value.length > 0 : value !== undefined && value !== null && String(value).trim() !== "";
}

function scopedOptions(field: ObservationField, record: PrescriptionDraftRecord, catalog: Catalog) {
  let options = catalog[field.resource ?? ""] ?? [];
  const resolved = (key: string) => record.resolutions[key]?.option_id;
  if (field.key === "disease_subgroup" && resolved("disease_group")) options = options.filter((option) => Number(option.disease_group) === resolved("disease_group"));
  if (field.key === "exon" && resolved("gene")) options = options.filter((option) => Number(option.gene) === resolved("gene"));
  if (field.key === "panel_version" && resolved("panel")) options = options.filter((option) => Number(option.panel) === resolved("panel"));
  return options;
}

export function ObservationFormSections({ observation, catalog = {}, disabled, selectedRecords = new Set(), onToggleRecord, onChange, onMoveRecord, moveTargets = [] }: ObservationFormSectionsProps) {
  const updateRecord = (collection: ObservationCollection, tempId: string, updater: (record: PrescriptionDraftRecord) => PrescriptionDraftRecord) => onChange({ ...observation, [collection]: observation[collection].map((record) => record.temp_id === tempId ? updater(record) : record) });
  const removeRecord = (collection: ObservationCollection, tempId: string) => onChange({ ...observation, [collection]: observation[collection].filter((record) => record.temp_id !== tempId) });
  const addRecord = (collection: ObservationCollection) => onChange({ ...observation, [collection]: [...observation[collection], createBlankRecord(collection)] });
  const updateAnthropometry = (key: string, value: string) => onChange({ ...observation, anthropometry: { ...(observation.anthropometry ?? {}), [key]: value } });

  return <div className="intake-observation-form">
    <section className="panel entry-block intake-form-section"><div className="panel-heading"><div><p className="eyebrow">Observation-level draft</p><h3>Observation context</h3></div></div><div className="entry-grid">
      <IntakeTextField label="Observed at" type="datetime-local" disabled={disabled} value={observation.observed_at?.slice(0, 16) ?? ""} onChange={(value) => onChange({ ...observation, observed_at: value || null })} />
      <IntakeTextField label="Prescription date" type="date" disabled={disabled} value={observation.prescription_date ?? ""} onChange={(value) => onChange({ ...observation, prescription_date: value || null })} />
      <label className="filter-field"><span>Temporal context</span><select className="filter-select" disabled={disabled} value={observation.temporal_context} onChange={(event) => onChange({ ...observation, temporal_context: event.target.value as PrescriptionObservationDraft["temporal_context"] })}><option value="current">Current</option><option value="historical">Historical</option><option value="planned">Planned</option><option value="unknown">Unknown</option></select></label>
      <IntakeTextField label="Height" type="number" disabled={disabled} value={String(observation.anthropometry?.height ?? "")} onChange={(value) => updateAnthropometry("height", value)} />
      <IntakeTextField label="Weight" type="number" disabled={disabled} value={String(observation.anthropometry?.weight ?? "")} onChange={(value) => updateAnthropometry("weight", value)} />
      <IntakeTextField label="Body surface area" type="number" disabled={disabled} value={String(observation.anthropometry?.body_surface_area ?? "")} onChange={(value) => updateAnthropometry("body_surface_area", value)} />
    </div></section>
    {observationCollections.map((collection) => {
      const schema = observationFieldSchemas[collection];
      return <details className="panel entry-block intake-record-section" key={collection} open={observation[collection].length > 0}>
        <summary className="panel-heading"><div><p className="eyebrow">New Entry section</p><h3>{schema.label}</h3></div><span>{observation[collection].length} record{observation[collection].length === 1 ? "" : "s"}</span></summary>
        <button type="button" className="secondary-button" disabled={disabled} onClick={() => addRecord(collection)}><Plus size={15} />Add {schema.label}</button>
        {!observation[collection].length ? <p className="hero-text">No {schema.label.toLowerCase()} recorded.</p> : null}
        {observation[collection].map((record, index) => <article className={`intake-record-card intake-record-${record.state}`} key={record.temp_id}>
          <div className="intake-record-heading"><label><input type="checkbox" checked={selectedRecords.has(`${collection}:${record.temp_id}`)} onChange={() => onToggleRecord?.(collection, record.temp_id)} /><strong>{schema.label} {index + 1}</strong></label><span className={`intake-state intake-state-${record.state}`}>{record.state}</span></div>
          <div className="entry-grid">{schema.fields.map((field) => {
            const raw = record.values[field.key];
            const updateValue = (value: unknown, option?: EntryOption) => updateRecord(collection, record.temp_id, (current) => {
              const resolutions = { ...current.resolutions };
              if (field.resource) resolutions[field.key] = option
                ? { status: "resolved", resource: field.resource, raw_value: option.name ?? option.display, option_id: option.id, match_method: "reviewer_selected", candidates: [], reason: "" }
                : { status: "unresolved", resource: field.resource, raw_value: value, option_id: null, match_method: null, candidates: [], reason: "Selection required." };
              return { ...current, state: "edited", values: { ...current.values, [field.key]: value }, resolutions };
            });
            if (field.multiple) return <IntakeTextArea key={field.key} label={field.label} disabled={disabled} value={Array.isArray(raw) ? raw.join(", ") : String(raw ?? "")} onChange={(value) => updateValue(value.split(",").map((item) => item.trim()).filter(Boolean))} help="Enter one or more values separated by commas; unresolved extracted values remain flagged for review." />;
            if (field.resource) {
              const options = scopedOptions(field, record, catalog);
              return <IntakeSelectField key={field.key} label={field.label} required={field.required} disabled={disabled} options={options} value={record.resolutions[field.key]?.option_id ?? ""} placeholder={hasValue(raw) ? String(raw) : `Select ${field.label.toLowerCase()}`} onChange={(value, option) => updateValue(option ? option.name ?? option.display : value, option)} />;
            }
            if (field.type === "textarea") return <IntakeTextArea key={field.key} label={field.label} disabled={disabled} value={String(raw ?? "")} onChange={updateValue} />;
            return <IntakeTextField key={field.key} label={field.label} type={field.type} required={field.required} disabled={disabled} value={String(raw ?? "")} onChange={updateValue} />;
          })}</div>
          <div className="intake-record-actions"><button type="button" className="secondary-button" disabled={disabled || !recordReady(collection, record)} onClick={() => updateRecord(collection, record.temp_id, (current) => ({ ...current, state: "validated" }))}><CheckCircle2 size={15} />Mark validated</button>{moveTargets.length ? <select className="filter-select" disabled={disabled} value="" aria-label="Move record" onChange={(event) => { if (event.target.value) onMoveRecord?.(collection, record.temp_id, event.target.value); }}><option value="">Move to observation…</option>{moveTargets.map((target) => <option key={target.id} value={target.id}>{target.label}</option>)}</select> : null}<button type="button" className="text-button danger-button" disabled={disabled} onClick={() => removeRecord(collection, record.temp_id)}><Trash2 size={15} />Remove</button></div>
        </article>)}
      </details>;
    })}
  </div>;
}
