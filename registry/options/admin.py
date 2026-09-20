from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import (
    SiteSettings,
    Center,
    Doctor,
    PatientType,
    District,
    Thana,
    Sex,
    EconomicStatus,
    BloodGroup,
    MaritalStatus,
    AlcoholHistory,
    SmokingHistory,
    TBHistory,
    CovidHistory,
    Vaccine,
    VaccinationDose,

    DiagnosisDiseaseGroup,
    DiagnosisDiseaseSubgroup,
    DiagnosisPrimarySite,
    DiagnosisMetastaticSite,
    DiagnosisLaterality,

    Comorbidity,

    HistopathologyDetails,
    HistopathologyType,
    HistopathologySite,
    HistopathologyGrade,

    IHCCycle,
    IHCCycleResult,
    IHCStagingCycle,
    IHCStagingCycleResult,

    TNMT,
    TNMN,
    TNMM,
    TNMStage,

    MolecularPathologyMethod,
    MolecularPathologySpecimen,
    MolecularPathologyGene,
    MolecularPathologyExon,
    MolecularPathologyMutation,
    MolecularPathologyProteinMutation,
    MolecularPathologyResult,

    CancerMarkerName,
    
    SurgeryModality,
    SurgeryLaterality,

    RadiotherapySite,
    RadiotherapyIntent,
    RadiotherapyModality,

    TreatmentModality,
    LineOfTreatment,
    TreatmentProtocol,
    TreatmentProtocolCycleNo,

    RECISTTargetLesion,
    RECISTNonTargetLesion,
    RECISTNewLesion,
    RECISTResponseResult,

    IRECISTTargetLesion,
    IRECISTNonTargetLesion,
    IRECISTNewLesion,
    IRECISTResponseResult,

    ProgressionSite,
    ResponseEstimationMethod,

    RECIST11Assessment,
    IRECISTAssessment,

    PathologicalResponseTargetLesion,
    PathologicalResponseNonTargetLesion,
    PathologicalResponseNewLesion,
    PathologicalResponseResult,
    PathologicalResponseAssessment,

    DiseaseProgressionStatus,
    SurvivalStatus
)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("site_title",)
    fieldsets = (
        ("Registry identity", {"fields": ("site_title", "header_eyebrow", "site_description")} ),
        ("Brand assets", {"fields": ("logo", "logo_alt_text", "favicon")} ),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# Common lookup models
lookup_models = [
    PatientType,
    District,
    Sex,
    EconomicStatus,
    BloodGroup,
    MaritalStatus,
    AlcoholHistory,
    SmokingHistory,
    TBHistory,
    CovidHistory,
    Vaccine,
    VaccinationDose,
    DiagnosisDiseaseGroup,
    DiagnosisPrimarySite,
    DiagnosisMetastaticSite,
    DiagnosisLaterality,
    Comorbidity,
    HistopathologyDetails,
    HistopathologyType,
    HistopathologySite,
    HistopathologyGrade,
    IHCCycle,
    IHCCycleResult,
    IHCStagingCycle,
    IHCStagingCycleResult,
    TNMT,
    TNMN,
    TNMM,
    TNMStage,
    MolecularPathologyMethod,
    MolecularPathologySpecimen,
    MolecularPathologyGene,
    MolecularPathologyMutation,
    MolecularPathologyProteinMutation,
    MolecularPathologyResult,
    CancerMarkerName,
    SurgeryModality,
    SurgeryLaterality,
    RadiotherapySite,
    RadiotherapyIntent,
    RadiotherapyModality,
    TreatmentModality,
    LineOfTreatment,
    TreatmentProtocol,
    RECISTTargetLesion,
    RECISTNonTargetLesion,
    RECISTNewLesion,
    RECISTResponseResult,
    IRECISTTargetLesion,
    IRECISTNonTargetLesion,
    IRECISTNewLesion,
    IRECISTResponseResult,
    ProgressionSite,
    ResponseEstimationMethod,
    PathologicalResponseTargetLesion,
    PathologicalResponseNonTargetLesion,
    PathologicalResponseNewLesion,
    PathologicalResponseResult,
    DiseaseProgressionStatus,
    SurvivalStatus,
]



class LookupAdmin(ImportExportModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("name",)


for model in lookup_models:
    admin.site.register(model, LookupAdmin)


@admin.register(Center)
class CenterAdmin(ImportExportModelAdmin):
    list_display = ("id", "name", "source_created_at", "source_updated_at")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Doctor)
class DoctorAdmin(ImportExportModelAdmin):
    list_display = ("id", "name", "bmdc_number", "phone", "email", "institution", "center", "status")
    list_filter = ("center", "status")
    search_fields = ("name", "bmdc_number", "phone", "email", "institution", "center__name")
    list_select_related = ("center",)
    ordering = ("name",)


# @admin.register(DoctorDegree)
# class DoctorDegreeAdmin(ImportExportModelAdmin):
#     list_display = ("id", "legacy_id", "doctor", "degree")
#     list_filter = ("degree",)
#     search_fields = ("doctor__name", "degree")
#     list_select_related = ("doctor",)


# @admin.register(DoctorRecognitionRecord)
# class DoctorRecognitionRecordAdmin(ImportExportModelAdmin):
#     list_display = ("id", "legacy_id", "group", "value")
#     list_filter = ("group",)
#     search_fields = ("group", "value")


# @admin.register(OptionProvenance)
# class OptionProvenanceAdmin(ImportExportModelAdmin):
#     list_display = ("content_type", "object_id", "legacy_id", "is_active")
#     list_filter = ("content_type", "is_active")
#     search_fields = ("legacy_id",)


# @admin.register(OptionAlias)
# class OptionAliasAdmin(ImportExportModelAdmin):
#     list_display = ("content_type", "object_id", "alias", "is_active")
#     list_filter = ("content_type", "is_active")
#     search_fields = ("alias", "normalized_alias")


@admin.register(Thana)
class ThanaAdmin(ImportExportModelAdmin):
    list_display = ("id", "name", "district")
    list_filter = ("district",)
    search_fields = ("name", "district__name")
    ordering = ("district__name", "name")


@admin.register(DiagnosisDiseaseSubgroup)
class DiagnosisDiseaseSubgroupAdmin(ImportExportModelAdmin):
    list_display = ("id", "name", "disease_group")
    list_filter = ("disease_group",)
    search_fields = ("name", "disease_group__name")
    ordering = ("disease_group__name", "name")


@admin.register(MolecularPathologyExon)
class MolecularPathologyExonAdmin(ImportExportModelAdmin):
    list_display = ("id", "name", "gene")
    list_filter = ("gene",)
    search_fields = ("name", "gene__name")
    ordering = ("gene__name", "name")

# @admin.register(CancerMarkerUnit)
# class CancerMarkerUnitAdmin(ImportExportModelAdmin):
#     list_display = ("id", "name", "marker")
#     list_filter = ("marker",)
#     search_fields = ("name", "marker__name")
#     ordering = ("marker__name", "name")

@admin.register(RECIST11Assessment)
class RECIST11AssessmentAdmin(ImportExportModelAdmin):
    list_display = (
        "id",
        "target_lesion",
        "non_target_lesion",
        "new_lesion",
        "response_result",
    )

    list_filter = (
        "target_lesion",
        "non_target_lesion",
        "new_lesion",
        "response_result",
    )

    search_fields = (
        "target_lesion__name",
        "non_target_lesion__name",
        "new_lesion__name",
        "response_result__name",
    )

    ordering = ("id",)


@admin.register(IRECISTAssessment)
class IRECISTAssessmentAdmin(ImportExportModelAdmin):
    list_display = (
        "id",
        "target_lesion",
        "non_target_lesion",
        "new_lesion",
        "response_result",
    )

    list_filter = (
        "target_lesion",
        "non_target_lesion",
        "new_lesion",
        "response_result",
    )

    search_fields = (
        "target_lesion__name",
        "non_target_lesion__name",
        "new_lesion__name",
        "response_result__name",
    )

    ordering = ("id",)

@admin.register(PathologicalResponseAssessment)
class PathologicalResponseAssessmentAdmin(ImportExportModelAdmin):
    list_display = (
        "id",
        "target_lesion",
        "non_target_lesion",
        "new_lesion",
        "response_result",
    )

    list_filter = (
        "target_lesion",
        "non_target_lesion",
        "new_lesion",
        "response_result",
    )

    search_fields = (
        "target_lesion__name",
        "non_target_lesion__name",
        "new_lesion__name",
        "response_result__name",
    )

    ordering = ("id",)

@admin.register(TreatmentProtocolCycleNo)
class TreatmentProtocolCycleNoAdmin(ImportExportModelAdmin):
    list_display = ("id", "cycle_no", "protocol")
    list_filter = ("protocol",)
    search_fields = ("cycle_no", "protocol__name")
    ordering = ("protocol__name", "cycle_no")
