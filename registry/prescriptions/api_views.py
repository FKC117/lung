from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import PrescriptionDocument
from .serializers import PrescriptionDocumentSerializer
from .services.processing import process_document


class PrescriptionDocumentViewSet(viewsets.ModelViewSet):
    queryset = PrescriptionDocument.objects.select_related("patient", "uploaded_by").prefetch_related("pages", "issues", "extraction_runs__issues")
    serializer_class = PrescriptionDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

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
