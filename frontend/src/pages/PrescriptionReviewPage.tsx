import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Check, FileText, Play, Save, ShieldCheck, Upload, XCircle } from "lucide-react";

import {
  type PrescriptionDocument,
  approvePrescriptionReview,
  fetchPrescriptionDocuments,
  processPrescriptionDocument,
  rejectPrescriptionReview,
  startPrescriptionReview,
  updatePrescriptionReview,
  uploadPrescriptionDocument,
} from "../api";

const statusLabel: Record<PrescriptionDocument["status"], string> = {
  uploaded: "Ready to extract",
  processing: "Processing",
  ready_for_review: "Ready for review",
  failed: "Processing failed",
};

function formatDate(value: string | null) {
  return value ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—";
}

type ReviewData = Record<string, unknown>;

function displayLabel(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function setReviewValue(data: ReviewData, path: Array<string | number>, nextValue: unknown): ReviewData {
  const copy = structuredClone(data) as ReviewData;
  let target: Record<string | number, unknown> = copy;
  path.slice(0, -1).forEach((part) => { target = target[part] as Record<string | number, unknown>; });
  target[path[path.length - 1]] = nextValue;
  return copy;
}

function ReviewField({ label, value, path, onChange }: { label: string; value: unknown; path: Array<string | number>; onChange: (path: Array<string | number>, value: unknown) => void }) {
  if (Array.isArray(value)) return <section className="prescription-review-group"><h4>{displayLabel(label)}</h4>{value.length ? value.map((item, index) => <ReviewField key={index} label={`${displayLabel(label)} ${index + 1}`} value={item} path={[...path, index]} onChange={onChange} />) : <p className="hero-text">None extracted.</p>}</section>;
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    if ("value" in record) {
      const confidence = typeof record.confidence === "number" ? Math.round(record.confidence * 100) : null;
      return <label className="prescription-evidence-field"><span>{displayLabel(label)}</span><input className="auth-input" value={String(record.value ?? "")} onChange={(event) => onChange([...path, "value"], event.target.value)} /><small>{confidence !== null ? `${confidence}% confidence` : "Confidence not supplied"}{record.page ? ` · page ${record.page}` : ""}</small>{record.source_text ? <em>{String(record.source_text)}</em> : null}</label>;
    }
    return <section className="prescription-review-group"><h4>{displayLabel(label)}</h4>{Object.entries(record).filter(([key]) => !["source_text", "page", "confidence", "start", "end"].includes(key)).map(([key, item]) => <ReviewField key={key} label={key} value={item} path={[...path, key]} onChange={onChange} />)}</section>;
  }
  return <label className="prescription-evidence-field"><span>{displayLabel(label)}</span><input className="auth-input" value={value === null || value === undefined ? "" : String(value)} onChange={(event) => onChange(path, event.target.value)} /></label>;
}

