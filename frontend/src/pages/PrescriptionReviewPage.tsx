import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, CheckCircle2, Clock3, Eye, FileText, Files, LoaderCircle, Play, Upload, XCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { ApiError, type PrescriptionDocument, fetchPrescriptionDocuments, processPrescriptionDocument, reprocessPrescriptionDocument, uploadPrescriptionDocument } from "../api";

const statusLabel: Record<PrescriptionDocument["status"], string> = {
  uploaded: "Waiting to queue", processing: "Extracting", ready_for_review: "Ready for correction", failed: "Extraction failed",
};
const statusIcon = { uploaded: Clock3, processing: LoaderCircle, ready_for_review: CheckCircle2, failed: XCircle };
const internalExtractionKeys = new Set(["canonical_draft", "field_tracking", "gemini_extraction", "validation"]);

function formatDate(value: string | null) { return value ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—"; }
function friendlyFailure(reason?: string) {
  const text = (reason ?? "").toLowerCase();
  if (text.includes("molecular-exons") || text.includes("invalid scope")) return "The system could not prepare molecular test choices. This configuration issue has been corrected; retry extraction.";
  if (text.includes("google") || text.includes("gemini") || text.includes("503") || text.includes("unavailable")) return "The AI extraction service is temporarily unavailable. Please retry in a few minutes.";
  if (text.includes("tesseract") || text.includes("ocr")) return "The document could not be read clearly. Retry once; if it fails again, upload a clearer scan or PDF.";
  return "We could not process this document. Retry extraction; if it fails again, ask a registry administrator to review the processing log.";
}
function humanize(key: string) { return key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()); }
function hasExtractedValue(value: unknown) {
  return Array.isArray(value) ? value.length > 0 : value && typeof value === "object" ? Object.keys(value).length > 0 : value !== null && value !== undefined && value !== "";
}

function ExtractedValue({ value, depth = 0 }: { value: unknown; depth?: number }) {
  if (value === null || value === undefined || value === "") return <span className="prescription-empty-value">Not supplied</span>;
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return <span>{String(value)}</span>;
  if (depth >= 5) return <span>{String(value)}</span>;
  if (Array.isArray(value)) return <div className="prescription-extracted-list">{value.map((item, index) => <article key={index} className="prescription-extracted-item"><span className="prescription-extracted-item-number">{index + 1}</span><ExtractedValue value={item} depth={depth + 1} /></article>)}</div>;
  if (typeof value === "object") return <dl className="prescription-extracted-fields">{Object.entries(value as Record<string, unknown>).map(([key, item]) => <div key={key}><dt>{humanize(key)}</dt><dd><ExtractedValue value={item} depth={depth + 1} /></dd></div>)}</dl>;
  return <span>{String(value)}</span>;
}

function ExtractionPreview({ document, onClose, onCorrect }: { document: PrescriptionDocument; onClose: () => void; onCorrect: () => void }) {
  const run = document.extraction_runs[0];
  const extracted = run?.structured_data && typeof run.structured_data === "object" ? run.structured_data as Record<string, unknown> : {};
  const populatedSections = Object.entries(extracted)
    .filter(([key, value]) => !internalExtractionKeys.has(key) && hasExtractedValue(value));
  return <div className="entry-modal-backdrop prescription-preview-backdrop" role="presentation" onMouseDown={onClose}>
    <section className="entry-modal prescription-extraction-preview" role="dialog" aria-modal="true" aria-labelledby="extraction-preview-title" onMouseDown={(event) => event.stopPropagation()}>
      <button className="entry-modal-close" type="button" onClick={onClose} aria-label="Close extracted data">×</button>
      <p className="eyebrow">Complete extracted data · read only</p><h3 id="extraction-preview-title">{document.original_filename}</h3>
      <p>Every extracted clinical suggestion is shown below. Nothing here has been saved as a clinical record. Confirm or correct the information in New Entry.</p>
      {populatedSections.length ? <div className="prescription-preview-sections">{populatedSections.map(([key, value]) => <section key={key} className="prescription-preview-section"><h4>{humanize(key)}</h4><ExtractedValue value={value} /></section>)}</div> : <p className="hero-text">No structured suggestions are available yet. You can retry extraction from the history list.</p>}
      <div className="prescription-preview-actions"><button className="secondary-button" type="button" onClick={onClose}>Close</button><button className="primary-button" type="button" onClick={onCorrect}>Correct in New Entry <ArrowRight size={15} /></button></div>
    </section>
  </div>;
}

