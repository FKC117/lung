from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from django.db import transaction
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from rest_framework.exceptions import APIException, MethodNotAllowed, NotFound, ValidationError
from rest_framework.response import Response

from .models import PrescriptionBatchJob, PrescriptionDocument, PrescriptionReview, PrescriptionReviewChange
from .serializers import PrescriptionBatchJobSerializer, PrescriptionDocumentSerializer, PrescriptionReviewSerializer, PrescriptionReviewUpdateSerializer
from .services.batch import create_batch_job, sync_batch_job
from .services.access import prescription_batch_jobs_for_user, prescription_documents_for_user
from .services.draft_schema import is_canonical_draft
from .services.extraction import has_clinical_observation, source_has_clinical_signal
from .services.intake_draft import build_intake_draft
from .services.publish import publish_review
from .services.provider_data_policy import ProviderDataPolicyError
from .services.provider_budget import ProviderBudgetExhausted, ProviderBudgetConfigurationError
from .tasks import process_prescription_document, sync_prescription_batch_job


_MISSING = object()


class ReviewRevisionConflict(APIException):
    status_code = 409
    default_detail = "This review changed. Reload it before saving or approving."


def check_review_revision(review, request, *, required=False):
    expected = request.data.get("expected_revision")
    if required and expected is None:
        raise ValidationError({"expected_revision": "Approval and publication require the saved review revision."})
    # Legacy draft-save clients remain compatible; final actions require a revision.
    if expected is not None and (not isinstance(expected, int) or isinstance(expected, bool) or expected != review.revision):
        raise ReviewRevisionConflict()


def has_gemini_quality_issue(document):
    """Allow a repair run without ever replacing an in-progress review draft."""
    latest_run = document.extraction_runs.order_by("-created_at").first()
    extracted = latest_run.structured_data if latest_run and isinstance(latest_run.structured_data, dict) else {}
    if extracted.get("gemini_status") == "unavailable":
        return True
    gemini = extracted.get("gemini_extraction") if isinstance(extracted.get("gemini_extraction"), dict) else {}
    unresolved = gemini.get("unresolved_items") if isinstance(gemini.get("unresolved_items"), list) else []
    if any(isinstance(item, dict) and item.get("type") == "structured_extraction" for item in unresolved):
        return True
    return source_has_clinical_signal(document.pages.all()) and not has_clinical_observation(gemini)


def json_changes(previous, current, path="reviewed_data"):
    """Return leaf-level JSON changes for the clinical review audit trail."""
    if isinstance(previous, dict) and isinstance(current, dict):
        changes = []
        for key in sorted(set(previous) | set(current)):
            changes.extend(json_changes(previous.get(key, _MISSING), current.get(key, _MISSING), f"{path}.{key}"))
        return changes
    if previous != current:
        return [(path, None if previous is _MISSING else previous, None if current is _MISSING else current)]
    return []


