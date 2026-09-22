import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, FileText, Play, ShieldCheck, Upload } from "lucide-react";

import {
  type PrescriptionDocument,
  fetchPrescriptionDocuments,
  processPrescriptionDocument,
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

function valueText(value: unknown) {
  if (value === null || value === undefined || value === "") return "Not stated";
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

export default function PrescriptionReviewPage() {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedPage, setSelectedPage] = useState(0);
  const documentsQuery = useQuery({ queryKey: ["prescription-documents"], queryFn: fetchPrescriptionDocuments });
  const documents = documentsQuery.data ?? [];
  const selected = useMemo(
    () => documents.find((document) => document.id === selectedId) ?? documents[0] ?? null,
    [documents, selectedId],
  );
  const latestRun = selected?.extraction_runs[0];
  const page = selected?.pages[selectedPage] ?? selected?.pages[0];

  useEffect(() => setSelectedPage(0), [selected?.id]);

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
            {selected.issues.length || latestRun?.issues.length ? <section className="prescription-issues"><AlertTriangle size={18} /><div><strong>Validation needs review</strong>{[...selected.issues, ...(latestRun?.issues ?? [])].map((issue) => <p key={`${issue.id}-${issue.code}`}>{issue.page_number ? `Page ${issue.page_number}: ` : ""}{issue.message}</p>)}</div></section> : null}
            <div className="prescription-split-view">
              <section className="prescription-source">
                <div className="prescription-subheading"><h3>Source evidence</h3>{selected.pages.length > 1 ? <select className="filter-select" value={selectedPage} onChange={(event) => setSelectedPage(Number(event.target.value))}>{selected.pages.map((item, index) => <option value={index} key={item.id}>Page {item.page_number}</option>)}</select> : null}</div>
                {page?.image ? <img className="prescription-page-image" src={page.image} alt={`Prescription page ${page.page_number}`} /> : null}
                <pre className="prescription-ocr-text">{page?.cleaned_text || page?.raw_text || "OCR text will appear after extraction."}</pre>
                {page?.ocr_confidence !== null && page?.ocr_confidence !== undefined ? <p className="hero-text">OCR confidence: {Math.round(page.ocr_confidence * 100)}%</p> : null}
              </section>
              <section className="prescription-extraction">
                <div className="prescription-subheading"><h3>Proposed structured data</h3><span className={`prescription-confidence ${latestRun?.status === "completed" ? "is-ready" : ""}`}>{latestRun?.status === "completed" ? "Review required" : latestRun?.status ?? "Awaiting extraction"}</span></div>
                {latestRun?.error ? <p className="prescription-error">{latestRun.error}</p> : null}
                {latestRun?.structured_data && Object.keys(latestRun.structured_data).length ? <div className="prescription-data-list">{Object.entries(latestRun.structured_data).map(([key, value]) => <article key={key}><strong>{key.replaceAll("_", " ")}</strong><pre>{valueText(value)}</pre></article>)}</div> : <p className="hero-text">Run extraction to receive reviewable, source-linked clinical proposals. Nothing can be published from this screen yet.</p>}
              </section>
            </div>
          </>}
        </section>
      </section>
    </section>
  );
}
