import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchEntriesOptions, fetchPrescriptionDocument, loadLatestPrescriptionExtraction, startPrescriptionReview, updatePrescriptionReview, type PrescriptionReview, type PrescriptionDraftRecord, type LongitudinalIntakeDraft } from "../../api";
import { observationCollections, type ObservationCollection } from "./draftWorkspace";
import { authoritativeOptionResources, observationFieldSchemas, fieldDependencies } from "./observationFieldSchema";
import { ClinicalSectionFields } from "./ClinicalSectionFields";
import { scopedCatalog } from "./ObservationFormSections";
import { sourceFacts } from "./sourceFacts";

export const PreviewDraftEditContext = createContext<(key: string, dirty: boolean, busy: boolean) => void>(() => undefined);

export function PreviewDraftAction({ documentId, collection, eventIndex, children }: { documentId: number; collection: string; eventIndex: number; children?: (editing: boolean) => ReactNode }) {
  const client = useQueryClient();
  const report = useContext(PreviewDraftEditContext);
  const [pendingRun, setPendingRun] = useState<number | null>(null);
  const [modify, setModify] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [review, setReview] = useState<PrescriptionReview | null>(null);
  const [catalog, setCatalog] = useState<Awaited<ReturnType<typeof fetchEntriesOptions>>>({});
  const [records, setRecords] = useState<PrescriptionDraftRecord[]>([]);
  const [busy, setBusy] = useState(false);
  useEffect(() => { report(`${eventIndex}:${collection}`, dirty, busy); }, [dirty, busy, report, eventIndex, collection]);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const existingQuery = useQuery({ queryKey: ["prescription-document", documentId], queryFn: () => fetchPrescriptionDocument(documentId) });
  const choicesQuery = useQuery({ queryKey: ["prescription-review-options"], queryFn: () => fetchEntriesOptions(authoritativeOptionResources) });
  useEffect(() => {
    const current = existingQuery.data?.review;
    if (review || !current || !choicesQuery.data || !["draft", "in_review"].includes(current.status) || current.published_at) return;
    if (!observationCollections.includes(collection as ObservationCollection)) return;
    const sourceIds = new Set(sourceFacts(current.reviewed_data).filter((fact) => fact.source_path.startsWith(`observations.${eventIndex}.${collection}.`)).map((fact) => fact.record_temp_id));
    const matches = current.reviewed_data.observations.flatMap((observation) => observation[collection as ObservationCollection]).filter((record) => sourceIds.has(record.temp_id));
    if (matches.length) { setReview(current); setRecords(structuredClone(matches)); setCatalog(choicesQuery.data); }
  }, [existingQuery.data, choicesQuery.data, review, collection, eventIndex]);
  if (!observationCollections.includes(collection as ObservationCollection)) return children?.(false) ?? null;
  const key = collection as ObservationCollection;
  const open = async () => {
    setBusy(true); setError("");
    try {
      const current = await startPrescriptionReview(documentId);
      if (!["draft", "in_review"].includes(current.status) || current.published_at) throw new Error("This review is locked. Open the saved review to view it.");
      const ids = new Set(sourceFacts(current.reviewed_data).filter((fact) => fact.source_path.startsWith(`observations.${eventIndex}.${key}.`)).map((fact) => fact.record_temp_id));
      const matches = current.reviewed_data.observations.flatMap((observation) => observation[key]).filter((record) => ids.has(record.temp_id));
      let editable = matches;
      if (!editable.length) {
        const document = await fetchPrescriptionDocument(documentId);
        const run = document?.extraction_runs?.[0];
        const latest = run?.structured_data?.canonical_draft as LongitudinalIntakeDraft | undefined;
        if (!latest?.observations || run?.status !== "completed") throw new Error("No editable extraction is available for this segment.");
        const latestIds = new Set(sourceFacts(latest).filter((fact) => fact.source_path.startsWith(`observations.${eventIndex}.${key}.`)).map((fact) => fact.record_temp_id));
        editable = latest.observations.flatMap((observation) => observation[key]).filter((record) => latestIds.has(record.temp_id));
        if (!editable.length) throw new Error("This segment has no supported field mapping. Original evidence is preserved.");
        setPendingRun(run.id);
      }
      const choices = await fetchEntriesOptions(authoritativeOptionResources);
      setCatalog(choices); setReview(current); setRecords(structuredClone(editable));
    } catch (exception) { setError(exception instanceof Error ? exception.message : "Could not prepare draft choices."); }
    finally { setBusy(false); }
  };
  const save = async () => {
    if (!review) return;
    setBusy(true); setError("");
    try {
      const base = pendingRun !== null ? await loadLatestPrescriptionExtraction(documentId, review.revision, pendingRun) : review;
      if (pendingRun !== null) { setReview(base); setPendingRun(null); }
      const changes = new Map(records.map((record) => [record.temp_id, record]));
      const draft = { ...base.reviewed_data, observations: base.reviewed_data.observations.map((observation) => ({ ...observation, [key]: observation[key].map((record) => changes.get(record.temp_id) ?? record) })) };
      const result = await updatePrescriptionReview(documentId, { expected_revision: base.revision, reviewed_data: draft });
      setReview(result); setPendingRun(null); setSaved(true); setDirty(false);
      await client.invalidateQueries({ queryKey: ["prescription-documents"] });
      await client.invalidateQueries({ queryKey: ["prescription-document", documentId] });
    } catch (exception) { setError(exception instanceof Error ? exception.message : "Could not save these choices."); }
    finally { setBusy(false); }
  };
  return <div className="prescription-segment-review">
    {children?.(modify && Boolean(records.length))}
    <div className="prescription-card-action">
    {!review ? <div className="prescription-card-buttons"><button type="button" className="primary-button" disabled={busy} onClick={() => { void open(); }}>{busy ? "Loading choices…" : "Correct"}</button><button type="button" className="secondary-button" disabled={busy} onClick={() => { setModify(true); void open(); }}>Modify</button></div> : <>
      <p className="entry-field-help">Confirm these choices or modify the fields in this segment. Saving updates the observation draft.</p>
      {records.map((record, index) => <div key={record.temp_id}><strong>Item {index + 1}</strong><ClinicalSectionFields fields={observationFieldSchemas[key].fields.filter((field) => modify || Boolean(field.resource))} values={record.values} extractedValues={record.extracted_values} resolutions={record.resolutions} catalog={scopedCatalog(record, catalog)} disabled={busy || saved} onChange={(field, value, options = []) => {
        setDirty(true);
        setRecords((current) => current.map((item) => {
          if (item.temp_id !== record.temp_id) return item;
          const values = { ...item.values, [field.key]: field.resource ? field.multiple ? options.map((option) => option.id) : options[0]?.id ?? value : value };
          const resolutions = { ...item.resolutions, [field.key]: { status: options.length ? "resolved" as const : "unresolved" as const, resource: field.resource!, raw_value: item.resolutions[field.key]?.raw_value ?? item.values[field.key], option_id: options[0]?.id ?? null, option_ids: field.multiple ? options.map((option) => option.id) : undefined, match_method: "reviewer_selected", candidates: [], reason: options.length ? "" : "Selection required." } };
          if (!field.resource) { if (item.resolutions[field.key]) resolutions[field.key] = item.resolutions[field.key]; else delete resolutions[field.key]; }
          const invalidated = new Set([field.key]);
          for (let pass = 0; pass < 4; pass++) for (const [child, parents] of Object.entries(fieldDependencies[key] ?? {})) if (!invalidated.has(child) && Object.values(parents).some((parent) => invalidated.has(parent))) { delete resolutions[child]; values[child] = ""; invalidated.add(child); }
          return { ...item, state: "edited" as const, values, resolutions };
        }));
      }} /></div>)}
      <div className="prescription-card-buttons"><button type="button" className="secondary-button" disabled={busy || saved} onClick={() => setModify(true)}>Modify</button><button type="button" className="primary-button" disabled={busy || saved} onClick={() => { void save(); }}>{saved ? "Confirmed in draft" : busy ? "Saving…" : modify ? "Save modifications" : "Correct — save to draft"}</button></div>
    </>}
    {pendingRun !== null ? <p className="entry-field-help">Editing the latest extraction. Saving first loads it into an untouched draft; existing edits are protected.</p> : null}
    {error ? <p role="alert">{error}</p> : null}
  </div></div>;
}
