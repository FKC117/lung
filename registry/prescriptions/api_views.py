from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import MethodNotAllowed, NotFound, ValidationError
from rest_framework.response import Response

from .models import PrescriptionDocument, PrescriptionReview, PrescriptionReviewChange
from .serializers import PrescriptionDocumentSerializer, PrescriptionReviewSerializer, PrescriptionReviewUpdateSerializer
from .services.processing import process_document


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

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PATCH", detail="Update review data through the review endpoint.")

    def create(self, request, *args, **kwargs):
        uploaded = request.FILES.get("file")
        if not uploaded:
            raise ValidationError({"file": "A prescription file is required."})
        checksum = PrescriptionDocument.checksum(uploaded)
        existing = PrescriptionDocument.objects.filter(sha256=checksum).first()
        if existing:
            return Response({"detail": "Duplicate prescription upload.", "document_id": existing.pk}, status=status.HTTP_409_CONFLICT)
        document = PrescriptionDocument.objects.create(
            file=uploaded,
            original_filename=uploaded.name,
            sha256=checksum,
            patient_id=request.data.get("patient") or None,
            uploaded_by=request.user,
        )
        return Response(self.get_serializer(document).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def process(self, request, pk=None):
        document = self.get_object()
        if document.status != PrescriptionDocument.Status.UPLOADED:
            return Response({"detail": "Only a newly uploaded document can be processed."}, status=status.HTTP_409_CONFLICT)
        process_document(document)
        document.refresh_from_db()
        return Response(self.get_serializer(document).data)

    def _start_review(self, document, user):
        latest_run = document.extraction_runs.filter(status="completed").first()
        review, _ = PrescriptionReview.objects.get_or_create(document=document)
        if not review.reviewed_data:
            if not latest_run:
                raise ValidationError({"detail": "Process the document before starting review."})
            review.reviewed_data = latest_run.structured_data
            review.assigned_to = review.assigned_to or user
            review.save(update_fields=["reviewed_data", "assigned_to", "updated_at"])
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
        serializer = PrescriptionReviewUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            changes = []
            if "reviewed_data" in serializer.validated_data and serializer.validated_data["reviewed_data"] != review.reviewed_data:
                changes.extend(json_changes(review.reviewed_data, serializer.validated_data["reviewed_data"]))
                review.reviewed_data = serializer.validated_data["reviewed_data"]
            if "selected_patient" in serializer.validated_data and serializer.validated_data["selected_patient"] != review.selected_patient:
                old = review.selected_patient_id
                review.selected_patient = serializer.validated_data["selected_patient"]
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
        if not review.reviewed_data:
            raise ValidationError({"detail": "Review data is required before approval."})
        previous_status = review.status
        review.status = PrescriptionReview.Status.APPROVED
        review.reviewed_by = request.user
        review.reviewed_at = timezone.now()
        review.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        PrescriptionReviewChange.objects.create(review=review, changed_by=request.user, field_path="status", previous_value=previous_status, new_value="approved")
        return Response(PrescriptionReviewSerializer(review).data)

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