export default function PrescriptionReviewPage() {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedPage, setSelectedPage] = useState(0);
  const [reviewedData, setReviewedData] = useState<ReviewData>({});
  const [reviewNotes, setReviewNotes] = useState("");
  const [patientId, setPatientId] = useState("");
  const [reviewError, setReviewError] = useState("");
  const [readyToApprove, setReadyToApprove] = useState(false);
  const documentsQuery = useQuery({ queryKey: ["prescription-documents"], queryFn: fetchPrescriptionDocuments });
  const documents = documentsQuery.data ?? [];
  const selected = useMemo(
    () => documents.find((document) => document.id === selectedId) ?? documents[0] ?? null,
    [documents, selectedId],
  );
  const latestRun = selected?.extraction_runs[0];
  const page = selected?.pages[selectedPage] ?? selected?.pages[0];
  const reviewIssues = useMemo(() => {
    const issues = [...(selected?.issues ?? []), ...(latestRun?.issues ?? [])];
    return issues.filter(
      (issue, index) =>
        index === issues.findIndex((candidate) =>
          candidate.code === issue.code &&
          candidate.page_number === issue.page_number &&
          candidate.message === issue.message,
        ),
    );
  }, [latestRun?.issues, selected?.issues]);

  useEffect(() => setSelectedPage(0), [selected?.id]);
  useEffect(() => {
    const data = selected?.review?.reviewed_data ?? latestRun?.structured_data ?? {};
    setReviewedData(data);
    setReviewNotes(selected?.review?.notes ?? "");
    setPatientId(selected?.review?.selected_patient ? String(selected.review.selected_patient) : "");
    setReviewError("");
    setReadyToApprove(false);
  }, [selected?.id, selected?.review?.updated_at, latestRun?.id]);

  const uploadMutation = useMutation({
    mutationFn: () => uploadPrescriptionDocument(file!),
    onSuccess: (document) => {
      setFile(null);
      setSelectedId(document.id);
      void queryClient.invalidateQueries({ queryKey: ["prescription-documents"] });
    },
  });
  const processMutation = useMutation({
    mutationFn: processPrescriptionDocument,
    onSuccess: (document) => {
      setSelectedId(document.id);
      void queryClient.invalidateQueries({ queryKey: ["prescription-documents"] });
    },
  });
  const refreshDocuments = async () => queryClient.invalidateQueries({ queryKey: ["prescription-documents"] });
  const startReviewMutation = useMutation({ mutationFn: startPrescriptionReview, onSuccess: refreshDocuments });
  const saveReviewMutation = useMutation({ mutationFn: ({ documentId, data }: { documentId: number; data: Record<string, unknown> }) => updatePrescriptionReview(documentId, { reviewed_data: data, notes: reviewNotes, selected_patient: patientId ? Number(patientId) : null }), onSuccess: refreshDocuments });
  const approveReviewMutation = useMutation({ mutationFn: approvePrescriptionReview, onSuccess: refreshDocuments });
  const rejectReviewMutation = useMutation({ mutationFn: ({ documentId, reason }: { documentId: number; reason: string }) => rejectPrescriptionReview(documentId, reason), onSuccess: refreshDocuments });

  function saveReview() {
    if (!selected) return;
    setReviewError("");
    saveReviewMutation.mutate({ documentId: selected.id, data: reviewedData });
  }

  return (
    <section className="page-grid prescription-workspace">
      <section className="hero-panel hero-panel-tight">
        <div className="hero-copy">
          <p className="eyebrow">Prescription intake</p>
          <h2>Extract, review, then decide</h2>
          <p className="hero-text">Prescription data stays outside clinical records until a reviewer has checked every proposed item and its source evidence.</p>
        </div>
        <span className="data-pill"><ShieldCheck size={16} /> Human review required</span>
      </section>

      <section className="panel prescription-upload-panel">
        <div>
          <p className="eyebrow">1. Upload</p>
          <h3>Prescription document</h3>
          <p className="hero-text">PDF, image, or text. Duplicate files are rejected by the registry checksum.</p>
        </div>
        <label className="prescription-file-picker">
          <Upload size={20} />
          <span>{file ? file.name : "Choose a prescription"}</span>
          <input type="file" accept="application/pdf,image/*,text/plain" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
        </label>
        <button type="button" className="primary-button" disabled={!file || uploadMutation.isPending} onClick={() => uploadMutation.mutate()}>
          <Upload size={16} /> {uploadMutation.isPending ? "Uploading…" : "Upload for extraction"}
        </button>
        {uploadMutation.error ? <p className="prescription-error">{uploadMutation.error.message}</p> : null}
      </section>

      <section className="prescription-layout">
        <aside className="panel prescription-queue">
          <div className="panel-heading"><div><p className="eyebrow">Review queue</p><h3>Documents</h3></div><span className="data-pill">{documents.length}</span></div>
          {documentsQuery.isLoading ? <p className="hero-text">Loading documents…</p> : null}
          {documents.map((document) => (
            <button type="button" key={document.id} className={`prescription-queue-item${selected?.id === document.id ? " is-selected" : ""}`} onClick={() => setSelectedId(document.id)}>
              <FileText size={18} />
              <span><strong>{document.original_filename}</strong><small>{formatDate(document.created_at)} · {statusLabel[document.status]}</small></span>
            </button>
          ))}
          {!documentsQuery.isLoading && !documents.length ? <p className="hero-text">No prescription documents have been uploaded.</p> : null}
        </aside>

        <section className="panel prescription-review">
          {!selected ? <div className="prescription-empty"><FileText size={34} /><h3>Select or upload a prescription</h3><p>Its OCR text, extraction result, and validation warnings will appear here.</p></div> : <>
            <div className="panel-heading">
              <div><p className="eyebrow">2. Extraction and review</p><h3>{selected.original_filename}</h3><p className="hero-text">{selected.page_count || selected.pages.length || "No"} page{(selected.page_count || selected.pages.length) === 1 ? "" : "s"} · {statusLabel[selected.status]}</p></div>
              {selected.status === "uploaded" ? <button type="button" className="primary-button" disabled={processMutation.isPending} onClick={() => processMutation.mutate(selected.id)}><Play size={16} /> {processMutation.isPending ? "Extracting…" : "Run extraction"}</button> : null}
            </div>
            {processMutation.error ? <p className="prescription-error">{processMutation.error.message}</p> : null}
            {reviewIssues.length ? <section className="prescription-issues"><AlertTriangle size={18} /><div><strong>Validation needs review</strong>{reviewIssues.map((issue) => <p key={`${issue.code}-${issue.page_number ?? "document"}-${issue.message}`}>{issue.page_number ? `Page ${issue.page_number}: ` : ""}{issue.message}</p>)}</div></section> : null}
            <div className="prescription-split-view">
              <section className="prescription-source">
                <div className="prescription-subheading"><h3>Source evidence</h3>{selected.pages.length > 1 ? <select className="filter-select" value={selectedPage} onChange={(event) => setSelectedPage(Number(event.target.value))}>{selected.pages.map((item, index) => <option value={index} key={item.id}>Page {item.page_number}</option>)}</select> : null}</div>
                {page?.image ? <img className="prescription-page-image" src={page.image} alt={`Prescription page ${page.page_number}`} /> : null}
                <pre className="prescription-ocr-text">{page?.cleaned_text || page?.raw_text || "OCR text will appear after extraction."}</pre>
                {page?.ocr_confidence !== null && page?.ocr_confidence !== undefined ? <p className="hero-text">OCR confidence: {Math.round(page.ocr_confidence * 100)}%</p> : null}
              </section>
              <section className="prescription-extraction">
                <div className="prescription-subheading"><h3>Human review</h3><span className={`prescription-confidence ${selected.review?.status === "approved" ? "is-ready" : ""}`}>{selected.review?.status?.replaceAll("_", " ") ?? (latestRun?.status === "completed" ? "Ready to start" : "Awaiting extraction")}</span></div>
                {latestRun?.error ? <p className="prescription-error">{latestRun.error}</p> : null}
                {!selected.review && latestRun?.status === "completed" ? <div className="prescription-review-start"><p className="hero-text">Start review to create an editable, audited copy of the extraction. The original extraction remains unchanged.</p><button type="button" className="primary-button" disabled={startReviewMutation.isPending} onClick={() => startReviewMutation.mutate(selected.id)}><ShieldCheck size={16} />{startReviewMutation.isPending ? "Starting…" : "Start human review"}</button>{startReviewMutation.error ? <p className="prescription-error">{startReviewMutation.error.message}</p> : null}</div> : null}
                {selected.review ? <div className="prescription-review-editor">
                  <label className="filter-field"><span>Matched patient ID</span><input className="auth-input" inputMode="numeric" value={patientId} onChange={(event) => setPatientId(event.target.value.replace(/[^0-9]/g, ""))} disabled={selected.review.status === "approved" || selected.review.status === "rejected"} placeholder="Leave blank if not identified" /><p className="entry-field-help">Only enter a confirmed existing patient ID.</p></label>
                  <label className="filter-field"><span>Reviewer notes</span><textarea className="auth-input entry-textarea" value={reviewNotes} onChange={(event) => setReviewNotes(event.target.value)} disabled={selected.review.status === "approved" || selected.review.status === "rejected"} placeholder="Record corrections, uncertainty, or rejection reason." /></label>
                  <section className="prescription-guided-review"><div><p className="eyebrow">Correct extracted facts</p><h4>Review each value against the source evidence</h4></div>{Object.entries(reviewedData).map(([key, value]) => <ReviewField key={key} label={key} value={value} path={[key]} onChange={(path, value) => setReviewedData((current) => setReviewValue(current, path, value))} />)}<p className="entry-field-help">Each field shows its source page and confidence where available. Changes affect the review copy only.</p></section>
                  {reviewError ? <p className="prescription-error">{reviewError}</p> : null}
                  {(saveReviewMutation.error || approveReviewMutation.error || rejectReviewMutation.error) ? <p className="prescription-error">{(saveReviewMutation.error || approveReviewMutation.error || rejectReviewMutation.error)?.message}</p> : null}
                  {selected.review.status !== "approved" && selected.review.status !== "rejected" ? <div className="prescription-review-actions"><button type="button" className="secondary-button" disabled={saveReviewMutation.isPending} onClick={saveReview}><Save size={16} />{saveReviewMutation.isPending ? "Saving…" : "Save review"}</button><button type="button" className="secondary-button" onClick={() => setReadyToApprove(true)}>Finish corrections</button><button type="button" className="secondary-button prescription-reject-button" disabled={rejectReviewMutation.isPending} onClick={() => { if (!reviewNotes.trim()) { setReviewError("Enter a rejection reason in reviewer notes before rejecting."); return; } rejectReviewMutation.mutate({ documentId: selected.id, reason: reviewNotes.trim() }); }}><XCircle size={16} />Reject review</button></div> : null}
                  {readyToApprove && selected.review.status !== "approved" && selected.review.status !== "rejected" ? <section className="prescription-approval-step"><strong>Final check</strong><p>Save corrections before approval. Approval locks this review but does not publish clinical records.</p><button type="button" className="primary-button" disabled={approveReviewMutation.isPending || saveReviewMutation.isPending} onClick={() => approveReviewMutation.mutate(selected.id)}><Check size={16} />{approveReviewMutation.isPending ? "Approving…" : "Approve completed review"}</button></section> : null}
                  {selected.review.changes.length ? <details className="prescription-audit"><summary>{selected.review.changes.length} audited change{selected.review.changes.length === 1 ? "" : "s"}</summary>{selected.review.changes.map((change) => <p key={change.id}>{change.field_path} · {formatDate(change.changed_at)}</p>)}</details> : null}
                </div> : null}
                {!selected.review && latestRun?.status !== "completed" ? <p className="hero-text">Run extraction to receive reviewable, source-linked clinical proposals. Approval never publishes clinical records.</p> : null}
              </section>
            </div>
          </>}
        </section>
      </section>
    </section>
  );
}
