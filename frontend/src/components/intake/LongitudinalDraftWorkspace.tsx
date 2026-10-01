import { useMemo, useState } from "react";
import { Check, ChevronDown, ExternalLink, FileText, GitMerge, GitPullRequest, Maximize2, Minimize2, Plus, Save, Trash2 } from "lucide-react";
import type { EntryOption, LongitudinalIntakeDraft, PrescriptionDocument } from "../../api";
import { PatientFormSections } from "./PatientFormSections";
import { ObservationFormSections } from "./ObservationFormSections";
import { deleteObservation, emptyObservation, mergeObservations, moveRecord, observationCollections, recordCount, splitObservation, type ObservationCollection, type RecordRef } from "./draftWorkspace";

type Tab = "patient" | "diagnosis" | "pathology" | "treatment" | "outcome";
type JsonRecord = Record<string, unknown>;
const groups: Record<Exclude<Tab, "patient">, ObservationCollection[]> = {
  diagnosis: ["diagnoses", "comorbidities"],
  pathology: ["histopathologies", "ihc_results", "pathological_staging_results", "clinical_tnm_stagings", "pathological_tnm_stagings", "molecular_tests", "cancer_markers"],
  treatment: ["treatments", "surgeries", "radiotherapies"],
  outcome: ["recist_assessments", "irecist_assessments", "pathological_responses", "progression_records", "survival_records"],
};
const tabs: Array<[Tab, string]> = [["patient", "Patient"], ["diagnosis", "Diagnosis"], ["pathology", "Pathology"], ["treatment", "Treatment"], ["outcome", "Outcome"]];
const dateLabel = (value: string | null) => value ? new Date(value).toLocaleDateString() : "Undated";
const humanize = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const asRecord = (value: unknown): JsonRecord | null => value && typeof value === "object" && !Array.isArray(value) ? value as JsonRecord : null;
const isEvidence = (value: unknown) => {
  const item = asRecord(value);
  return Boolean(item && "value" in item && ("source_text" in item || "page" in item || "confidence" in item));
};

interface Props {
  document: PrescriptionDocument;
  draft: LongitudinalIntakeDraft;
  catalog: Record<string, EntryOption[]>;
  disabled?: boolean;
  saving?: boolean;
  error?: string;
  dirty?: boolean;
  onChange: (draft: LongitudinalIntakeDraft) => void;
  onSave: () => void;
  onApprove?: () => void;
  onPublish?: () => void;
  approving?: boolean;
  publishing?: boolean;
}

function GeminiValue({ value }: { value: unknown }) {
  const item = asRecord(value);
  if (isEvidence(value) && item) {
    const confidence = typeof item.confidence === "number" ? Math.round(item.confidence * 100) + "% confidence" : "Confidence not supplied";
    return <div className="clinical-gemini-fact"><strong>{String(item.value ?? "Not supplied")}</strong><small>{confidence}{item.page ? " · page " + String(item.page) : ""}</small>{item.source_text ? <em>{String(item.source_text)}</em> : null}</div>;
  }
  if (Array.isArray(value)) return <div className="clinical-gemini-list">{value.map((entry, index) => <GeminiValue key={index} value={entry} />)}</div>;
  if (item) return <dl className="clinical-gemini-object">{Object.entries(item).map(([key, entry]) => <div key={key}><dt>{humanize(key)}</dt><dd><GeminiValue value={entry} /></dd></div>)}</dl>;
  return <span>{value === null || value === undefined || value === "" ? "Not supplied" : String(value)}</span>;
}

