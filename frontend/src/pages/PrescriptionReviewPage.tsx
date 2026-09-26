import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Check, ExternalLink, FileText, Play, Save, ShieldCheck, Upload, XCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";

import {
  type LongitudinalIntakeDraft,
  type PrescriptionDocument,
  approvePrescriptionReview,
  fetchEntriesOptions,
  fetchPrescriptionDocuments,
  processPrescriptionDocument,
  rejectPrescriptionReview,
  reopenPrescriptionReview,
  startPrescriptionReview,
  updatePrescriptionReview,
  uploadPrescriptionDocument,
} from "../api";
import { LongitudinalDraftWorkspace } from "../components/intake/LongitudinalDraftWorkspace";

const workspaceOptionResources = ["sexes", "districts", "thanas", "blood-groups", "economic-statuses", "patient-types", "comorbidities", "diagnosis-disease-groups", "diagnosis-disease-subgroups", "diagnosis-primary-sites", "diagnosis-lateralities", "histopathology-details", "histopathology-types", "histopathology-sites", "histopathology-grades", "ihc-cycles", "ihc-cycle-results", "ihc-staging-cycles", "ihc-staging-cycle-results", "tnm-t", "tnm-n", "tnm-m", "tnm-stages", "molecular-methods", "molecular-specimens", "molecular-genes", "molecular-exons", "molecular-alteration-types", "molecular-results", "molecular-clinical-significances", "molecular-panels", "molecular-panel-versions", "molecular-panel-targets", "cancer-marker-names", "treatment-modalities", "lines-of-treatment", "treatment-protocols", "treatment-drugs", "surgery-modalities", "surgery-lateralities", "radiotherapy-sites", "radiotherapy-intents", "radiotherapy-modalities", "recist-target-lesions", "recist-non-target-lesions", "recist-new-lesions", "recist-response-results", "irecist-target-lesions", "irecist-non-target-lesions", "irecist-new-lesions", "irecist-response-results", "progression-sites", "response-estimation-methods", "pathological-response-categories", "tumor-regression-grades", "disease-progression-statuses", "survival-statuses"];

const statusLabel: Record<PrescriptionDocument["status"], string> = {
  uploaded: "Ready to extract",
  processing: "Processing",
  ready_for_review: "Ready for review",
  failed: "Processing failed",
};

function formatDate(value: string | null) {
  return value ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—";
}

function reviewMediaUrl(url: string) {
  try {
    const parsed = new URL(url, window.location.origin);
    // Django serializers return an absolute development media URL. Route it
    // through Vite so the embedded PDF has the same browser origin as the UI.
    return parsed.pathname.startsWith("/media/")
      ? `${parsed.pathname}${parsed.search}${parsed.hash}`
      : url;
  } catch {
    return url;
  }
}

type ReviewData = Record<string, unknown>;

