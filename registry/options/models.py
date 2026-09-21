from django.db import models

# Create your models here.
from django.contrib.contenttypes.models import ContentType
from django.db import models
import re


class SiteSettings(models.Model):
    """Singleton configuration for registry-wide presentation settings."""

    site_title = models.CharField(max_length=120, default="Lungcancer Registry")
    header_eyebrow = models.CharField(max_length=120, default="Lung Cancer Registry")
    site_description = models.CharField(max_length=255, blank=True)
    logo = models.FileField(upload_to="site-branding/logos/", blank=True)
    logo_alt_text = models.CharField(max_length=120, default="Lungcancer Registry logo")
    favicon = models.FileField(upload_to="site-branding/favicons/", blank=True)

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def save(self, *args, **kwargs):
        # The admin exposes one editable registry-wide settings record.
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.site_title


class Center(models.Model):
    name = models.CharField(max_length=191, unique=True)
    source_created_at = models.DateTimeField(null=True, blank=True)
    source_updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


class Doctor(models.Model):
    name = models.CharField(max_length=191)
    degree = models.CharField(max_length=250, blank=True)
    bmdc_number = models.CharField(max_length=32, blank=True)
    institution = models.CharField(max_length=255, blank=True)
    center = models.ForeignKey(Center, on_delete=models.SET_NULL, null=True, blank=True, related_name="doctors")
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    designation = models.CharField(max_length=50, blank=True)
    department = models.CharField(max_length=50, blank=True)
    photo = models.CharField(max_length=55, blank=True)
    status = models.CharField(max_length=10, blank=True)
    source_created_at = models.DateTimeField(null=True, blank=True)
    source_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Doctor"
        verbose_name_plural = "Doctors"
        constraints = [models.UniqueConstraint(fields=("name", "bmdc_number", "institution"), name="unique_doctor_identity")]

    def __str__(self):
        return self.name


# class DoctorDegree(models.Model):
#     doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="degrees")
#     degree = models.CharField(max_length=50)
#     source_created_at = models.DateTimeField(null=True, blank=True)
#     source_updated_at = models.DateTimeField(null=True, blank=True)

#     class Meta:
#         constraints = [models.UniqueConstraint(fields=("doctor", "degree"), name="unique_doctor_degree")]

#     def __str__(self):
#         return f"{self.doctor.name}: {self.degree}"


# class DoctorRecognitionRecord(models.Model):
#     legacy_id = models.PositiveBigIntegerField(unique=True, null=True, blank=True)
#     group = models.CharField(max_length=191)
#     value = models.CharField(max_length=191)

#     def __str__(self):
#         return f"{self.group}: {self.value}"


# class OptionProvenance(models.Model):
#     content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
#     object_id = models.PositiveBigIntegerField()
#     legacy_id = models.PositiveBigIntegerField(null=True, blank=True)
#     is_active = models.BooleanField(default=True)
#     source_created_at = models.DateTimeField(null=True, blank=True)
#     source_updated_at = models.DateTimeField(null=True, blank=True)

#     class Meta:
#         constraints = [
#             models.UniqueConstraint(fields=("content_type", "object_id"), name="unique_option_provenance_object"),
#             models.UniqueConstraint(fields=("content_type", "legacy_id"), name="unique_option_provenance_legacy"),
#         ]


# class OptionAlias(models.Model):
#     content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
#     object_id = models.PositiveBigIntegerField()
#     alias = models.CharField(max_length=191)
#     normalized_alias = models.CharField(max_length=191)
#     is_active = models.BooleanField(default=True)

#     class Meta:
#         constraints = [
#             models.UniqueConstraint(fields=("content_type", "normalized_alias"), name="unique_option_alias_normalized"),
#         ]

#     def save(self, *args, **kwargs):
#         self.normalized_alias = re.sub(r"[^a-z0-9]", "", (self.alias or "").casefold())
#         super().save(*args, **kwargs)

