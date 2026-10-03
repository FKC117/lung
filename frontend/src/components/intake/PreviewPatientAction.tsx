import { useContext, useEffect, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { fetchEntriesOptions, startPrescriptionReview, updatePrescriptionReview, type PrescriptionReview } from "../../api";
import { patientFieldSchema, authoritativeOptionResources } from "./observationFieldSchema";
import { IntakeTextField, IntakeSelectField } from "./SharedIntakeFields";
import { PreviewDraftEditContext } from "./PreviewDraftAction";

export function PreviewPatientAction({ documentId, children }: { documentId: number; children?: (editing: boolean) => ReactNode }) {
 const client = useQueryClient(); const report = useContext(PreviewDraftEditContext);
 const [review, setReview] = useState<PrescriptionReview | null>(null);
 const [values, setValues] = useState<Record<string, unknown>>({});
 const [catalog, setCatalog] = useState<Awaited<ReturnType<typeof fetchEntriesOptions>>>({});
 const [modify, setModify] = useState(false); const [dirty, setDirty] = useState(false);
 const [busy, setBusy] = useState(false); const [saved, setSaved] = useState(false); const [error, setError] = useState("");
 useEffect(() => { report("patient", dirty, busy); }, [dirty, busy, report]);
 const prepare = async () => {
  const current = await startPrescriptionReview(documentId);
  if (!["draft", "in_review"].includes(current.status) || current.published_at) throw new Error("This review is locked.");
  const choices = await fetchEntriesOptions(authoritativeOptionResources);
  setReview(current); setValues(current.reviewed_data.patient.values); setCatalog(choices);
  return current;
 };
 const confirm = async () => {
  setBusy(true); setError("");
  try {
   const current = review ?? await prepare();
   const patientValues = review ? values : current.reviewed_data.patient.values;
   if (patientFieldSchema.some((field) => field.resource && patientValues[field.key] != null && patientValues[field.key] !== "" && !Number.isInteger(Number(patientValues[field.key])))) { setModify(true); throw new Error("Choose the patient dropdown values before confirming."); }
   const result = await updatePrescriptionReview(documentId, { expected_revision: current.revision, reviewed_data: { ...current.reviewed_data, patient: { ...current.reviewed_data.patient, values: patientValues } } });
   setReview(result); setSaved(true); setDirty(false);
   await client.invalidateQueries({ queryKey: ["prescription-documents"] });
   await client.invalidateQueries({ queryKey: ["prescription-document", documentId] });
  } catch (exception) { setError(exception instanceof Error ? exception.message : "Could not save patient details."); }
  finally { setBusy(false); }
 };
 return <div className="prescription-segment-review">{children?.(modify && Boolean(review))}<div className="prescription-card-action">
  {modify && review ? <div className="entry-grid">{patientFieldSchema.filter((field) => field.key in values).map((field) => field.resource ? <IntakeSelectField key={field.key} label={field.label} value={Number.isInteger(Number(values[field.key])) && values[field.key] !== "" ? String(values[field.key]) : ""} options={catalog[field.resource] ?? []} disabled={busy || saved} help={!(catalog[field.resource] ?? []).length ? "No configured options. Original extracted value is preserved above." : undefined} onChange={(value, option) => { setValues((previous) => ({ ...previous, [field.key]: option?.id ?? value })); setDirty(true); }} /> : <IntakeTextField key={field.key} label={field.label} type={field.type ?? "text"} value={String(values[field.key] ?? "")} disabled={busy || saved} onChange={(value) => { setValues((previous) => ({ ...previous, [field.key]: value })); setDirty(true); }} />)}</div> : null}
  <div className="prescription-card-buttons"><button type="button" className="primary-button" disabled={busy || saved} onClick={() => { void confirm(); }}>{saved ? "Confirmed in draft" : busy ? "Saving…" : modify ? "Save modifications" : "Correct — save to draft"}</button><button type="button" className="secondary-button" disabled={busy || saved} onClick={async () => { setBusy(true); setError(""); try { await prepare(); setModify(true); } catch (exception) { setError(exception instanceof Error ? exception.message : "Could not open patient choices."); } finally { setBusy(false); } }}>Modify</button></div>
  <small className="entry-field-help">Confirms profile details in the draft. Select the registry patient explicitly before final approval.</small>
  {error ? <p role="alert">{error}</p> : null}
 </div></div>;
}