function displayLabel(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

const entrySectionLabels: Record<string, string> = {
  patient: "Patient profile",
  prescriber_candidates: "Prescription context",
  medications: "Medication prescriptions",
  date_candidates: "Prescription dates",
  diagnosis_candidates: "Diagnosis",
  staging_candidates: "Clinical and pathological staging",
  histopathology_candidates: "Histopathology",
  molecular_candidates: "Molecular pathology",
  ihc_candidates: "IHC cycle",
  cancer_marker_candidates: "Cancer markers",
  treatment_candidates: "Treatment protocols",
  administration_candidates: "Treatment administrations",
  response_candidates: "RECIST / iRECIST response",
  progression_candidates: "Disease progression records",
  survival_candidates: "Survival follow-ups",
  surgery_candidates: "Surgery",
  radiotherapy_candidates: "Radiotherapy",
  chronology: "Clinical timeline",
  observations: "Clinical observations",
  field_tracking: "Field coverage",
  gemini_extraction: "Gemini enrichment cross-check",
  unresolved_items: "Unresolved items",
  form_field_candidates: "New Entry field candidates",
  intake_draft: "New Entry draft",
};

function setReviewValue(data: ReviewData, path: Array<string | number>, nextValue: unknown): ReviewData {
  const copy = structuredClone(data) as ReviewData;
  let target: Record<string | number, unknown> = copy;
  path.slice(0, -1).forEach((part) => { target = target[part] as Record<string | number, unknown>; });
  target[path[path.length - 1]] = nextValue;
  return copy;
}

function ReviewField({ label, value, path, onChange }: { label: string; value: unknown; path: Array<string | number>; onChange: (path: Array<string | number>, value: unknown) => void }) {
  if (Array.isArray(value)) return <section className="prescription-review-group"><h4>{displayLabel(label)}</h4>{value.length ? value.map((item, index) => <article className="prescription-candidate-card" key={index}><p className="prescription-candidate-number">Candidate {index + 1}</p><ReviewField label={displayLabel(label)} value={item} path={[...path, index]} onChange={onChange} /></article>) : <p className="hero-text">None extracted.</p>}</section>;
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
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [reviewedData, setReviewedData] = useState<ReviewData>({});
  const [reviewNotes, setReviewNotes] = useState("");
  const [patientId, setPatientId] = useState("");
  const [reviewError, setReviewError] = useState("");
  const [readyToApprove, setReadyToApprove] = useState(false);
  const [reopenReason, setReopenReason] = useState("");
  const [reviewTab, setReviewTab] = useState("patient");
  const [pdfPreviewUrl, setPdfPreviewUrl] = useState<string | null>(null);
  const [pdfLoadError, setPdfLoadError] = useState(false);
  const documentsQuery = useQuery({ queryKey: ["prescription-documents"], queryFn: fetchPrescriptionDocuments });
  const workspaceOptionsQuery = useQuery({ queryKey: ["prescription-workspace-options"], queryFn: () => fetchEntriesOptions(workspaceOptionResources), staleTime: 60_000 });
  const documents = documentsQuery.data ?? [];
  const selected = useMemo(
    () => documents.find((document) => document.id === selectedId) ?? documents[0] ?? null,
    [documents, selectedId],
  );
  const latestRun = selected?.extraction_runs[0];
  const isPdf = Boolean(selected?.original_filename.toLowerCase().endsWith(".pdf"));
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

  useEffect(() => {
    const data = selected?.review?.reviewed_data ?? latestRun?.structured_data ?? {};
    setReviewedData(data);
    setReviewNotes(selected?.review?.notes ?? "");
    setPatientId(selected?.review?.selected_patient ? String(selected.review.selected_patient) : "");
    setReviewError("");
    setReadyToApprove(false);
    setReopenReason("");
    setReviewTab("patient");
  }, [selected?.id, selected?.review?.updated_at, latestRun?.id]);
  useEffect(() => {
    if (!isPdf || !selected?.file) {
      setPdfPreviewUrl(null);
      setPdfLoadError(false);
      return;
    }
    let objectUrl: string | null = null;
    let cancelled = false;
    setPdfPreviewUrl(null);
    setPdfLoadError(false);
    void fetch(reviewMediaUrl(selected.file), { credentials: "include" })
      .then((response) => {
        if (!response.ok) throw new Error("The original PDF could not be loaded.");
        return response.blob();
      })
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        if (!cancelled) setPdfPreviewUrl(objectUrl);
      })
      .catch(() => { if (!cancelled) setPdfLoadError(true); });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [isPdf, selected?.file]);

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
  const saveReviewMutation = useMutation({ mutationFn: ({ documentId, data }: { documentId: number; data: Record<string, unknown> }) => updatePrescriptionReview(documentId, { reviewed_data: data as LongitudinalIntakeDraft, notes: reviewNotes, selected_patient: patientId ? Number(patientId) : null }), onSuccess: refreshDocuments });
  const approveReviewMutation = useMutation({ mutationFn: approvePrescriptionReview, onSuccess: refreshDocuments });
  const reopenReviewMutation = useMutation({ mutationFn: ({ documentId, reason }: { documentId: number; reason: string }) => reopenPrescriptionReview(documentId, reason), onSuccess: refreshDocuments });
  const rejectReviewMutation = useMutation({ mutationFn: ({ documentId, reason }: { documentId: number; reason: string }) => rejectPrescriptionReview(documentId, reason), onSuccess: refreshDocuments });

  function saveReview() {
    if (!selected) return;
    setReviewError("");
    saveReviewMutation.mutate({ documentId: selected.id, data: reviewedData });
  }

  async function correctInNewEntry() {
    if (!selected) return;
    setReviewError("");
    try {
      // The backend creates the immutable extraction snapshot on demand. The
      // actual correction happens only in New Entry, not this workbench.
      if (!selected.review) await startReviewMutation.mutateAsync(selected.id);
      navigate(`/entries/new?prescription_document=${selected.id}`);
    } catch (error) {
      setReviewError(error instanceof Error ? error.message : "Unable to open the New Entry correction form.");
    }
  }

  const reviewSections = [
    { key: "patient", step: "Patient profile and matching", label: "Patient", fields: ["patient"] },
    { key: "observations", step: "Longitudinal clinical draft", label: "Observations", fields: ["observations"] },
    { key: "unresolved", step: "Review safeguards", label: "Unresolved items", fields: ["unresolved_items"] },
  ].filter((section) => section.fields.some((field) => {
    const value = reviewedData[field];
    return Array.isArray(value) ? value.length > 0 : Boolean(value && typeof value === "object" && Object.keys(value as object).length);
  }));
  const activeReviewSection = reviewSections.find((section) => section.key === reviewTab) ?? reviewSections[0];

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
              <div><p className="eyebrow">Prescription review workbench</p><h3>{selected.original_filename}</h3><p className="hero-text">{selected.page_count || selected.pages.length || "No"} page{(selected.page_count || selected.pages.length) === 1 ? "" : "s"} · {statusLabel[selected.status]}{latestRun?.ai_model ? ` · Gemini enrichment: ${latestRun.ai_model}` : " · Deterministic extraction"}</p></div>
              {documents.length > 1 ? <select className="filter-select prescription-document-switcher" value={selected.id} onChange={(event) => setSelectedId(Number(event.target.value))} aria-label="Switch prescription document">{documents.map((document) => <option key={document.id} value={document.id}>{document.original_filename}</option>)}</select> : null}
              {selected.status === "uploaded" ? <button type="button" className="primary-button" disabled={processMutation.isPending} onClick={() => processMutation.mutate(selected.id)}><Play size={16} /> {processMutation.isPending ? "Extracting…" : "Run extraction"}</button> : null}
              {latestRun?.status === "completed" && selected.review?.status !== "rejected" ? <button type="button" className="primary-button" disabled={startReviewMutation.isPending} onClick={() => void correctInNewEntry()}><FileText size={16} />{startReviewMutation.isPending ? "Opening…" : "Correct in New Entry"}</button> : null}
            </div>
            {processMutation.error ? <p className="prescription-error">{processMutation.error.message}</p> : null}
            {reviewIssues.length ? <details className="prescription-issues"><summary><AlertTriangle size={18} /> {reviewIssues.length} validation item{reviewIssues.length === 1 ? "" : "s"} to resolve before approval</summary><div>{reviewIssues.map((issue) => <p key={`${issue.code}-${issue.page_number ?? "document"}-${issue.message}`}>{issue.page_number ? `Page ${issue.page_number}: ` : ""}{issue.message}</p>)}</div></details> : null}
            {selected.review && reviewedData.schema_version === 1 ? <LongitudinalDraftWorkspace
              document={selected}
              draft={reviewedData as LongitudinalIntakeDraft}
              catalog={workspaceOptionsQuery.data ?? {}}
              disabled={selected.review.status === "approved" || selected.review.status === "rejected"}
              saving={saveReviewMutation.isPending}
              error={reviewError || saveReviewMutation.error?.message}
              onChange={(draft) => {
                setReviewedData(draft);
                setPatientId(draft.patient.match_status === "existing" && draft.patient.patient_id ? String(draft.patient.patient_id) : "");
              }}
              onSave={saveReview}
            /> : <div className="prescription-split-view">
              <section className="prescription-source">
                <div className="prescription-subheading"><div><h3>Source evidence</h3><p className="hero-text">Read pages in prescription order while reviewing.</p></div></div>
                {isPdf && selected?.file ? <details className="prescription-original-file" open><summary>Original prescription PDF</summary><a className="secondary-button prescription-open-file" href={reviewMediaUrl(selected.file)} target="_blank" rel="noreferrer"><ExternalLink size={16} />Open in new tab</a>{pdfPreviewUrl ? <iframe title={`Original prescription: ${selected.original_filename}`} src={`${pdfPreviewUrl}#view=FitH`} className="prescription-pdf-viewer" /> : <p className="hero-text">{pdfLoadError ? "The inline preview is unavailable. Open the original PDF in a new tab." : "Loading original PDF…"}</p>}</details> : null}
                {selected.pages.length ? <div className="prescription-source-pages">{selected.pages.map((item) => <article className="prescription-source-page" key={item.id}><div className="prescription-source-page-heading"><strong>Page {item.page_number}</strong>{item.ocr_confidence !== null && item.ocr_confidence !== undefined ? <span>OCR confidence {Math.round(item.ocr_confidence * 100)}%</span> : null}</div>{item.image ? <img className="prescription-page-image" src={reviewMediaUrl(item.image)} alt={`Prescription page ${item.page_number}`} /> : null}<pre className="prescription-ocr-text">{item.cleaned_text || item.raw_text || "No text was extracted from this page."}</pre></article>)}</div> : <p className="hero-text">Source pages will appear after extraction.</p>}
              </section>
              <section className="prescription-extraction">
                <div className="prescription-subheading"><h3>Human review</h3><span className={`prescription-confidence ${selected.review?.status === "approved" ? "is-ready" : ""}`}>{selected.review?.status?.replaceAll("_", " ") ?? (latestRun?.status === "completed" ? "Ready to start" : "Awaiting extraction")}</span></div>
                {latestRun?.error ? <p className="prescription-error">{latestRun.error}</p> : null}
                {!selected.review && latestRun?.status === "completed" ? <div className="prescription-review-start"><p className="hero-text">Start review to create an editable, audited copy of the extraction. The original extraction remains unchanged.</p><button type="button" className="primary-button" disabled={startReviewMutation.isPending} onClick={() => startReviewMutation.mutate(selected.id)}><ShieldCheck size={16} />{startReviewMutation.isPending ? "Starting…" : "Start human review"}</button>{startReviewMutation.error ? <p className="prescription-error">{startReviewMutation.error.message}</p> : null}</div> : null}
                {selected.review ? <div className="prescription-review-editor">
                  <label className="filter-field"><span>Matched patient ID</span><input className="auth-input" inputMode="numeric" value={patientId} onChange={(event) => setPatientId(event.target.value.replace(/[^0-9]/g, ""))} disabled={selected.review.status === "approved" || selected.review.status === "rejected"} placeholder="Leave blank if not identified" /><p className="entry-field-help">Only enter a confirmed existing patient ID.</p></label>
                  <label className="filter-field"><span>Reviewer notes</span><textarea className="auth-input entry-textarea" value={reviewNotes} onChange={(event) => setReviewNotes(event.target.value)} disabled={selected.review.status === "approved" || selected.review.status === "rejected"} placeholder="Record corrections, uncertainty, or rejection reason." /></label>
                  <section className="prescription-guided-review">
                    <div><p className="eyebrow">3. Correct extracted facts</p><h4>Review one clinical area at a time</h4><p className="entry-field-help">Warnings are shown separately and are never converted into clinical facts.</p></div>
                    {reviewSections.length ? <div className="prescription-review-tabs" role="tablist" aria-label="Review sections">{reviewSections.map((section) => <button type="button" role="tab" aria-selected={activeReviewSection?.key === section.key} className={activeReviewSection?.key === section.key ? "is-active" : ""} key={section.key} onClick={() => setReviewTab(section.key)}>{section.label}</button>)}</div> : <p className="hero-text">No supported clinical facts were extracted. Review the source and record a rejection or note.</p>}
                    {activeReviewSection ? <div className="prescription-review-step"><div className="prescription-step-title"><span>{activeReviewSection.step} · section {reviewSections.findIndex((section) => section.key === activeReviewSection.key) + 1} of {reviewSections.length}</span><strong>{activeReviewSection.label}</strong></div>{activeReviewSection.fields.map((field) => reviewedData[field] !== undefined ? <ReviewField key={field} label={entrySectionLabels[field] ?? field} value={reviewedData[field]} path={[field]} onChange={(path, value) => setReviewedData((current) => setReviewValue(current, path, value))} /> : null)}</div> : null}
                  </section>
                  {reviewError ? <p className="prescription-error">{reviewError}</p> : null}
                  {(saveReviewMutation.error || approveReviewMutation.error || reopenReviewMutation.error || rejectReviewMutation.error) ? <p className="prescription-error">{(saveReviewMutation.error || approveReviewMutation.error || reopenReviewMutation.error || rejectReviewMutation.error)?.message}</p> : null}
                  {selected.review.status !== "rejected" ? <div className="prescription-review-actions"><button type="button" className="primary-button" disabled={saveReviewMutation.isPending} onClick={() => {
                    if (JSON.stringify(reviewedData) !== JSON.stringify(selected.review?.reviewed_data)) {
                      setReviewError("Save the review before opening New Entry so the handoff is auditable.");
                      return;
                    }
                    navigate(`/entries/new?prescription_document=${selected.id}`);
                  }}><FileText size={16} />Open in New Entry</button>{selected.review.status !== "approved" ? <><button type="button" className="secondary-button" disabled={saveReviewMutation.isPending} onClick={saveReview}><Save size={16} />{saveReviewMutation.isPending ? "Saving…" : "Save review"}</button><button type="button" className="secondary-button" onClick={() => setReadyToApprove(true)}>Finish corrections</button><button type="button" className="secondary-button prescription-reject-button" disabled={rejectReviewMutation.isPending} onClick={() => { if (!reviewNotes.trim()) { setReviewError("Enter a rejection reason in reviewer notes before rejecting."); return; } rejectReviewMutation.mutate({ documentId: selected.id, reason: reviewNotes.trim() }); }}><XCircle size={16} />Reject review</button></> : null}</div> : null}
                  {readyToApprove && selected.review.status !== "approved" && selected.review.status !== "rejected" ? <section className="prescription-approval-step"><strong>Final check</strong><p>Save corrections before approval. Approval locks this review but does not publish clinical records.</p><button type="button" className="primary-button" disabled={approveReviewMutation.isPending || saveReviewMutation.isPending} onClick={() => approveReviewMutation.mutate(selected.id)}><Check size={16} />{approveReviewMutation.isPending ? "Approving…" : "Approve completed review"}</button></section> : null}
                  {selected.review.status === "approved" ? <section className="prescription-approval-step"><strong>Approved review</strong><p>If a correction is needed, reopen this review with an auditable reason. It will return to in-review status.</p><label className="filter-field"><span>Reason for reopening</span><textarea className="auth-input entry-textarea" value={reopenReason} onChange={(event) => setReopenReason(event.target.value)} placeholder="Explain what must be corrected." /></label><button type="button" className="secondary-button" disabled={reopenReviewMutation.isPending} onClick={() => { if (!reopenReason.trim()) { setReviewError("Enter a reason before reopening this review."); return; } reopenReviewMutation.mutate({ documentId: selected.id, reason: reopenReason.trim() }); }}><Save size={16} />{reopenReviewMutation.isPending ? "Reopening…" : "Reopen for correction"}</button></section> : null}
                  {selected.review.changes.length ? <details className="prescription-audit"><summary>{selected.review.changes.length} audited change{selected.review.changes.length === 1 ? "" : "s"}</summary>{selected.review.changes.map((change) => <p key={change.id}>{change.field_path} · {formatDate(change.changed_at)}</p>)}</details> : null}
                </div> : null}
                {!selected.review && latestRun?.status !== "completed" ? <p className="hero-text">Run extraction to receive reviewable, source-linked clinical proposals. Approval never publishes clinical records.</p> : null}
              </section>
            </div>}
          </>}
        </section>
      </section>
    </section>
  );
}