class PatientType(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "Patient Type"
        verbose_name_plural = "Patient Types"

    def __str__(self):
        return self.name    


class District(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "District"
        verbose_name_plural = "Districts"

    def __str__(self):
        return self.name


class Thana(models.Model):
    district = models.ForeignKey(
        District,
        on_delete=models.CASCADE,
        related_name="thanas"
    )
    name = models.CharField(max_length=191)

    class Meta:
        unique_together = ("district", "name")

    def __str__(self):
        return self.name


class Sex(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "Sex"
        verbose_name_plural = "Sex"

    def __str__(self):
        return self.name


class EconomicStatus(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "Economic Status"
        verbose_name_plural = "Economic Statuses"

    def __str__(self):
        return self.name


class BloodGroup(models.Model):
    name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


class MaritalStatus(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "Marital Status"
        verbose_name_plural = "Marital Statuses"

    def __str__(self):
        return self.name


class AlcoholHistory(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "Alcohol History"
        verbose_name_plural = "Alcohol Histories"

    def __str__(self):
        return self.name


class SmokingHistory(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "Smoking History"
        verbose_name_plural = "Smoking Histories"

    def __str__(self):
        return self.name


class TBHistory(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "TB History"
        verbose_name_plural = "TB Histories"

    def __str__(self):
        return self.name


class CovidHistory(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "COVID-19 History"
        verbose_name_plural = "COVID-19 Histories"

    def __str__(self):
        return self.name

class Vaccine(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name

class VaccinationDose(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name

class DiagnosisDiseaseGroup(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name


class DiagnosisDiseaseSubgroup(models.Model):
    disease_group = models.ForeignKey(
        DiagnosisDiseaseGroup,
        on_delete=models.CASCADE,
        related_name="subgroups"
    )
    name = models.CharField(max_length=191)

    class Meta:
        unique_together = ("disease_group", "name")

    def __str__(self):
        return self.name

class DiagnosisPrimarySite(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name

class DiagnosisMetastaticSite(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name

class DiagnosisLaterality(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "Diagnosis Laterality"
        verbose_name_plural = "Diagnosis Lateralities"

    def __str__(self):
        return self.name
    
class Comorbidity(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "Comorbidity"
        verbose_name_plural = "Comorbidities"

    def __str__(self):
        return self.name

class HistopathologyDetails(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "Histopathology Details"
        verbose_name_plural = "Histopathology Details"

    def __str__(self):
        return self.name

class HistopathologyType(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name

class HistopathologySite(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name

class HistopathologyGrade(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name

class IHCCycle(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name

class IHCCycleResult(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name

class IHCStagingCycle(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name

class IHCStagingCycleResult(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name

# TNM Staging Models STart Here

class TNMT(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "TNM T"
        verbose_name_plural = "TNM T"

    def __str__(self):
        return self.name


class TNMN(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "TNM N"
        verbose_name_plural = "TNM N"

    def __str__(self):
        return self.name


class TNMM(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "TNM M"
        verbose_name_plural = "TNM M"

    def __str__(self):
        return self.name


class TNMStage(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "TNM Stage"
        verbose_name_plural = "TNM Stages"

    def __str__(self):
        return self.name



# TNM Staging Models Ends Here

# Moleuclar pathology Models Start Here

class MolecularPathologyMethod(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name

class MolecularPathologySpecimen(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name

class MolecularPathologyGene(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name

class MolecularPathologyExon(models.Model):
    gene = models.ForeignKey(
        MolecularPathologyGene,
        on_delete=models.CASCADE,
        related_name="exons"
    )
    name = models.CharField(max_length=191)

    class Meta:
        unique_together = ("gene", "name")

    def __str__(self):
        return f"{self.gene.name} - {self.name}"

# class MolecularPathologyMutation(models.Model):
#     exon = models.ForeignKey(
#         MolecularPathologyExon,
#         on_delete=models.CASCADE,
#         related_name="mutations"
#     )
#     name = models.CharField(max_length=191)

#     class Meta:
#         unique_together = ("exon", "name")

#     def __str__(self):
#         return f"{self.exon.gene.name} - {self.exon.name} - {self.name}"

# class MolecularPathologyProteinMutation(models.Model):
#     name = models.CharField(max_length=191, unique=True)

#     def __str__(self):
#         return self.name

class MolecularAlterationType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class MolecularPathologyResult(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class MolecularClinicalSignificance(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class MolecularPanel(models.Model):
    name = models.CharField(max_length=191, unique=True)
    manufacturer = models.CharField(max_length=191, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class MolecularPanelVersion(models.Model):
    class ReportingPolicy(models.TextChoices):
        EXPLICIT_ONLY = "explicit_only", "Explicit results only"
        UNREPORTED_NEGATIVE = (
            "unreported_negative",
            "Unreported covered targets are not detected",
        )
        POSITIVES_ONLY = "positives_only", "Positive findings only"

    panel = models.ForeignKey(
        MolecularPanel,
        on_delete=models.PROTECT,
        related_name="versions",
    )
    version = models.CharField(max_length=100)

    method = models.ForeignKey(
        MolecularPathologyMethod,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    reporting_policy = models.CharField(
        max_length=30,
        choices=ReportingPolicy.choices,
        default=ReportingPolicy.EXPLICIT_ONLY,
    )

    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["panel", "version"],
                name="unique_molecular_panel_version",
            )
        ]

    def __str__(self):
        return f"{self.panel} - {self.version}"

class MolecularPanelTarget(models.Model):
    panel_version = models.ForeignKey(
        MolecularPanelVersion,
        on_delete=models.CASCADE,
        related_name="targets",
    )
    gene = models.ForeignKey(
        MolecularPathologyGene,
        on_delete=models.PROTECT,
        related_name="panel_targets",
    )
    alteration_type = models.ForeignKey(
        MolecularAlterationType,
        on_delete=models.PROTECT,
    )

    covered_exons = models.ManyToManyField(
        MolecularPathologyExon,
        blank=True,
        related_name="panel_targets",
    )

    coverage_notes = models.TextField(blank=True)
    is_reportable = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["panel_version", "gene", "alteration_type"],
                name="unique_panel_gene_alteration",
            )
        ]

    def __str__(self):
        return (
            f"{self.panel_version} - "
            f"{self.gene} - {self.alteration_type}"
        )



class CancerMarkerName(models.Model):
    name = models.CharField(max_length=191, unique=True)
    unit = models.CharField(max_length=191, blank=True)

    def __str__(self):
        return self.name


# Treatment Models Start Here

class SurgeryModality(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "Surgery Modality"
        verbose_name_plural = "Surgery Modalities"

    def __str__(self):
        return self.name

class SurgeryLaterality(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name

class RadiotherapySite(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name

class RadiotherapyIntent(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name

class RadiotherapyModality(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "Radiotherapy Modality"
        verbose_name_plural = "Radiotherapy Modalities"

    def __str__(self):
        return self.name

class TreatmentModality(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "Treatment Modality"
        verbose_name_plural = "Treatment Modalities"

    def __str__(self):
        return self.name

class LineOfTreatment(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name

class TreatmentDrug(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name


class TreatmentProtocol(models.Model):
    name = models.CharField(max_length=191, unique=True)
    drugs = models.ManyToManyField(
        TreatmentDrug,
        through="TreatmentProtocolDrug",
        related_name="protocols",
    )

    def __str__(self):
        return self.name


class TreatmentProtocolDrug(models.Model):
    protocol = models.ForeignKey(
        TreatmentProtocol,
        on_delete=models.CASCADE,
        related_name="protocol_drugs",
    )
    drug = models.ForeignKey(
        TreatmentDrug,
        on_delete=models.PROTECT,
        related_name="protocol_drugs",
    )
    sequence = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ("sequence", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["protocol", "drug"],
                name="unique_drug_per_protocol",
            )
        ]
    def __str__(self):
        return f"{self.protocol} - {self.drug}"
    
# Treatment Models Ends Here

#Outcome models starts here

# =========================================================
# RECIST 1.1 LOOKUP MODELS
# =========================================================

class RECISTTargetLesion(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "RECIST 1.1 Target Lesion"
        verbose_name_plural = "RECIST 1.1 Target Lesions"

    def __str__(self):
        return self.name


class RECISTNonTargetLesion(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "RECIST 1.1 Non-Target Lesion"
        verbose_name_plural = "RECIST 1.1 Non-Target Lesions"

    def __str__(self):
        return self.name


class RECISTNewLesion(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "RECIST 1.1 New Lesion"
        verbose_name_plural = "RECIST 1.1 New Lesions"

    def __str__(self):
        return self.name


class RECISTResponseResult(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "RECIST 1.1 Response Result"
        verbose_name_plural = "RECIST 1.1 Response Results"

    def __str__(self):
        return self.name


# =========================================================
# iRECIST LOOKUP MODELS
# =========================================================

class IRECISTTargetLesion(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "iRECIST Target Lesion"
        verbose_name_plural = "iRECIST Target Lesions"

    def __str__(self):
        return self.name


class IRECISTNonTargetLesion(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "iRECIST Non-Target Lesion"
        verbose_name_plural = "iRECIST Non-Target Lesions"

    def __str__(self):
        return self.name


class IRECISTNewLesion(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "iRECIST New Lesion"
        verbose_name_plural = "iRECIST New Lesions"

    def __str__(self):
        return self.name


class IRECISTResponseResult(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "iRECIST Response Result"
        verbose_name_plural = "iRECIST Response Results"

    def __str__(self):
        return self.name


# =========================================================
# COMMON LOOKUPS
# =========================================================

class ProgressionSite(models.Model):
    name = models.CharField(max_length=191, unique=True)

    def __str__(self):
        return self.name


class ResponseEstimationMethod(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "Method of Estimation"
        verbose_name_plural = "Methods of Estimation"

    def __str__(self):
        return self.name


# =========================================================
# RECIST 1.1 ASSESSMENT
# =========================================================

class RECIST11Assessment(models.Model):
    target_lesion = models.ForeignKey(
        RECISTTargetLesion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    non_target_lesion = models.ForeignKey(
        RECISTNonTargetLesion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    new_lesion = models.ForeignKey(
        RECISTNewLesion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    response_result = models.ForeignKey(
        RECISTResponseResult,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "RECIST 1.1 Assessment"
        verbose_name_plural = "RECIST 1.1 Assessments"

    def __str__(self):
        if self.response_result:
            return f"RECIST 1.1 - {self.response_result}"

        return "RECIST 1.1 Assessment"


# =========================================================
# iRECIST ASSESSMENT
# =========================================================

class IRECISTAssessment(models.Model):
    target_lesion = models.ForeignKey(
        IRECISTTargetLesion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    non_target_lesion = models.ForeignKey(
        IRECISTNonTargetLesion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    new_lesion = models.ForeignKey(
        IRECISTNewLesion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    response_result = models.ForeignKey(
        IRECISTResponseResult,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "iRECIST Assessment"
        verbose_name_plural = "iRECIST Assessments"

    def __str__(self):
        if self.response_result:
            return f"iRECIST - {self.response_result}"

        return "iRECIST Assessment"


class PathologicalResponseTargetLesion(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "Pathological Response Target Lesion"
        verbose_name_plural = "Pathological Response Target Lesions"

    def __str__(self):
        return self.name


class PathologicalResponseNonTargetLesion(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "Pathological Response Non-Target Lesion"
        verbose_name_plural = "Pathological Response Non-Target Lesions"

    def __str__(self):
        return self.name


class PathologicalResponseNewLesion(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "Pathological Response New Lesion"
        verbose_name_plural = "Pathological Response New Lesions"

    def __str__(self):
        return self.name


class PathologicalResponseResult(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "Pathological Response Result"
        verbose_name_plural = "Pathological Response Results"

    def __str__(self):
        return self.name


class PathologicalResponseAssessment(models.Model):
    target_lesion = models.ForeignKey(
        PathologicalResponseTargetLesion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    non_target_lesion = models.ForeignKey(
        PathologicalResponseNonTargetLesion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    new_lesion = models.ForeignKey(
        PathologicalResponseNewLesion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    response_result = models.ForeignKey(
        PathologicalResponseResult,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Pathological Response Assessment"
        verbose_name_plural = "Pathological Response Assessments"

    def __str__(self):
        if self.response_result:
            return f"Pathological Response - {self.response_result}"

        return "Pathological Response Assessment"


class DiseaseProgressionStatus(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "Disease Progression Status"
        verbose_name_plural = "Disease Progression Status"

    def __str__(self):
        return self.name

class SurvivalStatus(models.Model):
    name = models.CharField(max_length=191, unique=True)

    class Meta:
        verbose_name = "Survival Status"
        verbose_name_plural = "Survival Status"

    def __str__(self):
        return self.name
# Outcome models ends here
