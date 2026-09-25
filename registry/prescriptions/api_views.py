from django.http import FileResponse
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import MethodNotAllowed, NotFound, ValidationError
from rest_framework.response import Response

from .models import PrescriptionBatchJob, PrescriptionDocument, PrescriptionReview, PrescriptionReviewChange
from .serializers import PrescriptionBatchJobSerializer, PrescriptionDocumentSerializer, PrescriptionReviewSerializer, PrescriptionReviewUpdateSerializer
from .services.batch import create_batch_job, sync_batch_job
from .services.access import prescription_batch_jobs_for_user, prescription_documents_for_user
from .services.draft_schema import is_canonical_draft
from .services.intake_draft import build_intake_draft
from .tasks import process_prescription_document, sync_prescription_batch_job


_MISSING = object()


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
        if document.status != PrescriptionDocument.Status.UPLOADED:
            return Response({"detail": "Only a newly uploaded document can be processed."}, status=status.HTTP_409_CONFLICT)
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

    def _start_review(self, document, user):
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
            return document.review
        except PrescriptionReview.DoesNotExist as exc:
            raise NotFound("Start a review before viewing or changing it.") from exc

    @action(detail=True, methods=["post"], url_path="start-review")
    def start_review(self, request, pk=None):
        review = self._start_review(self.get_object(), request.user)
        return Response(PrescriptionReviewSerializer(review).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "patch"], url_path="review")
    def review(self, request, pk=None):
        review = self._existing_review(self.get_object())
        if request.method == "GET":
            return Response(PrescriptionReviewSerializer(review).data)
        if review.status in {PrescriptionReview.Status.APPROVED, PrescriptionReview.Status.REJECTED}:
            raise ValidationError({"detail": "A completed review cannot be edited. Start a new review if correction is required."})
        serializer = PrescriptionReviewUpdateSerializer(
            data=request.data,
            partial=True,
            context={"document_id": review.document_id},
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
            review.assigned_to = review.assigned_to or request.user
            review.save()
            PrescriptionReviewChange.objects.bulk_create([
                PrescriptionReviewChange(review=review, changed_by=request.user, field_path=path, previous_value=old, new_value=new)
                for path, old, new in changes
            ])
        return Response(PrescriptionReviewSerializer(review).data)

    @action(detail=True, methods=["post"], url_path="approve-review")
    def approve_review(self, request, pk=None):
        review = self._existing_review(self.get_object())
        if review.status == PrescriptionReview.Status.REJECTED:
            raise ValidationError({"detail": "A rejected review cannot be approved."})
        validator = PrescriptionReviewUpdateSerializer(
            data={"reviewed_data": review.reviewed_data},
            context={"document_id": review.document_id, "approval": True},
        )
        validator.is_valid(raise_exception=True)
        previous_status = review.status
        review.status = PrescriptionReview.Status.APPROVED
        review.reviewed_by = request.user
        review.reviewed_at = timezone.now()
        review.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        PrescriptionReviewChange.objects.create(review=review, changed_by=request.user, field_path="status", previous_value=previous_status, new_value="approved")
        return Response(PrescriptionReviewSerializer(review).data)

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
    def reopen_review(self, request, pk=None):
        review = self._existing_review(self.get_object())
        reason = request.data.get("reason", "").strip()
        if review.status != PrescriptionReview.Status.APPROVED:
            raise ValidationError({"detail": "Only an approved review can be reopened."})
        if not reason:
            raise ValidationError({"reason": "A reopen reason is required."})
        previous_reviewer = review.reviewed_by_id
        previous_reviewed_at = review.reviewed_at.isoformat() if review.reviewed_at else None
        with transaction.atomic():
            review.status = PrescriptionReview.Status.IN_REVIEW
            review.reviewed_by = None
            review.reviewed_at = None
            review.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
            PrescriptionReviewChange.objects.bulk_create([
                PrescriptionReviewChange(review=review, changed_by=request.user, field_path="status", previous_value="approved", new_value="in_review"),
                PrescriptionReviewChange(review=review, changed_by=request.user, field_path="reviewed_by", previous_value=previous_reviewer, new_value=None),
                PrescriptionReviewChange(review=review, changed_by=request.user, field_path="reviewed_at", previous_value=previous_reviewed_at, new_value=None),
                PrescriptionReviewChange(review=review, changed_by=request.user, field_path="reopen_reason", previous_value=None, new_value=reason),
            ])
        return Response(PrescriptionReviewSerializer(review).data)

    @action(detail=True, methods=["post"], url_path="reject-review")
    def reject_review(self, request, pk=None):
        review = self._existing_review(self.get_object())
        reason = request.data.get("reason", "").strip()
        if not reason:
            raise ValidationError({"reason": "A rejection reason is required."})
        previous_status = review.status
        review.status = PrescriptionReview.Status.REJECTED
        review.notes = reason
        review.reviewed_by = request.user
        review.reviewed_at = timezone.now()
        review.save(update_fields=["status", "notes", "reviewed_by", "reviewed_at", "updated_at"])
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
        job = create_batch_job(document_ids=normalized_ids, user=request.user, display_name=display_name)
        return Response(self.get_serializer(job).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="sync")
    def sync(self, request, pk=None):
        job = self.get_object()
        try:
            task = sync_prescription_batch_job.delay(job.pk)
        except Exception as exc:
            raise ValidationError({"detail": f"Unable to queue batch synchronization: {exc}"}) from exc
        return Response({**self.get_serializer(job).data, "task_id": task.id}, status=status.HTTP_202_ACCEPTED)