function GeminiPayload({ document }: { document: PrescriptionDocument }) {
  const structured = asRecord(document.extraction_runs[0]?.structured_data);
  const payload = asRecord(structured?.gemini_extraction);
  if (!payload) return <details className="clinical-gemini-payload"><summary>Gemini structured payload <small>No Gemini payload available</small></summary></details>;
  const patient = asRecord(payload.patient);
  const observations = Array.isArray(payload.observations) ? payload.observations.map(asRecord).filter((item): item is JsonRecord => Boolean(item)) : [];
  const alerts = ["warnings", "unresolved_items"].flatMap((key) => Array.isArray(payload[key]) ? payload[key] : []);
  return <details className="clinical-gemini-payload">
    <summary>Gemini structured payload <small>{observations.length} extracted observation{observations.length === 1 ? "" : "s"}</small></summary>
    <p className="clinical-gemini-help">Read-only Gemini evidence. It is not saved until you validate the matching form fields.</p>
    {patient && Object.keys(patient).length ? <section><h4>Patient</h4><GeminiValue value={patient} /></section> : null}
    {observations.map((observation, index) => <details className="clinical-gemini-observation" key={index}><summary>Observation {index + 1} · {String(observation.temporal_context ?? "unknown")}</summary><GeminiValue value={Object.fromEntries(Object.entries(observation).filter(([key]) => key !== "temporal_context"))} /></details>)}
    {alerts.length ? <section className="clinical-gemini-alerts"><h4>Needs review</h4>{alerts.map((item, index) => <p key={index}>{asRecord(item)?.reason ? String(asRecord(item)?.reason) : String(item)}</p>)}</section> : null}
    <details className="clinical-gemini-raw"><summary>View exact JSON</summary><pre>{JSON.stringify(payload, null, 2)}</pre></details>
  </details>;
}

