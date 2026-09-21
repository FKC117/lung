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
    MolecularAlterationType,
    MolecularPathologyResult,
    MolecularClinicalSignificance,
    MolecularPanel,
    MolecularPanelVersion,
    MolecularPanelTarget,

    CancerMarkerName,
    
    SurgeryModality,
    SurgeryLaterality,

    RadiotherapySite,
    RadiotherapyIntent,
    RadiotherapyModality,

    TreatmentModality,
    LineOfTreatment,
    TreatmentDrug,
    TreatmentProtocol,
    TreatmentProtocolDrug,

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
    PathologicalResponseCategory,
    TumorRegressionGrade,

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
    MolecularAlterationType,
    MolecularPathologyResult,
    MolecularClinicalSignificance,
    CancerMarkerName,
    SurgeryModality,
    SurgeryLaterality,
    RadiotherapySite,
    RadiotherapyIntent,
    RadiotherapyModality,
    TreatmentModality,
    LineOfTreatment,
    TreatmentDrug,
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
    PathologicalResponseCategory,
    TumorRegressionGrade,
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


@admin.register(MolecularPanel)
class MolecularPanelAdmin(ImportExportModelAdmin):
    list_display = ("id", "name", "manufacturer", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "manufacturer", "description")
    ordering = ("name",)


@admin.register(MolecularPanelVersion)
class MolecularPanelVersionAdmin(ImportExportModelAdmin):
    list_display = ("id", "panel", "version", "method", "reporting_policy", "is_active")
    list_filter = ("reporting_policy", "is_active", "method")
    search_fields = ("panel__name", "version", "method__name")
    list_select_related = ("panel", "method")
    ordering = ("panel__name", "version")


@admin.register(MolecularPanelTarget)
class MolecularPanelTargetAdmin(ImportExportModelAdmin):
    list_display = ("id", "panel_version", "gene", "alteration_type", "is_reportable")
    list_filter = ("alteration_type", "is_reportable")
    search_fields = ("panel_version__panel__name", "panel_version__version", "gene__name")
    list_select_related = ("panel_version__panel", "gene", "alteration_type")


@admin.register(TreatmentProtocolDrug)
class TreatmentProtocolDrugAdmin(ImportExportModelAdmin):
    list_display = ("id", "protocol", "drug", "sequence")
    list_filter = ("protocol", "drug")
    search_fields = ("protocol__name", "drug__name")
    list_select_related = ("protocol", "drug")
    ordering = ("protocol__name", "sequence")



