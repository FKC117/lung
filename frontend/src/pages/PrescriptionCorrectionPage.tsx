import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ApiError,
  loadLatestPrescriptionExtraction,
  approvePrescriptionReview,
  fetchEntriesOptions,
  fetchPrescriptionDocument,
  fetchPrescriptionRepairProposals,
  publishPrescriptionReview,
  prescriptionPreviewUrl,
  startPrescriptionReview,
  type LongitudinalIntakeDraft,
  type PrescriptionReview,
  updatePrescriptionReview,
} from "../api";
import { normalizePathologyFormDraft } from "../components/intake/ObservationFormSections";
import { LongitudinalDraftWorkspace } from "../components/intake/LongitudinalDraftWorkspace";
import { RepairProposalPanel, adoptRepairProposal } from "../components/intake/RepairProposalPanel";
import { authoritativeOptionResources } from "../components/intake/observationFieldSchema";

function errorMessage(error: unknown) {
  return error instanceof ApiError || error instanceof Error ? error.message : "Unable to update the prescription review.";
}

export default function PrescriptionCorrectionPage() {
  const { documentId } = useParams();
  const id = Number(documentId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [review, setReview] = useState<PrescriptionReview | null>(null);
  const [draft, setDraft] = useState<LongitudinalIntakeDraft | null>(null);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState("");
  const documentQuery = useQuery({ queryKey: ["prescription-document", id], queryFn: () => fetchPrescriptionDocument(id), enabled: Number.isSafeInteger(id) && id > 0 });
  const repairQuery = useQuery({ queryKey: ["prescription-repair-proposals", id, review?.revision], queryFn: () => fetchPrescriptionRepairProposals(id), enabled: Boolean(review) });
  const catalogQuery = useQuery({ queryKey: ["prescription-review-options"], queryFn: () => fetchEntriesOptions(authoritativeOptionResources), staleTime: 0 });
  const startMutation = useMutation({ mutationFn: () => startPrescriptionReview(id) });
  const saveMutation = useMutation({ mutationFn: (next: LongitudinalIntakeDraft) => updatePrescriptionReview(id, { reviewed_data: next, expected_revision: review?.revision }) });
  const approveMutation = useMutation({ mutationFn: (revision: number) => approvePrescriptionReview(id, revision) });
  const refreshMutation = useMutation({ mutationFn: (runId: number) => loadLatestPrescriptionExtraction(id, review!.revision, runId) });
  const publishMutation = useMutation({ mutationFn: () => publishPrescriptionReview(id, review?.revision) });

  useEffect(() => {
    const existing = documentQuery.data?.review;
    if (existing) {
      setReview(existing);
      setDraft(existing.reviewed_data);
      return;
    }
    if (documentQuery.data && !startMutation.isPending && !startMutation.data) startMutation.mutate();
  }, [documentQuery.data, startMutation.isPending, startMutation.data, startMutation.mutate]);

  useEffect(() => {
    if (!startMutation.data) return;
    setReview(startMutation.data);
    setDraft(startMutation.data.reviewed_data);
    queryClient.invalidateQueries({ queryKey: ["prescription-documents"] });
  }, [startMutation.data, queryClient]);

  const save = async () => {
    if (!draft) return null;
    setError("");
    try {
      const saved = await saveMutation.mutateAsync(normalizePathologyFormDraft(draft));
      setReview(saved);
      setDraft(saved.reviewed_data);
      setDirty(false);
      queryClient.invalidateQueries({ queryKey: ["prescription-documents"] });
      return saved;
    } catch (exception) {
      setError(errorMessage(exception));
      return null;
    }
  };

  const approve = async () => {
    setError("");
    let approvalRevision = review?.revision;
    if (dirty || (draft && JSON.stringify(normalizePathologyFormDraft(draft)) !== JSON.stringify(draft))) {
      const saved = await save();
      if (!saved) return;
      approvalRevision = saved.revision;
    }
    if (approvalRevision === undefined) return;
    try {
      const approved = await approveMutation.mutateAsync(approvalRevision);
      setReview(approved);
      setDraft(approved.reviewed_data);
      setDirty(false);
      queryClient.invalidateQueries({ queryKey: ["prescription-documents"] });
    } catch (exception) {
      setError(errorMessage(exception));
    }
  };

  const publish = async () => {
    if (review?.published_at) return;
    setError("");
    try {
      await publishMutation.mutateAsync();
      queryClient.invalidateQueries({ queryKey: ["prescription-documents"] });
      navigate("/prescriptions");
    } catch (exception) {
      setError(errorMessage(exception));
    }
  };

  if (documentQuery.isLoading || startMutation.isPending || catalogQuery.isLoading) return <section className="panel state-card"><p>Opening prescription review…</p></section>;
  if (documentQuery.error || startMutation.error || !documentQuery.data || !review || !draft) return <section className="panel state-card"><Link className="secondary-button" to="/prescriptions"><ArrowLeft size={16} />Back to prescriptions</Link><h3>Prescription review unavailable</h3><p>{errorMessage(documentQuery.error ?? startMutation.error)}</p></section>;

  const published = Boolean(review.published_at);
  const locked = published || review.status === "approved" || review.status === "rejected";
  const latestRun = documentQuery.data.extraction_runs?.[0];
  const canRefresh = documentQuery.data.status === "ready_for_review" && !locked && review.revision === 1 && !review.changes?.length && !review.selected_patient && !review.notes
    && draft.patient.match_status === "unresolved" && latestRun?.status === "completed"
    && new Date(latestRun.created_at) > new Date(review.created_at);
  const previewDocument = { ...documentQuery.data, file: prescriptionPreviewUrl(documentQuery.data.file) };
  return <section className="page-grid prescription-correction-page"><Link className="text-button" to="/prescriptions"><ArrowLeft size={16} />Prescription queue</Link>{canRefresh ? <div className="panel"><strong>Newer extraction available</strong><p>Load its suggestions into this untouched draft. The previous draft is retained in the review history.</p><button type="button" className="secondary-button" disabled={dirty || refreshMutation.isPending || saveMutation.isPending || approveMutation.isPending} onClick={async () => { setError(""); try { const saved = await refreshMutation.mutateAsync(latestRun.id); setReview(saved); setDraft(saved.reviewed_data); setDirty(false); queryClient.setQueryData(["prescription-document", id], { ...documentQuery.data, review: saved }); queryClient.invalidateQueries({ queryKey: ["prescription-documents"] }); } catch (exception) { setError(errorMessage(exception)); } }}>Load latest extraction</button>{dirty ? <small>Unsaved edits must be preserved; refresh is unavailable.</small> : null}</div> : null}<RepairProposalPanel proposals={repairQuery.data?.proposals ?? []} disabled={locked || dirty || repairQuery.data?.revision !== review.revision} onAdopt={(proposal) => { try { if (proposal.review_revision !== review.revision) throw new Error("This suggestion belongs to an older saved revision."); setDraft(adoptRepairProposal(draft, proposal)); setDirty(true); setError(""); } catch (exception) { setError(errorMessage(exception)); } }} /><LongitudinalDraftWorkspace document={previewDocument} draft={draft} catalog={catalogQuery.data ?? {}} disabled={locked || refreshMutation.isPending} saving={saveMutation.isPending || refreshMutation.isPending} approving={approveMutation.isPending || refreshMutation.isPending} publishing={publishMutation.isPending} dirty={dirty} error={error} onChange={(next) => { setDraft(next); setDirty(true); }} onSave={() => { void save(); }} onApprove={review.status === "draft" || review.status === "in_review" ? () => { void approve(); } : undefined} onPublish={review.status === "approved" ? () => { void publish(); } : undefined} /> </section>;
}