export function LongitudinalDraftWorkspace({ document, draft, catalog, disabled, saving, error, dirty, onChange, onSave, onApprove, onPublish, approving, publishing }: Props) {
  const [selectedId, setSelectedId] = useState(draft.observations[0]?.temp_id ?? "");
  const [tab, setTab] = useState<Tab>("patient");
  const [selectedRecords, setSelectedRecords] = useState<Set<string>>(new Set());
  const [mergeTarget, setMergeTarget] = useState("");
  const [sourceExpanded, setSourceExpanded] = useState(false);
  const selected = draft.observations.find((item) => item.temp_id === selectedId) ?? draft.observations[0];
  const evidence = useMemo(() => selected?.evidence_refs ?? [], [selected]);
  if (!selected) return null;
  const setDraft = (next: LongitudinalIntakeDraft, nextSelected = selected.temp_id) => { onChange(next); setSelectedId(nextSelected); setSelectedRecords(new Set()); };
  const split = () => {
    const refs: RecordRef[] = [...selectedRecords].map((key) => {
      const [collection, tempId] = key.split(":");
      return { collection: collection as ObservationCollection, tempId };
    });
    const next = splitObservation(draft, selected.temp_id, refs);
    setDraft(next, next.observations.at(-1)?.temp_id);
  };
  const unresolved = [...draft.unresolved_items, ...observationCollections.flatMap((collection) => selected[collection].filter((record) => record.state === "unresolved").map(() => ({ reason: collection.replaceAll("_", " ") + " needs review" })))];
  const pdf = document.original_filename.toLowerCase().endsWith(".pdf");
  return <section className="clinical-intake-workspace">
    <header className="clinical-intake-header"><div><p className="eyebrow">Prescription review</p><h2>{document.original_filename}</h2>{dirty ? <small className="clinical-dirty">Unsaved changes</small> : null}</div><div className="clinical-intake-actions"><button type="button" className="secondary-button" disabled={disabled || saving} onClick={onSave}><Save size={16} />Save draft</button>{onApprove ? <button type="button" className="primary-button" disabled={disabled || approving || saving} onClick={onApprove}><Check size={16} />Approve</button> : null}{onPublish ? <button type="button" className="primary-button" disabled={publishing} onClick={onPublish}>Publish</button> : null}</div></header>
    {error ? <p className="entry-error-message">{error}</p> : null}
    <div className="clinical-intake-grid">
      <aside className={"clinical-source-column" + (sourceExpanded ? " is-expanded" : "")}><details open><summary><FileText size={16} /> Prescription <ChevronDown size={15} /></summary><div className="clinical-source-actions"><button type="button" className="secondary-button" onClick={() => setSourceExpanded((current) => !current)}>{sourceExpanded ? <Minimize2 size={15} /> : <Maximize2 size={15} />}{sourceExpanded ? "Close full page" : "Full page"}</button><a className="secondary-button" href={document.file} target="_blank" rel="noreferrer"><ExternalLink size={15} />Open source</a></div><p className="clinical-source-help">{pdf ? "Use the PDF toolbar’s − / + controls to zoom. Full page gives the toolbar more room." : "Open source shows the original file at full size."}</p>{pdf ? <iframe title="Prescription preview" className="clinical-pdf" src={document.file} /> : <img className="clinical-image" src={document.file} alt="Prescription preview" />}<div className="clinical-evidence">{evidence.length ? evidence.map((item) => <p key={item.evidence_id}><small>p. {item.page ?? "—"}</small>{item.source_text}</p>) : <p>No linked evidence for this observation.</p>}</div><GeminiPayload document={document} /></details></aside>
      <aside className="clinical-timeline-column"><div className="clinical-column-title"><strong>Observations</strong><button type="button" className="text-button" disabled={disabled} onClick={() => { const next = emptyObservation(); setDraft({ ...draft, observations: [...draft.observations, next] }, next.temp_id); }}><Plus size={15} />Add</button></div><div className="clinical-timeline">{draft.observations.map((observation) => <button type="button" key={observation.temp_id} className={observation.temp_id === selected.temp_id ? "is-selected" : ""} onClick={() => { setSelectedId(observation.temp_id); setSelectedRecords(new Set()); }}><span>{dateLabel(observation.observed_at || observation.prescription_date)}</span><strong>{observation.temporal_context}</strong><small>{recordCount(observation)} items</small></button>)}</div><div className="clinical-timeline-tools"><button type="button" className="secondary-button" disabled={disabled || !selectedRecords.size} onClick={split}><GitPullRequest size={14} />Split</button><select className="filter-select" value={mergeTarget} disabled={disabled} onChange={(event) => setMergeTarget(event.target.value)}><option value="">Merge into…</option>{draft.observations.filter((item) => item.temp_id !== selected.temp_id).map((item) => <option key={item.temp_id} value={item.temp_id}>{dateLabel(item.observed_at)}</option>)}</select><button type="button" className="secondary-button" disabled={disabled || !mergeTarget} onClick={() => mergeTarget && setDraft(mergeObservations(draft, selected.temp_id, mergeTarget), mergeTarget)}><GitMerge size={14} />Merge</button><button type="button" className="text-button danger-button" disabled={disabled || draft.observations.length === 1} onClick={() => setDraft(deleteObservation(draft, selected.temp_id))}><Trash2 size={14} />Delete</button></div></aside>
      <main className="clinical-editor-column"><nav className="clinical-section-tabs">{tabs.map(([key, label]) => <button type="button" className={tab === key ? "is-active" : ""} key={key} onClick={() => setTab(key)}>{label}</button>)}</nav>{tab === "patient" ? <PatientFormSections patient={draft.patient} catalog={catalog} disabled={disabled} onChange={(patient) => onChange({ ...draft, patient })} /> : <ObservationFormSections observation={selected} collections={groups[tab]} catalog={catalog} disabled={disabled} selectedRecords={selectedRecords} onToggleRecord={(collection, tempId) => setSelectedRecords((current) => { const next = new Set(current); const key = collection + ":" + tempId; next.has(key) ? next.delete(key) : next.add(key); return next; })} onChange={(observation) => onChange({ ...draft, observations: draft.observations.map((item) => item.temp_id === observation.temp_id ? observation : item) })} moveTargets={draft.observations.filter((item) => item.temp_id !== selected.temp_id).map((item) => ({ id: item.temp_id, label: dateLabel(item.observed_at) }))} onMoveRecord={(collection, tempId, targetId) => setDraft(moveRecord(draft, selected.temp_id, targetId, { collection, tempId }))} />}</main>
    </div>
    {unresolved.length ? <aside className="clinical-unresolved"><strong>Needs review</strong>{unresolved.map((item, index) => <span key={index}>• {String(item.reason || "Review this item")}</span>)}</aside> : null}
  </section>;
}
