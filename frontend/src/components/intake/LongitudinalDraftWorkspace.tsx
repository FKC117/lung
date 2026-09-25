import { useMemo, useState } from "react";
import { Columns3, FileText, GitMerge, GitPullRequest, Plus, Save, Trash2 } from "lucide-react";
import type { EntryOption, LongitudinalIntakeDraft, PrescriptionDocument } from "../../api";
import { PatientFormSections } from "./PatientFormSections";
import { ObservationFormSections } from "./ObservationFormSections";
import { deleteObservation, emptyObservation, mergeObservations, moveRecord, observationCollections, recordCount, splitObservation, type ObservationCollection, type RecordRef } from "./draftWorkspace";

interface Props {
  document: PrescriptionDocument;
  draft: LongitudinalIntakeDraft;
  catalog: Record<string, EntryOption[]>;
  disabled?: boolean;
  saving?: boolean;
  error?: string;
  onChange: (draft: LongitudinalIntakeDraft) => void;
  onSave: () => void;
}

function formatObservation(index: number, date: string | null) {
  return `Observation ${index + 1}${date ? ` · ${new Date(date).toLocaleDateString()}` : ""}`;
}

export function LongitudinalDraftWorkspace({ document, draft, catalog, disabled, saving, error, onChange, onSave }: Props) {
  const [selectedId, setSelectedId] = useState(draft.observations[0]?.temp_id ?? "");
  const [selectedRecords, setSelectedRecords] = useState<Set<string>>(new Set());
  const [mergeTarget, setMergeTarget] = useState("");
  const selectedIndex = Math.max(0, draft.observations.findIndex((item) => item.temp_id === selectedId));
  const selected = draft.observations[selectedIndex] ?? draft.observations[0];
  const evidence = useMemo(() => selected?.evidence_refs ?? [], [selected]);
  if (!selected) return null;

  const setDraft = (next: LongitudinalIntakeDraft, nextSelected = selectedId) => { onChange(next); setSelectedId(nextSelected); setSelectedRecords(new Set()); };
  const add = () => { const observation = emptyObservation(); setDraft({ ...draft, observations: [...draft.observations, observation] }, observation.temp_id); };
  const remove = () => { const next = deleteObservation(draft, selected.temp_id); setDraft(next, next.observations[Math.min(selectedIndex, next.observations.length - 1)].temp_id); };
  const split = () => { const refs: RecordRef[] = [...selectedRecords].map((key) => { const [collection, tempId] = key.split(":"); return { collection: collection as ObservationCollection, tempId }; }); const next = splitObservation(draft, selected.temp_id, refs); setDraft(next, next.observations.at(-1)?.temp_id ?? selected.temp_id); };
  const merge = () => { if (!mergeTarget) return; const next = mergeObservations(draft, selected.temp_id, mergeTarget); setDraft(next, mergeTarget); setMergeTarget(""); };
  const updateObservation = (observation: typeof selected) => onChange({ ...draft, observations: draft.observations.map((item) => item.temp_id === observation.temp_id ? observation : item) });

  return <section className="longitudinal-draft-workspace">
    <header className="longitudinal-workspace-toolbar"><div><p className="eyebrow">Longitudinal Intake Workspace</p><h3>{document.original_filename}</h3><p className="hero-text">Review source evidence, organize the timeline, and validate the same New Entry fields before saving the canonical draft.</p></div><button type="button" className="primary-button" disabled={disabled || saving} onClick={onSave}><Save size={16} />{saving ? "Saving…" : "Save canonical draft"}</button></header>
    {error ? <p className="entry-error-message" role="alert">{error}</p> : null}
    <div className="longitudinal-workspace-columns">
      <aside className="longitudinal-source-pane">
        <div className="longitudinal-pane-title"><FileText size={17} /><div><strong>Prescription and evidence</strong><small>Source material remains read-only</small></div></div>
        {document.file.toLowerCase().includes("source-file") && document.original_filename.toLowerCase().endsWith(".pdf") ? <iframe className="longitudinal-pdf" title={`Prescription ${document.original_filename}`} src={document.file} /> : null}
        <a className="secondary-button" href={document.file} target="_blank" rel="noreferrer">Open original</a>
        <div className="longitudinal-evidence-list">{evidence.length ? evidence.map((item) => <article key={item.evidence_id} className="longitudinal-evidence-card"><div><span>Page {item.page ?? "—"}</span>{item.confidence != null ? <span>{Math.round(item.confidence * 100)}%</span> : null}</div><strong>{item.field_path}</strong><p>{item.source_text || "No source excerpt recorded."}</p></article>) : <p className="hero-text">This observation has no linked evidence.</p>}</div>
      </aside>
      <aside className="longitudinal-timeline-pane">
        <div className="longitudinal-pane-title"><Columns3 size={17} /><div><strong>Observation timeline</strong><small>{draft.observations.length} draft observation{draft.observations.length === 1 ? "" : "s"}</small></div></div>
        <button type="button" className="secondary-button" disabled={disabled} onClick={add}><Plus size={15} />Add observation</button>
        <div className="longitudinal-observation-list">{draft.observations.map((observation, index) => { const unresolved = observationCollections.flatMap((collection) => observation[collection]).filter((record) => record.state === "unresolved").length; return <button type="button" key={observation.temp_id} className={`longitudinal-observation-card${selected.temp_id === observation.temp_id ? " is-selected" : ""}`} onClick={() => { setSelectedId(observation.temp_id); setSelectedRecords(new Set()); }}><span>{observation.temporal_context}</span><strong>{formatObservation(index, observation.observed_at)}</strong><small>{recordCount(observation)} records · {unresolved ? `${unresolved} unresolved` : "ready for review"}</small></button>; })}</div>
        <div className="longitudinal-timeline-actions"><button type="button" className="secondary-button" disabled={disabled || !selectedRecords.size} onClick={split}><GitPullRequest size={15} />Split selected ({selectedRecords.size})</button><div className="longitudinal-merge-row"><select className="filter-select" value={mergeTarget} disabled={disabled || draft.observations.length < 2} onChange={(event) => setMergeTarget(event.target.value)}><option value="">Merge into…</option>{draft.observations.filter((item) => item.temp_id !== selected.temp_id).map((item, index) => <option value={item.temp_id} key={item.temp_id}>{formatObservation(index, item.observed_at)}</option>)}</select><button type="button" className="secondary-button" disabled={!mergeTarget || disabled} onClick={merge}><GitMerge size={15} />Merge</button></div><button type="button" className="text-button danger-button" disabled={disabled || draft.observations.length === 1} onClick={remove}><Trash2 size={15} />Delete observation</button></div>
      </aside>
      <main className="longitudinal-form-pane">
        <PatientFormSections patient={draft.patient} catalog={catalog} disabled={disabled} onChange={(patient) => onChange({ ...draft, patient })} />
        <ObservationFormSections observation={selected} catalog={catalog} disabled={disabled} selectedRecords={selectedRecords} onToggleRecord={(collection, tempId) => { const key = `${collection}:${tempId}`; setSelectedRecords((current) => { const next = new Set(current); if (next.has(key)) next.delete(key); else next.add(key); return next; }); }} onChange={updateObservation} moveTargets={draft.observations.filter((item) => item.temp_id !== selected.temp_id).map((item, index) => ({ id: item.temp_id, label: formatObservation(index, item.observed_at) }))} onMoveRecord={(collection, tempId, targetId) => setDraft(moveRecord(draft, selected.temp_id, targetId, { collection, tempId }))} />
        {draft.unresolved_items.length ? <section className="panel entry-block intake-unresolved-items"><div className="panel-heading"><div><p className="eyebrow">Requires review</p><h3>Unresolved extraction items</h3></div><span className="intake-state intake-state-unresolved">{draft.unresolved_items.length}</span></div>{draft.unresolved_items.map((item, index) => <article key={index}><pre>{JSON.stringify(item, null, 2)}</pre><button type="button" className="text-button danger-button" disabled={disabled} onClick={() => onChange({ ...draft, unresolved_items: draft.unresolved_items.filter((_, itemIndex) => itemIndex !== index) })}>Mark addressed</button></article>)}</section> : null}
      </main>
    </div>
  </section>;
}
