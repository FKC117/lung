from django.conf import settings
from decimal import Decimal
from django.db import models

# Create your models here.
from options.models import (
    Center,
    Doctor,
    PatientType,
    Sex,
    District,
    Thana,
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
    MolecularPathologyResult,
    MolecularClinicalSignificance,
    MolecularAlterationType,
    MolecularPanel,
    MolecularPanelTarget,
    MolecularPanelVersion,

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


class Patient(models.Model):
    registration_no = models.CharField(max_length=64, unique=True)
    patient_id = models.CharField(max_length=100, unique=True)

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    nid = models.CharField(max_length=50, blank=True)
    passport = models.CharField(max_length=50, blank=True)
    photo = models.CharField(max_length=255, blank=True)

    sex = models.ForeignKey(
        Sex,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    date_of_birth = models.DateField(null=True, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)

    district = models.ForeignKey(
        District,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    thana = models.ForeignKey(
        Thana,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    area = models.TextField(blank=True)
    marital_status = models.ForeignKey(
        MaritalStatus,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    alcohol_history = models.ForeignKey(
        AlcoholHistory,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )


    economic_status = models.ForeignKey(
        EconomicStatus,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    blood_group = models.ForeignKey(
        BloodGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    type_of_patient = models.ForeignKey(
        PatientType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    first_diagnosis_date = models.DateField(null=True, blank=True)
    dietary_habits = models.TextField(max_length=250, blank=True)
    personal_history_of_cancer = models.TextField(max_length=250, blank=True)
    family_history_of_cancer = models.TextField(max_length=250, blank=True)
    any_known_mutation = models.TextField(null=True, blank=True)

    smoking_history = models.ForeignKey(
        SmokingHistory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    cigarettes_per_day = models.PositiveIntegerField(null=True, blank=True)
    smoking_duration_in_years = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    quit_smoking_for_in_years = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    pack_years = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        editable=False,
    )

    tb_history = models.ForeignKey(
        TBHistory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    covid_history = models.ForeignKey(
        CovidHistory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    covid_infection_date = models.DateField(null=True, blank=True)
    vaccine = models.ForeignKey(
        Vaccine,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    vaccination_dose = models.ForeignKey(
        VaccinationDose,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    is_draft = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if (
            self.cigarettes_per_day is not None
            and self.smoking_duration_in_years is not None
        ):
            self.pack_years = (
                Decimal(self.cigarettes_per_day)
                / Decimal("20")
                * self.smoking_duration_in_years
            ).quantize(Decimal("0.01"))
        else:
            self.pack_years = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient_id} - {self.name}"



class ClinicalObservation(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        REVIEWED = "reviewed", "Reviewed"
        PUBLISHED = "published", "Published"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="observations",
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clinical_observations",
    )
    center = models.ForeignKey(
        Center,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clinical_observations",
    )

    observed_at = models.DateTimeField(null=True, blank=True)
    prescription_date = models.DateField(null=True, blank=True)

    prescription_age_years = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    prescription_age_months = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    prescription_age_days = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    clinical_notes = models.TextField(blank=True)

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="published_clinical_observations",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-observed_at", "-id")
        indexes = [
            models.Index(
                fields=["patient", '-observed_at'],
                name="obs_patient_date_idx",
            ),
            models.Index(
                fields=["status", "-observed_at"],
                name="obs_status_date_idx",
            ),
            models.Index(
                fields=["prescription_date"],
                name="obs_prescription_idx",
            ),
        ]

    def __str__(self):
        return f"Observation {self.pk} - {self.patient}"


class PatientAnthropometry(models.Model):
    observation = models.OneToOneField(
        ClinicalObservation,
        on_delete=models.CASCADE,
        related_name="anthropometry",
    )

    height_cm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    weight_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    bmi = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        editable=False,
    )
    bsa = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        editable=False,
    )

    def save(self, *args, **kwargs):
        if self.height_cm and self.weight_kg and self.height_cm > 0:
            height_m = self.height_cm / Decimal("100")

            # BMI = weight (kg) / height² (m)
            self.bmi = (
                self.weight_kg / (height_m ** 2)
            ).quantize(Decimal("0.01"))

            # Mosteller BSA = √[(height cm × weight kg) / 3600]
            self.bsa = (
                (self.height_cm * self.weight_kg / Decimal("3600")).sqrt()
            ).quantize(Decimal("0.01"))
        else:
            self.bmi = None
            self.bsa = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Anthropometry - {self.observation}"


class PatientComorbidity(models.Model):
    observation = models.ForeignKey(
        ClinicalObservation,
        on_delete=models.CASCADE,
        related_name="comorbidities",
    )
    comorbidity = models.ForeignKey(
        Comorbidity,
        on_delete=models.PROTECT,
    )

    diagnosed_on = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["observation", "is_active"],
                name="comorb_obs_active_idx",
            ),
            models.Index(
                fields=["diagnosed_on"],
                name="comorb_diagnosed_idx",
            ),
        ]

    def __str__(self):
        return f"{self.comorbidity} - {self.observation}"


class Diagnosis(models.Model):
    observation = models.ForeignKey(
        ClinicalObservation,
        on_delete=models.CASCADE,
        related_name="diagnoses",
    )

    diagnosed_on = models.DateField(null=True, blank=True)

    disease_group = models.ForeignKey(
        DiagnosisDiseaseGroup,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    disease_subgroup = models.ForeignKey(
        DiagnosisDiseaseSubgroup,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    primary_site = models.ForeignKey(
        DiagnosisPrimarySite,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    laterality = models.ForeignKey(
        DiagnosisLaterality,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    diagnosis_in_details = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["observation", "diagnosed_on"],
                name="diagnosis_obs_date_idx",
            ),
        ]

    def __str__(self):
        return f"Diagnosis for {self.observation}"


class MetastaticSiteRecord(models.Model):
    diagnosis = models.ForeignKey(
        Diagnosis,
        on_delete=models.CASCADE,
        related_name="metastatic_site_records",
    )
    site = models.ForeignKey(
        DiagnosisMetastaticSite,
        on_delete=models.PROTECT,
    )

    identified_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["diagnosis", "identified_on"],
                name="metastasis_diag_date_idx",
            ),
            models.Index(
                fields=["site", "identified_on"],
                name="metastasis_site_date_idx",
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["diagnosis", "site", "identified_on"],
                name="unique_diagnosis_metastatic_site_date",
            )
        ]

    def __str__(self):
        return f"{self.site} - {self.diagnosis}"


class Histopathology(models.Model):
    observation = models.ForeignKey(
        ClinicalObservation,
        on_delete=models.CASCADE,
        related_name="histopathologies",
    )

    biopsy_date = models.DateField(null=True, blank=True)
    report_date = models.DateField(null=True, blank=True)

    histopathology_details = models.ForeignKey(
        HistopathologyDetails,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    histopathology_type = models.ForeignKey(
        HistopathologyType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    histopathology_site = models.ForeignKey(
        HistopathologySite,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    histopathology_grade = models.ForeignKey(
        HistopathologyGrade,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    report_summary = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["observation", "biopsy_date"],
                name="histopath_obs_biopsy_idx",
            ),
            models.Index(
                fields=["histopathology_type", "report_date"],
                name="histopath_type_date_idx",
            ),
        ]

    def __str__(self):
        return f"Histopathology for {self.observation}"

class IHCResult(models.Model):
    observation = models.ForeignKey(
        ClinicalObservation,
        on_delete=models.CASCADE,
        related_name="ihc_results",
    )
    tested_at = models.DateField(null=True, blank=True)

    marker = models.ForeignKey(
        IHCCycle,
        on_delete=models.PROTECT,
    )
    result = models.ForeignKey(
        IHCCycleResult,
        on_delete=models.PROTECT,
    )

    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["observation", "tested_at"],
                name="ihc_obs_date_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["observation", "tested_at", "marker"],
                name="unique_ihc_marker_date",
            )
        ]

    def __str__(self):
        return f"{self.marker} - {self.result}"

class PathologicalStagingResult(models.Model):
    observation = models.ForeignKey(
        ClinicalObservation,
        on_delete=models.CASCADE,
        related_name="pathological_staging_results",
    )
    assessed_at = models.DateField(null=True, blank=True)

    feature = models.ForeignKey(
        IHCStagingCycle,
        on_delete=models.PROTECT,
    )
    result = models.ForeignKey(
        IHCStagingCycleResult,
        on_delete=models.PROTECT,
    )

    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["observation", "assessed_at"],
                name="pathstage_obs_date_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["observation", "assessed_at", "feature"],
                name="unique_pathstage_feature_date",
            )
        ]

    def __str__(self):
        return f"{self.feature} - {self.result}"

class ClinicalTNMStaging(models.Model):
    observation = models.ForeignKey(
        ClinicalObservation,
        on_delete=models.CASCADE,
        related_name="clinical_tnm_stagings",
    )

    t = models.ForeignKey(
        TNMT,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    n = models.ForeignKey(
        TNMN,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    m = models.ForeignKey(
        TNMM,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    stage = models.ForeignKey(
        TNMStage,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    staged_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["observation", "staged_on"],
                name="clinical_tnm_obs_date_idx",
            ),
        ]

    def __str__(self):
        return f"Clinical TNM - {self.observation}"

class PathologicalTNMStaging(models.Model):
    observation = models.ForeignKey(
        ClinicalObservation,
        on_delete=models.CASCADE,
        related_name="pathological_tnm_stagings",
    )

    t = models.ForeignKey(
        TNMT,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    n = models.ForeignKey(
        TNMN,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    m = models.ForeignKey(
        TNMM,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    stage = models.ForeignKey(
        TNMStage,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    staged_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["observation", "staged_on"],
                name="path_tnm_obs_date_idx",
            ),
        ]

    def __str__(self):
        return f"Pathological TNM - {self.observation}"

# Molecular pathology starts here

class MolecularTest(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class QCStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PASSED = "passed", "Passed"
        PARTIAL = "partial", "Partially passed"
        FAILED = "failed", "Failed"

    observation = models.ForeignKey(
        ClinicalObservation,
        on_delete=models.CASCADE,
        related_name="molecular_tests",
    )

    panel_version = models.ForeignKey(
        MolecularPanelVersion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tests",
    )
    method = models.ForeignKey(
        MolecularPathologyMethod,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    specimen = models.ForeignKey(
        MolecularPathologySpecimen,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    specimen_collected_on = models.DateField(null=True, blank=True)
    tested_on = models.DateField(null=True, blank=True)
    reported_on = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    qc_status = models.CharField(
        max_length=20,
        choices=QCStatus.choices,
        default=QCStatus.PENDING,
    )

    laboratory = models.CharField(max_length=191, blank=True)
    accession_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["observation", "reported_on"],
                name="molecular_test_obs_date_idx",
            ),
            models.Index(
                fields=["status", "qc_status"],
                name="molecular_test_status_idx",
            ),
        ]

    def __str__(self):
        return f"Molecular test - {self.observation}"

class MolecularTestResult(models.Model):
    class Origin(models.TextChoices):
        EXPLICIT = "explicit", "Explicitly reported"
        DERIVED = "derived", "Automatically derived"
        MANUAL = "manual", "Manually entered"

    molecular_test = models.ForeignKey(
        MolecularTest,
        on_delete=models.CASCADE,
        related_name="results",
    )

    panel_target = models.ForeignKey(
        MolecularPanelTarget,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="test_results",
    )

    gene = models.ForeignKey(
        MolecularPathologyGene,
        on_delete=models.PROTECT,
        related_name="test_results",
    )
    exon = models.ForeignKey(
        MolecularPathologyExon,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="test_results",
    )
    alteration_type = models.ForeignKey(
        MolecularAlterationType,
        on_delete=models.PROTECT,
    )
    result = models.ForeignKey(
        MolecularPathologyResult,
        on_delete=models.PROTECT,
    )

    partner_gene = models.ForeignKey(
        MolecularPathologyGene,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="fusion_partner_results",
    )

    dna_change = models.CharField(max_length=191, blank=True)
    protein_change = models.CharField(max_length=191, blank=True)
    common_name = models.CharField(max_length=191, blank=True)

    variant_allele_frequency = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    copy_number = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )

    clinical_significance = models.ForeignKey(
        MolecularClinicalSignificance,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    origin = models.CharField(
        max_length=20,
        choices=Origin.choices,
        default=Origin.EXPLICIT,
    )
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["molecular_test", "gene"],
                name="molecular_result_test_gene_idx",
            ),
            models.Index(
                fields=["gene", "result"],
                name="molecular_gene_result_idx",
            ),
        ]

    def __str__(self):
        return f"{self.gene} - {self.result}"














