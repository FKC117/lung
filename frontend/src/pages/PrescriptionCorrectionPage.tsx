import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ApiError,
  approvePrescriptionReview,
  fetchEntriesOptions,
  fetchPrescriptionDocument,
  publishPrescriptionReview,
  prescriptionPreviewUrl,
  startPrescriptionReview,
  type LongitudinalIntakeDraft,
  type PrescriptionReview,
  updatePrescriptionReview,
} from "../api";
import { normalizePathologyFormDraft } from "../components/intake/ObservationFormSections";
import { LongitudinalDraftWorkspace } from "../components/intake/LongitudinalDraftWorkspace";
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
  const catalogQuery = useQuery({ queryKey: ["prescription-review-options"], queryFn: () => fetchEntriesOptions(authoritativeOptionResources), staleTime: 0 });
  const startMutation = useMutation({ mutationFn: () => startPrescriptionReview(id) });
  const saveMutation = useMutation({ mutationFn: (next: LongitudinalIntakeDraft) => updatePrescriptionReview(id, { reviewed_data: next }) });
  const approveMutation = useMutation({ mutationFn: () => approvePrescriptionReview(id) });
  const publishMutation = useMutation({ mutationFn: () => publishPrescriptionReview(id) });

  useEffect(() => {
    const existing = documentQuery.data?.review;
    if (existing) {
      setReview(existing);
      setDraft(existing.reviewed_data);
      return;
    }
    if (documentQuery.data && !startMutation.isPending && !startMutation.data) startMutation.mutate();
  }, [documentQuery.data, startMutation]);

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
    if ((dirty || (draft && JSON.stringify(normalizePathologyFormDraft(draft)) !== JSON.stringify(draft))) && !(await save())) return;
    try {
      const approved = await approveMutation.mutateAsync();
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
  const previewDocument = { ...documentQuery.data, file: prescriptionPreviewUrl(documentQuery.data.file) };
  return <section className="page-grid prescription-correction-page"><Link className="text-button" to="/prescriptions"><ArrowLeft size={16} />Prescription queue</Link><LongitudinalDraftWorkspace document={previewDocument} draft={draft} catalog={catalogQuery.data ?? {}} disabled={locked} saving={saveMutation.isPending} approving={approveMutation.isPending} publishing={publishMutation.isPending} dirty={dirty} error={error} onChange={(next) => { setDraft(next); setDirty(true); }} onSave={() => { void save(); }} onApprove={review.status === "draft" || review.status === "in_review" ? () => { void approve(); } : undefined} onPublish={review.status === "approved" ? () => { void publish(); } : undefined} /> </section>;
}
