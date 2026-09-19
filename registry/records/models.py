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
    TNMStagingClinical as ClinicalTNMStagingOption,
    TNMStagingPathological as PathologicalTNMStagingOption,

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

