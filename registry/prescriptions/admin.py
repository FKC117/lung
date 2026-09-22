from django.contrib import admin

from .models import ExtractionIssue, ExtractionRun, PrescriptionDocument, PrescriptionDrugAlias, PrescriptionPage, PrescriptionReview, PrescriptionReviewChange

admin.site.register((PrescriptionDocument, PrescriptionPage, ExtractionRun, ExtractionIssue, PrescriptionDrugAlias, PrescriptionReview, PrescriptionReviewChange))
