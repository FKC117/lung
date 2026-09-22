from django.contrib import admin

from .models import ExtractionIssue, ExtractionRun, PrescriptionDocument, PrescriptionDrugAlias, PrescriptionPage

admin.site.register((PrescriptionDocument, PrescriptionPage, ExtractionRun, ExtractionIssue, PrescriptionDrugAlias))
