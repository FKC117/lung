import { useCallback, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, CheckCircle2, Clock3, Eye, FileText, Files, LoaderCircle, Play, Upload, XCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { ApiError, type PrescriptionDocument, fetchPrescriptionDocuments, processPrescriptionDocument, reprocessPrescriptionDocument, uploadPrescriptionDocument } from "../api";

import { PreviewPatientAction } from "../components/intake/PreviewPatientAction";
import { PreviewDraftAction, PreviewDraftEditContext } from "../components/intake/PreviewDraftAction";

const statusLabel: Record<PrescriptionDocument["status"], string> = { uploaded: "Waiting to queue", processing: "Extracting", ready_for_review: "Ready for correction", failed: "Extraction failed" };
const statusIcon = { uploaded: Clock3, processing: LoaderCircle, ready_for_review: CheckCircle2, failed: XCircle };
const internalExtractionKeys = new Set(["canonical_draft", "field_tracking", "gemini_extraction", "validation"]);
const clinicalSourceSignal = /\b(diagnosis|carcinoma|adenocarcinoma|small cell|histopathology|chemotherapy|radiotherapy|metastasis|metastatic|treatment)\b/i;

function formatDate(value: string | null) { return value ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—"; }
function friendlyFailure(reason?: string) {
  const text = (reason ?? "").toLowerCase();
  if (text.includes("molecular-exons") || text.includes("invalid scope")) return "The system could not prepare molecular test choices. This configuration issue has been corrected; retry extraction.";
  if (text.includes("google") || text.includes("gemini") || text.includes("503") || text.includes("unavailable")) return "The AI extraction service is temporarily unavailable. Please retry in a few minutes.";
  if (text.includes("tesseract") || text.includes("ocr")) return "The document could not be read clearly. Retry once; if it fails again, upload a clearer scan or PDF.";
  return "We could not process this document. Retry extraction; if it fails again, ask a registry administrator to review the processing log.";
}
function humanize(key: string) { return key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()); }
function hasExtractedValue(value: unknown) { return Array.isArray(value) ? value.length > 0 : value && typeof value === "object" ? Object.keys(value).length > 0 : value !== null && value !== undefined && value !== ""; }
function record(value: unknown): Record<string, unknown> | null { return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null; }
function geminiProblem(document: PrescriptionDocument) {
  const run = document.extraction_runs[0];
  const extracted = record(run?.structured_data);
  if (!run || !extracted) return null;
  if (extracted.gemini_status === "policy_blocked") return String(extracted.gemini_error || "Gemini transmission is disabled by the data policy. Local extraction is ready for review.");
  if (extracted.gemini_status === "unavailable") return String(extracted.gemini_error || "Gemini structured extraction was unavailable. Deterministic OCR evidence is ready for review.");
  const gemini = record(extracted.gemini_extraction);
  const unresolved = Array.isArray(gemini?.unresolved_items) ? gemini.unresolved_items.map(record) : [];
  // Supports documents extracted before gemini_status was added.
  if (unresolved.some((item) => item?.type === "structured_extraction")) return "Gemini structured extraction was unavailable. Deterministic OCR evidence is ready for review.";
  const hasClinicalSource = document.pages.some((page) => clinicalSourceSignal.test(page.cleaned_text || page.raw_text || ""));
  const hasClinicalObservation = Array.isArray(gemini?.observations) && gemini.observations.some((observation) => {
    const values = record(observation);
    return Boolean(values && Object.entries(values).some(([key, value]) => key !== "temporal_context" && hasExtractedValue(value)));
  });
  if (hasClinicalSource && !hasClinicalObservation) return "Gemini returned no clinical observations for this clinical prescription. Deterministic OCR evidence is ready for review.";
  return null;
}

function GeminiFact({ label, value }: { label: string; value: unknown }) {
  const fact = record(value);
  const isEvidence = Boolean(fact && "value" in fact && ("source_text" in fact || "page" in fact || "confidence" in fact));
  if (fact && isEvidence) return <article className="prescription-gemini-fact"><strong>{label}</strong><span>{String(fact.value ?? "Not supplied")}</span><small>{typeof fact.confidence === "number" ? `${Math.round(fact.confidence * 100)}% confidence` : "Confidence not supplied"}{fact.page ? ` · page ${fact.page}` : ""}</small>{fact.source_text ? <em>{String(fact.source_text)}</em> : null}</article>;
  if (Array.isArray(value)) return <div className="prescription-gemini-facts">{value.map((item, index) => <GeminiFact key={index} label={`${label} ${value.length > 1 ? index + 1 : ""}`.trim()} value={item} />)}</div>;
  if (fact) return <section className="prescription-gemini-composite"><h5>{label}</h5>{Object.entries(fact).map(([key, item]) => <GeminiFact key={key} label={humanize(key)} value={item} />)}</section>;
  return <article className="prescription-gemini-fact"><strong>{label}</strong><span>{value === null || value === undefined || value === "" ? "Not supplied" : String(value)}</span></article>;
}
function GeminiEvent({ observation, index, documentId }: { observation: Record<string, unknown>; index: number; documentId: number }) {
  const groups = Object.entries(observation).filter(([key, value]) => key !== "temporal_context" && hasExtractedValue(value));
  return <section className="prescription-gemini-event"><header><span>Event {index + 1}</span><strong>{String(observation.temporal_context ?? "unknown")}</strong></header>{groups.map(([key, value]) => <section className="prescription-gemini-group" key={key}><h5>{humanize(key)}</h5><PreviewDraftAction documentId={documentId} collection={key} eventIndex={index}>{(editing) => editing ? null : <GeminiFact label={humanize(key)} value={value} />}</PreviewDraftAction></section>)}</section>;
}
function ExtractionPreview({ document, onClose, onCorrect }: { document: PrescriptionDocument; onClose: () => void; onCorrect: () => void }) {
  const [editing, setEditing] = useState<Record<string, { dirty: boolean; busy: boolean }>>({});
  const report = useCallback((key: string, dirty: boolean, busy: boolean) => setEditing((current) => current[key]?.dirty === dirty && current[key]?.busy === busy ? current : { ...current, [key]: { dirty, busy } }), []);
  const close = () => {
    if (Object.values(editing).some((state) => state.busy)) return;
    if (Object.values(editing).some((state) => state.dirty) && !window.confirm("Discard unsaved dropdown choices and close?")) return;
    onClose();
  };
  const run = document.extraction_runs[0];
  const extracted = run?.structured_data && typeof run.structured_data === "object" ? run.structured_data as Record<string, unknown> : {};
  const gemini = record(extracted.gemini_extraction);
  const patient = record(gemini?.patient);
  const observations = Array.isArray(gemini?.observations) ? gemini.observations.map(record).filter((item): item is Record<string, unknown> => Boolean(item)) : [];
  const warnings = Array.isArray(gemini?.warnings) ? gemini.warnings : [];
  const unresolved = Array.isArray(gemini?.unresolved_items) ? gemini.unresolved_items : [];
  const geminiUnavailable = geminiProblem(document);
  const populatedSections = Object.entries(extracted).filter(([key, value]) => !internalExtractionKeys.has(key) && hasExtractedValue(value));
  return <PreviewDraftEditContext.Provider value={report}><div className="entry-modal-backdrop prescription-preview-backdrop" role="presentation" onMouseDown={close}>
    <section className="entry-modal prescription-extraction-preview" role="dialog" aria-modal="true" aria-labelledby="extraction-preview-title" onMouseDown={(event) => event.stopPropagation()}>
      <button className="entry-modal-close" type="button" onClick={close} aria-label="Close extracted data">×</button>
      <p className="eyebrow">Gemini extraction · review cards</p><h3 id="extraction-preview-title">{document.original_filename}</h3>
      <p>Check each card, choose any dropdown values, then confirm or modify its draft data. Original Gemini evidence is preserved.</p>
      {geminiUnavailable ? <section className="prescription-preview-section prescription-gemini-alerts"><h4><AlertTriangle size={16} /> Gemini suggestions unavailable</h4><p>{geminiUnavailable}</p><p>OCR evidence is still available. Re-run extraction to request a new Gemini response.</p></section> : null}
      {gemini ? <div className="prescription-gemini-preview">
        {patient && Object.keys(patient).length ? <section className="prescription-preview-section"><div className="prescription-preview-heading"><div><p className="eyebrow">Patient</p><h4>Patient identity</h4></div></div><PreviewPatientAction documentId={document.id}>{(editing) => editing ? null : <div className="prescription-gemini-facts">{Object.entries(patient).map(([key, value]) => <GeminiFact key={key} label={humanize(key)} value={value} />)}</div>}</PreviewPatientAction></section> : null}
        {observations.length ? <section className="prescription-preview-section"><div className="prescription-preview-heading"><div><p className="eyebrow">Clinical timeline</p><h4>{observations.length} extracted observation{observations.length === 1 ? "" : "s"}</h4></div></div><div className="prescription-gemini-events">{observations.map((observation, index) => <GeminiEvent key={index} observation={observation} index={index} documentId={document.id} />)}</div></section> : null}
        {warnings.length || unresolved.length ? <section className="prescription-preview-section prescription-gemini-alerts"><h4>Needs review</h4>{warnings.map((item, index) => <p key={`warning-${index}`}>{String(item)}</p>)}{unresolved.map((item, index) => <p key={`unresolved-${index}`}>{record(item)?.reason ? String(record(item)?.reason) : String(item)}</p>)}</section> : null}
        <details className="prescription-gemini-raw"><summary>View exact Gemini JSON</summary><pre>{JSON.stringify(gemini, null, 2)}</pre></details>
      </div> : populatedSections.length ? <section className="prescription-preview-section"><h4>Structured Gemini extraction is not available</h4><p className="hero-text">The deterministic extraction is available below. Gemini may be unconfigured or its request may have failed.</p><details className="prescription-gemini-raw"><summary>View deterministic extraction data</summary><pre>{JSON.stringify(Object.fromEntries(populatedSections), null, 2)}</pre></details></section> : <p className="hero-text">No structured suggestions are available yet. You can retry extraction from the history list.</p>}
      <div className="prescription-preview-actions"><button className="secondary-button" type="button" onClick={close}>Close</button><button className="primary-button" type="button" onClick={() => { if (Object.values(editing).some((state) => state.busy)) return; if (Object.values(editing).some((state) => state.dirty) && !window.confirm("Discard unsaved dropdown choices and open the full review?")) return; onCorrect(); }}>Review & correct <ArrowRight size={15} /></button></div>
    </section>
  </div></PreviewDraftEditContext.Provider>;
}

type UploadState = "waiting" | "uploading" | "queued" | "duplicate" | "failed";
type UploadProgress = Record<string, { state: UploadState; message?: string }>;
const fileKey = (file: File) => `${file.name}-${file.size}-${file.lastModified}`;

export default function PrescriptionReviewPage() {
  const navigate = useNavigate(); const queryClient = useQueryClient(); const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]); const [progress, setProgress] = useState<UploadProgress>({}); const [previewDocument, setPreviewDocument] = useState<PrescriptionDocument | null>(null);
  const documentsQuery = useQuery({ queryKey: ["prescription-documents"], queryFn: fetchPrescriptionDocuments, refetchInterval: (query) => query.state.data?.some((document) => document.status === "processing") ? 4000 : false });
  const documents = documentsQuery.data ?? [];
  const summary = useMemo(() => ({ total: documents.length, extracting: documents.filter((document) => document.status === "processing").length, ready: documents.filter((document) => document.status === "ready_for_review").length, failed: documents.filter((document) => document.status === "failed").length, geminiUnavailable: documents.filter((document) => Boolean(geminiProblem(document))).length }), [documents]);
  const uploadMutation = useMutation({ mutationFn: async () => { for (const file of files) { const key = fileKey(file); setProgress((current) => ({ ...current, [key]: { state: "uploading" } })); try { const document = await uploadPrescriptionDocument(file); await processPrescriptionDocument(document.id); setProgress((current) => ({ ...current, [key]: { state: "queued", message: "Queued for OCR and Gemini extraction" } })); } catch (error) { const duplicate = error instanceof ApiError && error.status === 409; setProgress((current) => ({ ...current, [key]: { state: duplicate ? "duplicate" : "failed", message: duplicate ? "Already uploaded — identical file content was skipped" : error instanceof Error ? error.message : "Upload failed" } })); } } await queryClient.invalidateQueries({ queryKey: ["prescription-documents"] }); } });
  const retryMutation = useMutation({ mutationFn: processPrescriptionDocument, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["prescription-documents"] }) });
  const reprocessMutation = useMutation({ mutationFn: reprocessPrescriptionDocument, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["prescription-documents"] }) });
  function chooseFiles(nextFiles: FileList | null) { const selected = Array.from(nextFiles ?? []); setFiles(selected); setProgress(Object.fromEntries(selected.map((file) => [fileKey(file), { state: "waiting" as const }]))); }
  const openReview = (documentId: number) => navigate(`/prescriptions/${documentId}/review`);
  return <section className="page-grid prescription-intake-page">
    <section className="hero-panel prescription-intake-hero"><div className="hero-copy"><p className="eyebrow">Prescription intake</p><h2>Upload the backlog. We process it in the background.</h2><p className="hero-text">This page is for intake and upload history. Clinical correction happens in the dedicated prescription review workspace after extraction is ready.</p></div><div className="prescription-intake-stats"><span><strong>{summary.total}</strong> uploaded</span><span><strong>{summary.extracting}</strong> extracting</span><span><strong>{summary.ready}</strong> ready</span>{summary.geminiUnavailable ? <span className="prescription-gemini-unavailable-count"><strong>{summary.geminiUnavailable}</strong> Gemini retry needed</span> : null}</div></section>
    <section className="panel prescription-bulk-upload"><div className="prescription-upload-copy"><p className="eyebrow">Bulk upload</p><h3>Drop a set of prescriptions here</h3><p className="hero-text">PDF, image, or text files. Each document is checksummed, uploaded, and queued for OCR + Gemini automatically.</p></div><div className="prescription-upload-actions"><input ref={inputRef} className="prescription-hidden-input" type="file" multiple accept="application/pdf,image/*,text/plain" onChange={(event) => chooseFiles(event.target.files)} /><button type="button" className="secondary-button prescription-choose-files" onClick={() => inputRef.current?.click()}><Files size={18} />Choose files</button><button type="button" className="primary-button" disabled={!files.length || uploadMutation.isPending} onClick={() => uploadMutation.mutate()}><Upload size={18} />{uploadMutation.isPending ? "Queueing files…" : `Upload${files.length ? ` ${files.length} file${files.length === 1 ? "" : "s"}` : ""}`}</button></div>{files.length ? <div className="prescription-upload-list" aria-live="polite">{files.map((file) => { const item = progress[fileKey(file)] ?? { state: "waiting" as const }; return <article key={fileKey(file)} className={`prescription-upload-item is-${item.state}`}><FileText size={17} /><span><strong>{file.name}</strong><small>{item.message ?? (item.state === "waiting" ? "Ready to upload" : item.state === "uploading" ? "Uploading…" : item.state === "queued" ? "Queued" : "Failed")}</small></span></article>; })}</div> : <button type="button" className="prescription-drop-target" onClick={() => inputRef.current?.click()}><Upload size={22} /><span>Choose one or many prescription files</span><small>Duplicate files are safely skipped by checksum.</small></button>}</section>
    <section className="panel prescription-history">
      <div className="panel-heading"><div><p className="eyebrow">Uploaded previously</p><h3>Prescription history</h3><p className="hero-text">Preview the extracted suggestions, then open the prescription review workspace when a document is ready.</p></div>{summary.failed || summary.geminiUnavailable ? <span className="data-pill prescription-failed-count">{summary.failed + summary.geminiUnavailable} needs attention</span> : null}</div>
      {documentsQuery.isLoading ? <p className="hero-text">Loading uploads…</p> : null}
      {!documentsQuery.isLoading && !documents.length ? <div className="prescription-history-empty"><Files size={28} /><p>No prescriptions uploaded yet.</p></div> : null}
      <div className="prescription-history-list">{documents.map((document) => {
        const Icon = statusIcon[document.status];
        const latestRun = document.extraction_runs[0];
        const failureReason = latestRun?.error || latestRun?.issues.find((issue) => issue.severity === "error")?.message || document.issues.find((issue) => issue.severity === "error")?.message;
        const geminiUnavailable = geminiProblem(document);
        const published = Boolean(document.review?.published_at);
        return <article className={`prescription-history-row${document.status === "failed" ? " is-failed" : ""}${geminiUnavailable ? " is-gemini-unavailable" : ""}`} key={document.id}>
          <span className={`prescription-history-status is-${document.status}${geminiUnavailable ? " is-gemini-unavailable" : ""}`}>{geminiUnavailable ? <AlertTriangle size={18} /> : <Icon size={18} />}</span>
          <div className="prescription-history-file"><strong>{document.original_filename}</strong><small>{formatDate(document.created_at)} · {document.page_count ? `${document.page_count} page${document.page_count === 1 ? "" : "s"}` : "Awaiting OCR"}{latestRun?.ai_model ? ` · ${latestRun.ai_model}` : ""}</small></div>
          <span className={`prescription-history-state is-${document.status}${geminiUnavailable ? " is-gemini-unavailable" : ""}`}>{published ? "Published" : geminiUnavailable ? "Gemini retry needed" : statusLabel[document.status]}</span>
          <div className="prescription-history-actions">{document.status === "uploaded" || document.status === "failed" ? <button type="button" className="secondary-button" disabled={retryMutation.isPending} onClick={() => retryMutation.mutate(document.id)}><Play size={15} />{document.status === "failed" ? "Re-run extraction" : "Queue extraction"}</button> : null}{document.status === "ready_for_review" ? <><button type="button" className="secondary-button" onClick={() => setPreviewDocument(document)}><Eye size={15} />View extracted data</button>{(!document.review || (geminiUnavailable && !published)) ? <button type="button" className="secondary-button" disabled={reprocessMutation.isPending} onClick={() => reprocessMutation.mutate(document.id)}><Play size={15} />Re-run extraction</button> : <span className="prescription-rerun-locked" title="Re-running is available only when Gemini extraction has a quality issue; published provenance is never changed."><Play size={15} /><span><strong>Re-run locked</strong><small>{published ? "Already published" : "Correction has started"}</small></span></span>}{!published ? <button type="button" className="primary-button" onClick={() => openReview(document.id)}>{document.review ? "Continue review" : "Review & correct"} <ArrowRight size={15} /></button> : null}</> : null}</div>
          {geminiUnavailable ? <p className="prescription-gemini-unavailable-reason"><strong>Gemini needs attention:</strong> {geminiUnavailable}</p> : null}
          {document.status === "failed" ? <p className="prescription-failure-reason"><strong>What you can do:</strong> {friendlyFailure(failureReason)}</p> : null}
        </article>;
      })}</div>
      {uploadMutation.error ? <p className="prescription-error">{uploadMutation.error.message}</p> : null}{retryMutation.error ? <p className="prescription-error">{retryMutation.error.message}</p> : null}{reprocessMutation.error ? <p className="prescription-error">{reprocessMutation.error.message}</p> : null}
    </section>
    {previewDocument ? <ExtractionPreview document={previewDocument} onClose={() => setPreviewDocument(null)} onCorrect={() => openReview(previewDocument.id)} /> : null}
  </section>;
}
