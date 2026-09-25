"""Authorization scopes for prescription intake data.

Prescription artifacts contain patient data.  Ownership or an explicit review
assignment is required for non-staff users; staff users retain registry-wide
operational access.
"""

from django.db.models import Q

from prescriptions.models import PrescriptionBatchJob, PrescriptionDocument


def prescription_documents_for_user(user):
    queryset = PrescriptionDocument.objects.all()
    if not user or not user.is_authenticated:
        return queryset.none()
    if user.is_staff or user.is_superuser:
        return queryset
    return queryset.filter(
        Q(uploaded_by=user)
        | Q(review__assigned_to=user)
        | Q(review__reviewed_by=user)
    ).distinct()


def prescription_batch_jobs_for_user(user):
    queryset = PrescriptionBatchJob.objects.all()
    if not user or not user.is_authenticated:
        return queryset.none()
    if user.is_staff or user.is_superuser:
        return queryset
    return queryset.filter(submitted_by=user)