type UploadState = "waiting" | "uploading" | "queued" | "duplicate" | "failed";
type UploadProgress = Record<string, { state: UploadState; message?: string }>;
const fileKey = (file: File) => `${file.name}-${file.size}-${file.lastModified}`;

export default function PrescriptionReviewPage() {
  const navigate = useNavigate(); const queryClient = useQueryClient(); const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]); const [progress, setProgress] = useState<UploadProgress>({}); const [previewDocument, setPreviewDocument] = useState<PrescriptionDocument | null>(null);
  const documentsQuery = useQuery({ queryKey: ["prescription-documents"], queryFn: fetchPrescriptionDocuments, refetchInterval: (query) => query.state.data?.some((document) => document.status === "processing") ? 4000 : false });
  const documents = documentsQuery.data ?? [];
  const summary = useMemo(() => ({ total: documents.length, extracting: documents.filter((document) => document.status === "processing").length, ready: documents.filter((document) => document.status === "ready_for_review").length, failed: documents.filter((document) => document.status === "failed").length }), [documents]);
  const uploadMutation = useMutation({ mutationFn: async () => { for (const file of files) { const key = fileKey(file); setProgress((current) => ({ ...current, [key]: { state: "uploading" } })); try { const document = await uploadPrescriptionDocument(file); await processPrescriptionDocument(document.id); setProgress((current) => ({ ...current, [key]: { state: "queued", message: "Queued for OCR and Gemini extraction" } })); } catch (error) { const duplicate = error instanceof ApiError && error.status === 409; setProgress((current) => ({ ...current, [key]: { state: duplicate ? "duplicate" : "failed", message: duplicate ? "Already uploaded — identical file content was skipped" : error instanceof Error ? error.message : "Upload failed" } })); } } await queryClient.invalidateQueries({ queryKey: ["prescription-documents"] }); } });
  const retryMutation = useMutation({ mutationFn: processPrescriptionDocument, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["prescription-documents"] }) });
  const reprocessMutation = useMutation({ mutationFn: reprocessPrescriptionDocument, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["prescription-documents"] }) });
  function chooseFiles(nextFiles: FileList | null) { const selected = Array.from(nextFiles ?? []); setFiles(selected); setProgress(Object.fromEntries(selected.map((file) => [fileKey(file), { state: "waiting" as const }]))); }
  return <section className="page-grid prescription-intake-page">
    <section className="hero-panel prescription-intake-hero"><div className="hero-copy"><p className="eyebrow">Prescription intake</p><h2>Upload the backlog. We process it in the background.</h2><p className="hero-text">This page is only for intake and upload history. Clinical correction happens in New Entry after extraction is ready.</p></div><div className="prescription-intake-stats"><span><strong>{summary.total}</strong> uploaded</span><span><strong>{summary.extracting}</strong> extracting</span><span><strong>{summary.ready}</strong> ready</span></div></section>
    <section className="panel prescription-bulk-upload"><div className="prescription-upload-copy"><p className="eyebrow">Bulk upload</p><h3>Drop a set of prescriptions here</h3><p className="hero-text">PDF, image, or text files. Each document is checksummed, uploaded, and queued for OCR + Gemini automatically.</p></div><div className="prescription-upload-actions"><input ref={inputRef} className="prescription-hidden-input" type="file" multiple accept="application/pdf,image/*,text/plain" onChange={(event) => chooseFiles(event.target.files)} /><button type="button" className="secondary-button prescription-choose-files" onClick={() => inputRef.current?.click()}><Files size={18} />Choose files</button><button type="button" className="primary-button" disabled={!files.length || uploadMutation.isPending} onClick={() => uploadMutation.mutate()}><Upload size={18} />{uploadMutation.isPending ? "Queueing files…" : `Upload${files.length ? ` ${files.length} file${files.length === 1 ? "" : "s"}` : ""}`}</button></div>{files.length ? <div className="prescription-upload-list" aria-live="polite">{files.map((file) => { const item = progress[fileKey(file)] ?? { state: "waiting" as const }; return <article key={fileKey(file)} className={`prescription-upload-item is-${item.state}`}><FileText size={17} /><span><strong>{file.name}</strong><small>{item.message ?? (item.state === "waiting" ? "Ready to upload" : item.state === "uploading" ? "Uploading…" : item.state === "queued" ? "Queued" : "Failed")}</small></span></article>; })}</div> : <button type="button" className="prescription-drop-target" onClick={() => inputRef.current?.click()}><Upload size={22} /><span>Choose one or many prescription files</span><small>Duplicate files are safely skipped by checksum.</small></button>}</section>
    <section className="panel prescription-history"><div className="panel-heading"><div><p className="eyebrow">Uploaded previously</p><h3>Prescription history</h3><p className="hero-text">Preview extracted suggestions, then open New Entry only when a document is ready for correction.</p></div>{summary.failed ? <span className="data-pill prescription-failed-count">{summary.failed} needs attention</span> : null}</div>{documentsQuery.isLoading ? <p className="hero-text">Loading uploads…</p> : null}{!documentsQuery.isLoading && !documents.length ? <div className="prescription-history-empty"><Files size={28} /><p>No prescriptions uploaded yet.</p></div> : null}<div className="prescription-history-list">{documents.map((document) => { const Icon = statusIcon[document.status]; const latestRun = document.extraction_runs[0]; const failureReason = latestRun?.error || latestRun?.issues.find((issue) => issue.severity === "error")?.message || document.issues.find((issue) => issue.severity === "error")?.message; return <article className={`prescription-history-row${document.status === "failed" ? " is-failed" : ""}`} key={document.id}><span className={`prescription-history-status is-${document.status}`}><Icon size={18} /></span><div className="prescription-history-file"><strong>{document.original_filename}</strong><small>{formatDate(document.created_at)} · {document.page_count ? `${document.page_count} page${document.page_count === 1 ? "" : "s"}` : "Awaiting OCR"}{latestRun?.ai_model ? ` · ${latestRun.ai_model}` : ""}</small></div><span className={`prescription-history-state is-${document.status}`}>{statusLabel[document.status]}</span><div className="prescription-history-actions">{document.status === "uploaded" || document.status === "failed" ? <button type="button" className="secondary-button" disabled={retryMutation.isPending} onClick={() => retryMutation.mutate(document.id)}><Play size={15} />{document.status === "failed" ? "Retry extraction" : "Queue extraction"}</button> : null}{document.status === "ready_for_review" ? <><button type="button" className="secondary-button" onClick={() => setPreviewDocument(document)}><Eye size={15} />View extracted data</button>{!document.review ? <button type="button" className="secondary-button" disabled={reprocessMutation.isPending} onClick={() => reprocessMutation.mutate(document.id)}><Play size={15} />Re-run extraction</button> : null}<button type="button" className="primary-button" onClick={() => navigate(`/entries/new?prescription_document=${document.id}`)}>Correct in New Entry <ArrowRight size={15} /></button></> : null}</div>{document.status === "failed" ? <p className="prescription-failure-reason"><strong>What you can do:</strong> {friendlyFailure(failureReason)}</p> : null}</article>; })}</div>{uploadMutation.error ? <p className="prescription-error">{uploadMutation.error.message}</p> : null}{retryMutation.error ? <p className="prescription-error">{retryMutation.error.message}</p> : null}{reprocessMutation.error ? <p className="prescription-error">{reprocessMutation.error.message}</p> : null}</section>
    {previewDocument ? <ExtractionPreview document={previewDocument} onClose={() => setPreviewDocument(null)} onCorrect={() => navigate(`/entries/new?prescription_document=${previewDocument.id}`)} /> : null}
  </section>;
}
