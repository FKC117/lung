from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from records.models import ClinicalObservation
from prescriptions.models import PrescriptionReview, RecordProvenance

@transaction.atomic
def publish_review(review, user):
    if review.status != PrescriptionReview.Status.APPROVED:
        raise ValidationError("Only approved reviews can be published.")
    if review.published_at:
        raise ValidationError("This review has already been published.")
    if not review.selected_patient_id:
        raise ValidationError("A reviewer must select the patient before publishing.")
    observation = ClinicalObservation.objects.create(
        patient=review.selected_patient,
        status=ClinicalObservation.Status.PUBLISHED,
        published_at=timezone.now(),
        published_by=user,
        clinical_notes="Published from human-reviewed prescription extraction.",
    )
    run = review.document.extraction_runs.filter(status="completed").first()
    RecordProvenance.objects.create(content_type=ContentType.objects.get_for_model(observation), object_id=observation.pk, document=review.document, extraction_run=run, field_path="clinical_observation", reviewer=user)
    review.published_at = timezone.now()
    review.published_by = user
    review.save(update_fields=["published_at", "published_by", "updated_at"])
    return observation
