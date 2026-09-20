from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import (
    ClinicalObservation,
    Diagnosis,
    Histopathology,
    IHCResult,
    ClinicalTNMStaging,
    PathologicalTNMStaging,
    PathologicalStagingResult,
    MolecularTest,
    MolecularTestResult,
    MetastaticSiteRecord,
    Patient,
    PatientAnthropometry,
    PatientComorbidity,
)


@admin.register(Patient)
class PatientAdmin(ImportExportModelAdmin):
    list_display = ("id", "registration_no", "patient_id", "name", "sex", "phone", "is_draft")
    list_filter = ("sex", "type_of_patient", "is_draft", "district")
    search_fields = ("registration_no", "patient_id", "name", "phone", "email", "nid", "passport")
    list_select_related = ("sex", "type_of_patient", "district")
    ordering = ("patient_id",)


@admin.register(ClinicalObservation)
class ClinicalObservationAdmin(ImportExportModelAdmin):
    list_display = ("id", "patient", "doctor", "center", "observed_at", "status")
    list_filter = ("status", "center", "doctor")
    search_fields = ("patient__patient_id", "patient__name", "doctor__name", "center__name")
    list_select_related = ("patient", "doctor", "center")
    ordering = ("-observed_at", "-id")


@admin.register(PatientAnthropometry)
class PatientAnthropometryAdmin(ImportExportModelAdmin):
    list_display = ("id", "observation", "height_cm", "weight_kg", "bmi", "bsa")
    search_fields = ("observation__patient__patient_id", "observation__patient__name")
    list_select_related = ("observation__patient",)


@admin.register(PatientComorbidity)
class PatientComorbidityAdmin(ImportExportModelAdmin):
    list_display = ("id", "observation", "comorbidity", "diagnosed_on", "is_active")
    list_filter = ("comorbidity", "is_active")
    search_fields = ("observation__patient__patient_id", "observation__patient__name", "comorbidity__name")
    list_select_related = ("observation__patient", "comorbidity")


@admin.register(Diagnosis)
class DiagnosisAdmin(ImportExportModelAdmin):
    list_display = ("id", "observation", "disease_group", "disease_subgroup", "primary_site", "diagnosed_on")
    list_filter = ("disease_group", "primary_site", "laterality")
    search_fields = ("observation__patient__patient_id", "observation__patient__name", "diagnosis_in_details")
    list_select_related = ("observation__patient", "disease_group", "disease_subgroup", "primary_site", "laterality")


@admin.register(MetastaticSiteRecord)
class MetastaticSiteRecordAdmin(ImportExportModelAdmin):
    list_display = ("id", "diagnosis", "site", "identified_on")
    list_filter = ("site",)
    search_fields = ("diagnosis__observation__patient__patient_id", "diagnosis__observation__patient__name", "site__name")
    list_select_related = ("diagnosis__observation__patient", "site")


@admin.register(Histopathology)
class HistopathologyAdmin(ImportExportModelAdmin):
    list_display = ("id", "observation", "histopathology_type", "biopsy_date", "report_date")
    list_filter = ("histopathology_type", "histopathology_grade", "histopathology_site")
    search_fields = ("observation__patient__patient_id", "observation__patient__name", "report_summary")
    list_select_related = ("observation__patient", "histopathology_type", "histopathology_grade", "histopathology_site")


@admin.register(IHCResult)
class IHCResultAdmin(ImportExportModelAdmin):
    list_display = ("id", "observation", "marker", "result", "tested_at", "percentage")
    list_filter = ("marker", "result")
    search_fields = ("observation__patient__patient_id", "observation__patient__name", "marker__name", "result__name")
    list_select_related = ("observation__patient", "marker", "result")


@admin.register(PathologicalStagingResult)
class PathologicalStagingResultAdmin(ImportExportModelAdmin):
    list_display = ("id", "observation", "feature", "result", "assessed_at", "percentage")
    list_filter = ("feature", "result")
    search_fields = ("observation__patient__patient_id", "observation__patient__name", "feature__name", "result__name")
    list_select_related = ("observation__patient", "feature", "result")


class TNMStagingAdmin(ImportExportModelAdmin):
    list_display = ("id", "observation", "t", "n", "m", "stage", "staged_on")
    list_filter = ("t", "n", "m", "stage")
    search_fields = ("observation__patient__patient_id", "observation__patient__name")
    list_select_related = ("observation__patient", "t", "n", "m", "stage")


admin.site.register(ClinicalTNMStaging, TNMStagingAdmin)
admin.site.register(PathologicalTNMStaging, TNMStagingAdmin)


@admin.register(MolecularTest)
class MolecularTestAdmin(ImportExportModelAdmin):
    list_display = ("id", "observation", "panel_version", "method", "specimen", "reported_on", "status", "qc_status")
    list_filter = ("status", "qc_status", "method", "specimen")
    search_fields = ("observation__patient__patient_id", "observation__patient__name", "laboratory", "accession_number")
    list_select_related = ("observation__patient", "panel_version", "method", "specimen")


@admin.register(MolecularTestResult)
class MolecularTestResultAdmin(ImportExportModelAdmin):
    list_display = ("id", "molecular_test", "gene", "exon", "alteration_type", "result", "origin")
    list_filter = ("alteration_type", "result", "clinical_significance", "origin")
    search_fields = ("molecular_test__observation__patient__patient_id", "gene__name", "exon__name", "dna_change", "protein_change", "common_name")
    list_select_related = ("molecular_test__observation__patient", "gene", "exon", "alteration_type", "result", "clinical_significance")