class PrescriptionDocumentViewSet(viewsets.ModelViewSet):
    queryset = PrescriptionDocument.objects.select_related("patient", "uploaded_by").prefetch_related("pages", "issues", "extraction_runs__issues")
    serializer_class = PrescriptionDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return prescription_documents_for_user(self.request.user).select_related(
            "patient", "uploaded_by"
        ).prefetch_related("pages", "issues", "extraction_runs__issues")

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PATCH", detail="Update review data through the review endpoint.")

    def create(self, request, *args, **kwargs):
        uploaded = request.FILES.get("file")
        if not uploaded:
            raise ValidationError({"file": "A prescription file is required."})
        checksum = PrescriptionDocument.checksum(uploaded)
        existing = PrescriptionDocument.objects.filter(sha256=checksum).first()
        if existing:
            payload = {"detail": "Duplicate prescription upload."}
            if prescription_documents_for_user(request.user).filter(pk=existing.pk).exists():
                payload["document_id"] = existing.pk
            return Response(payload, status=status.HTTP_409_CONFLICT)
        document = PrescriptionDocument.objects.create(
            file=uploaded,
            original_filename=uploaded.name,
            sha256=checksum,
            patient_id=request.data.get("patient") or None,
            uploaded_by=request.user,
        )
        return Response(self.get_serializer(document).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="source-file")
    @xframe_options_sameorigin
    def source_file(self, request, pk=None):
        document = self.get_object()
        if not document.file:
            raise NotFound("This prescription has no source file.")
        return FileResponse(
            document.file.open("rb"),
            as_attachment=False,
            filename=document.original_filename,
        )

    @action(detail=True, methods=["get"], url_path=r"pages/(?P<page_id>[^/.]+)/image")
    def page_image(self, request, pk=None, page_id=None):
        document = self.get_object()
        page = document.pages.filter(pk=page_id).first()
        if not page or not page.image:
            raise NotFound("This prescription page has no image.")
        return FileResponse(page.image.open("rb"), as_attachment=False)

    @action(detail=True, methods=["post"])
    def process(self, request, pk=None):
        document = self.get_object()
        if document.status not in {PrescriptionDocument.Status.UPLOADED, PrescriptionDocument.Status.FAILED}:
            return Response({"detail": "Only an uploaded or failed document can be queued for extraction."}, status=status.HTTP_409_CONFLICT)
        document.status = PrescriptionDocument.Status.PROCESSING
        document.processing_started_at = timezone.now()
        document.save(update_fields=["status", "processing_started_at"])
        try:
            task = process_prescription_document.delay(document.pk)
        except Exception as exc:
            document.status = PrescriptionDocument.Status.UPLOADED
            document.processing_started_at = None
            document.save(update_fields=["status", "processing_started_at"])
            raise ValidationError({"detail": f"Unable to queue extraction: {exc}"}) from exc
        return Response({**self.get_serializer(document).data, "task_id": task.id}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"], url_path="reprocess")
    def reprocess(self, request, pk=None):
        """Re-run an unreviewed completed document with the current extractor rules."""
        document = self.get_object()
        if document.status != PrescriptionDocument.Status.READY_FOR_REVIEW:
            raise ValidationError({"detail": "Only a completed, unreviewed document can be re-run."})
        review = getattr(document, "review", None)
        if review and review.published_at:
            raise ValidationError({"detail": "A published prescription cannot be re-run because its provenance is immutable."})
        if review and not has_gemini_quality_issue(document):
            raise ValidationError({"detail": "This document has already entered correction. Re-running a healthy extraction would overwrite its review context."})
        document.status = PrescriptionDocument.Status.PROCESSING
        document.processing_started_at = timezone.now()
        document.save(update_fields=["status", "processing_started_at"])
        try:
            task = process_prescription_document.delay(document.pk)
        except Exception as exc:
            document.status = PrescriptionDocument.Status.READY_FOR_REVIEW
            document.processing_started_at = None
            document.save(update_fields=["status", "processing_started_at"])
            raise ValidationError({"detail": f"Unable to queue extraction: {exc}"}) from exc
        return Response({**self.get_serializer(document).data, "task_id": task.id}, status=status.HTTP_202_ACCEPTED)

    def _start_review(self, document, user):
        if document.status != PrescriptionDocument.Status.READY_FOR_REVIEW:
            raise ValidationError({"detail": "Only a completed document can enter prescription review."})
        latest_run = document.extraction_runs.filter(status="completed").first()
        review, _ = PrescriptionReview.objects.get_or_create(document=document)
        if not review.reviewed_data or not is_canonical_draft(review.reviewed_data):
            if not latest_run:
                raise ValidationError({"detail": "Process the document before starting review."})
            source = review.reviewed_data or latest_run.structured_data
            if not review.reviewed_data and isinstance(latest_run.structured_data, dict):
                source = latest_run.structured_data.get("canonical_draft", latest_run.structured_data)
            review.reviewed_data = build_intake_draft(
                source,
                document_id=document.pk,
                linked_patient_id=review.selected_patient_id or document.patient_id,
            )
            draft_patient_id = review.reviewed_data["patient"]["patient_id"]
            if draft_patient_id:
                review.selected_patient_id = draft_patient_id
            review.assigned_to = review.assigned_to or user
            review.save(update_fields=["reviewed_data", "selected_patient", "assigned_to", "updated_at"])
        return review

    def _existing_review(self, document):
        try:
            queryset = PrescriptionReview.objects
            if transaction.get_connection().in_atomic_block:
                queryset = queryset.select_for_update()
            return queryset.get(document=document)
        except PrescriptionReview.DoesNotExist as exc:
            raise NotFound("Start a review before viewing or changing it.") from exc

    @action(detail=True, methods=["post"], url_path="start-review")
    def start_review(self, request, pk=None):
        review = self._start_review(self.get_object(), request.user)
        return Response(PrescriptionReviewSerializer(review).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="load-latest-extraction")
    @transaction.atomic
    def load_latest_extraction(self, request, pk=None):
        document = self.get_object()
        review = self._existing_review(document)
        check_review_revision(review, request, required=True)
        if (document.status != PrescriptionDocument.Status.READY_FOR_REVIEW or review.published_at
                or review.status not in {PrescriptionReview.Status.DRAFT, PrescriptionReview.Status.IN_REVIEW}
                or review.revision != 1 or review.changes.exists() or review.notes
                or review.selected_patient_id or document.patient_id
                or review.reviewed_data.get("patient", {}).get("match_status") != "unresolved"
                or any(record.get("state") == "edited" for observation in review.reviewed_data.get("observations", [])
                       for records in observation.values() if isinstance(records, list)
                       for record in records if isinstance(record, dict))):
            raise ValidationError({"detail": "Only an untouched, unassigned draft can load a newer extraction. Existing reviewer edits are protected."})
        latest = document.extraction_runs.first()
        if not latest or latest.status != "completed" or latest.pk != request.data.get("extraction_run_id"):
            raise ValidationError({"detail": "The extraction changed or is incomplete. Reload the document."})
        if latest.created_at <= review.created_at:
            raise ValidationError({"detail": "There is no newer extraction to load."})
        source = latest.structured_data
        try:
            draft = build_intake_draft(source.get("canonical_draft", source), document_id=document.pk,
                                      pages=list(document.pages.all()))
        except (DjangoValidationError, ValueError, TypeError) as exc:
            raise ValidationError({"detail": "The latest extraction cannot form a valid draft. Existing review is preserved."}) from exc
        if draft["patient"]["patient_id"] or draft["patient"]["match_status"] != "unresolved":
            raise ValidationError({"detail": "The extraction cannot select a patient."})
        previous = review.reviewed_data
        review.reviewed_data = draft
        review.revision += 1
        review.approved_revision = None
        review.status = PrescriptionReview.Status.IN_REVIEW
        review.assigned_to = review.assigned_to or request.user
        review.save()
        PrescriptionReviewChange.objects.create(review=review, changed_by=request.user,
            field_path="extraction_refresh", previous_value=previous,
            new_value={"extraction_run_id": latest.pk, "reviewed_data": draft})
        return Response(PrescriptionReviewSerializer(review).data)

    @action(detail=True, methods=["get", "patch"], url_path="review")
    @transaction.atomic
    def review(self, request, pk=None):
        review = self._existing_review(self.get_object())
        if request.method == "GET":
            return Response(PrescriptionReviewSerializer(review).data)
        check_review_revision(review, request)
        if review.status in {PrescriptionReview.Status.APPROVED, PrescriptionReview.Status.REJECTED}:
            raise ValidationError({"detail": "A completed review cannot be edited. Start a new review if correction is required."})
        serializer = PrescriptionReviewUpdateSerializer(
            data=request.data,
            partial=True,
            context={"document_id": review.document_id, "previous_draft": review.reviewed_data},
        )
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            changes = []
            if "reviewed_data" in serializer.validated_data and serializer.validated_data["reviewed_data"] != review.reviewed_data:
                changes.extend(json_changes(review.reviewed_data, serializer.validated_data["reviewed_data"]))
                review.reviewed_data = serializer.validated_data["reviewed_data"]
                draft_patient = review.reviewed_data["patient"]
                review.selected_patient_id = draft_patient["patient_id"] if draft_patient["match_status"] == "existing" else None
            if "selected_patient" in serializer.validated_data and serializer.validated_data["selected_patient"] != review.selected_patient:
                old = review.selected_patient_id
                review.selected_patient = serializer.validated_data["selected_patient"]
                review.reviewed_data["patient"]["match_status"] = "existing" if review.selected_patient_id else "unresolved"
                review.reviewed_data["patient"]["patient_id"] = review.selected_patient_id
                changes.append(("selected_patient", old, review.selected_patient_id))
            if "notes" in serializer.validated_data and serializer.validated_data["notes"] != review.notes:
                changes.append(("notes", review.notes, serializer.validated_data["notes"]))
                review.notes = serializer.validated_data["notes"]
            review.status = PrescriptionReview.Status.IN_REVIEW
            if changes:
                review.revision += 1
                review.approved_revision = None
            review.assigned_to = review.assigned_to or request.user
            review.save()
            PrescriptionReviewChange.objects.bulk_create([
                PrescriptionReviewChange(review=review, changed_by=request.user, field_path=path, previous_value=old, new_value=new)
                for path, old, new in changes
            ])
        return Response(PrescriptionReviewSerializer(review).data)

    @action(detail=True, methods=["get"], url_path="repair-proposals")
    def repair_proposals(self, request, pk=None):
        """Expose only revalidated saved proposals to the authorized document reviewer."""
        import json
        from django.core.exceptions import ValidationError as DjangoValidationError
        from .services.repair_contract import validate_repair_proposal
        document = self.get_object()
        review = self._existing_review(document)
        proposals = []
        if review.status not in {"draft", "in_review"} or review.published_at:
            return Response({"revision": review.revision, "proposals": proposals})
        rows = document.workflow_runs.filter(versions__kind="targeted_repair").order_by("created_at")
        for run in rows:
            for row in run.checkpoints.filter(namespace="repair-proposal", payload_type="json"):
                try:
                    saved = run.checkpoints.get(namespace="repair-request", checkpoint_id=row.checkpoint_id, payload_type="json")
                    reservation = json.loads(bytes(saved.payload))
                    if reservation["review_id"] != review.pk:
                        continue
                    original = reservation["request"]
                    proposal = json.loads(bytes(row.payload))
                    checked = validate_repair_proposal(original, {"patches": proposal["patches"]}, current_draft=review.reviewed_data, current_revision=review.revision, document_sha256=document.sha256)
                    proposals.append({"id": str(run.pk)+":"+row.checkpoint_id, "collection": original["collection"], "record_id": original["record_id"], "review_revision": checked["review_revision"], "patches": checked["patches"]})
                except (DjangoValidationError, KeyError, TypeError, ValueError, run.checkpoints.model.DoesNotExist):
                    # Invalid/stale/private artifacts are never promoted into form proposals.
                    continue
        return Response({"revision": review.revision, "proposals": proposals})

    @action(detail=True, methods=["post"], url_path="approve-review")
    @transaction.atomic
    def approve_review(self, request, pk=None):
        review = self._existing_review(self.get_object())
        check_review_revision(review, request, required=True)
        if review.status == PrescriptionReview.Status.REJECTED:
            raise ValidationError({"detail": "A rejected review cannot be approved."})
        validator = PrescriptionReviewUpdateSerializer(
            data={"reviewed_data": review.reviewed_data},
            context={"document_id": review.document_id, "approval": True},
        )
        validator.is_valid(raise_exception=True)
        previous_status = review.status
        review.status = PrescriptionReview.Status.APPROVED
        review.approved_revision = review.revision
        review.reviewed_by = request.user
        review.reviewed_at = timezone.now()
        review.save(update_fields=["status", "approved_revision", "reviewed_by", "reviewed_at", "updated_at"])
        PrescriptionReviewChange.objects.create(review=review, changed_by=request.user, field_path="status", previous_value=previous_status, new_value="approved")
        return Response(PrescriptionReviewSerializer(review).data)

    @action(detail=True, methods=["post"], url_path="publish")
    @transaction.atomic
    def publish(self, request, pk=None):
        """Publish a previously approved canonical draft, atomically and idempotently."""
        review = self._existing_review(self.get_object())
        check_review_revision(review, request, required=True)
        observations, counts = publish_review(review, request.user)
        review.refresh_from_db()
        return Response({
            "review": PrescriptionReviewSerializer(review, context={"request": request}).data,
            "observation_ids": [item.pk for item in observations],
            "counts": counts,
        })

    @action(detail=True, methods=["get"], url_path="entry-draft")
    def entry_draft(self, request, pk=None):
        """Return the same canonical draft consumed by future manual intake."""
        review = self._start_review(self.get_object(), request.user)
        validator = PrescriptionReviewUpdateSerializer(
            data={"reviewed_data": review.reviewed_data},
            context={"document_id": review.document_id},
        )
        validator.is_valid(raise_exception=True)
        return Response({
            "document_id": review.document_id,
            "review_id": review.pk,
            "selected_patient": review.selected_patient_id,
            "review_status": review.status,
            "intake_draft": review.reviewed_data,
            "reviewed_data": review.reviewed_data,
        })

    @action(detail=True, methods=["post"], url_path="reopen-review")
    @transaction.atomic
    def reopen_review(self, request, pk=None):
        review = self._existing_review(self.get_object())
        check_review_revision(review, request)
        if review.published_at:
            raise ValidationError({"detail": "A published review cannot be reopened."})
        reason = request.data.get("reason", "").strip()
        if review.status != PrescriptionReview.Status.APPROVED:
            raise ValidationError({"detail": "Only an approved review can be reopened."})
        if not reason:
            raise ValidationError({"reason": "A reopen reason is required."})
        previous_reviewer = review.reviewed_by_id
        previous_reviewed_at = review.reviewed_at.isoformat() if review.reviewed_at else None
        with transaction.atomic():
            review.status = PrescriptionReview.Status.IN_REVIEW
            review.revision += 1
            review.approved_revision = None
            review.reviewed_by = None
            review.reviewed_at = None
            review.save(update_fields=["status", "revision", "approved_revision", "reviewed_by", "reviewed_at", "updated_at"])
            PrescriptionReviewChange.objects.bulk_create([
                PrescriptionReviewChange(review=review, changed_by=request.user, field_path="status", previous_value="approved", new_value="in_review"),
                PrescriptionReviewChange(review=review, changed_by=request.user, field_path="reviewed_by", previous_value=previous_reviewer, new_value=None),
                PrescriptionReviewChange(review=review, changed_by=request.user, field_path="reviewed_at", previous_value=previous_reviewed_at, new_value=None),
                PrescriptionReviewChange(review=review, changed_by=request.user, field_path="reopen_reason", previous_value=None, new_value=reason),
            ])
        return Response(PrescriptionReviewSerializer(review).data)

    @action(detail=True, methods=["post"], url_path="reject-review")
    @transaction.atomic
    def reject_review(self, request, pk=None):
        review = self._existing_review(self.get_object())
        check_review_revision(review, request)
        if review.published_at:
            raise ValidationError({"detail": "A published review cannot be rejected."})
        reason = request.data.get("reason", "").strip()
        if not reason:
            raise ValidationError({"reason": "A rejection reason is required."})
        previous_status = review.status
        review.status = PrescriptionReview.Status.REJECTED
        review.revision += 1
        review.approved_revision = None
        review.notes = reason
        review.reviewed_by = request.user
        review.reviewed_at = timezone.now()
        review.save(update_fields=["status", "revision", "approved_revision", "notes", "reviewed_by", "reviewed_at", "updated_at"])
        PrescriptionReviewChange.objects.create(review=review, changed_by=request.user, field_path="status", previous_value=previous_status, new_value="rejected")
        return Response(PrescriptionReviewSerializer(review).data)


class PrescriptionBatchJobViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Historical backfill submission endpoint; completion remains review-only."""
    queryset = PrescriptionBatchJob.objects.prefetch_related("items__document").select_related("submitted_by")
    serializer_class = PrescriptionBatchJobSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return prescription_batch_jobs_for_user(self.request.user).prefetch_related(
            "items__document"
        ).select_related("submitted_by")

    def create(self, request, *args, **kwargs):
        document_ids = request.data.get("document_ids")
        display_name = str(request.data.get("display_name") or "Prescription backfill").strip()
        if not isinstance(document_ids, list) or not document_ids:
            raise ValidationError({"document_ids": "Provide one or more ready-for-review document IDs."})
        if len(document_ids) > 100:
            raise ValidationError({"document_ids": "Submit at most 100 documents per batch."})
        try:
            normalized_ids = [int(item) for item in document_ids]
        except (TypeError, ValueError) as exc:
            raise ValidationError({"document_ids": "Document IDs must be integers."}) from exc
        authorized_ids = set(
            prescription_documents_for_user(request.user)
            .filter(pk__in=normalized_ids)
            .values_list("pk", flat=True)
        )
        if authorized_ids != set(normalized_ids):
            raise ValidationError({"document_ids": "One or more documents are unavailable."})
        try:
            job = create_batch_job(document_ids=normalized_ids, user=request.user, display_name=display_name)
        except ProviderDataPolicyError as exc:
            raise ValidationError({"detail": str(exc), "code": "provider_data_policy"}) from exc
        except ProviderBudgetConfigurationError as exc:
            raise ValidationError({"detail": str(exc), "code": "provider_budget_configuration"}) from exc
        except ProviderBudgetExhausted as exc:
            return Response({"detail": "Shared provider budget is exhausted.", "retry_after_seconds": exc.retry_after_seconds},
                            status=status.HTTP_429_TOO_MANY_REQUESTS, headers={"Retry-After": str(exc.retry_after_seconds)})
        return Response(self.get_serializer(job).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="sync")
    def sync(self, request, pk=None):
        job = self.get_object()
        try:
            task = sync_prescription_batch_job.delay(job.pk)
        except Exception as exc:
            raise ValidationError({"detail": f"Unable to queue batch synchronization: {exc}"}) from exc
        return Response({**self.get_serializer(job).data, "task_id": task.id}, status=status.HTTP_202_ACCEPTED)
