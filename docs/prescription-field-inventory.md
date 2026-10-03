# Actual prescription form field inventory

Contract: `prescription-fields-1`. Generated from the shared JSON and Django model metadata.

Model existence is a destination check, not proof of persistence coverage; service tests verify actual writes.

| Section | Field | Type | Option resource | Required | Destination |
|---|---|---|---|---|---|
| patient | patient_id | text | — | no | Patient.patient_id |
| patient | name | text | — | no | Patient.name |
| patient | registration_no | text | — | no | Patient.registration_no |
| patient | phone | text | — | no | Patient.phone |
| patient | email | email | — | no | Patient.email |
| patient | nid | text | — | no | Patient.nid |
| patient | passport | text | — | no | Patient.passport |
| patient | date_of_birth | date | — | no | Patient.date_of_birth |
| patient | age | number | — | no | Patient.age |
| patient | sex | option | sexes | no | Patient.sex |
| patient | district | option | districts | no | Patient.district |
| patient | thana | option | thanas | no | Patient.thana |
| patient | blood_group | option | blood-groups | no | Patient.blood_group |
| patient | economic_status | option | economic-statuses | no | Patient.economic_status |
| patient | type_of_patient | option | patient-types | no | Patient.type_of_patient |
| patient | area | text | — | no | Patient.area |
| observation | observed_at | datetime-local | — | no | ClinicalObservation.observed_at |
| observation | prescription_date | date | — | no | ClinicalObservation.prescription_date |
| anthropometry | height_cm | number | — | no | PatientAnthropometry.height_cm |
| anthropometry | weight_kg | number | — | no | PatientAnthropometry.weight_kg |
| anthropometry | bmi | derived | — | no | PatientAnthropometry.bmi (derived/read-only) |
| anthropometry | bsa | derived | — | no | PatientAnthropometry.bsa (derived/read-only) |
| comorbidities | comorbidity | option | comorbidities | yes | PatientComorbidity.comorbidity |
| comorbidities | diagnosed_on | date | — | no | PatientComorbidity.diagnosed_on |
| comorbidities | is_active | boolean | — | no | PatientComorbidity.is_active |
| comorbidities | notes | textarea | — | no | PatientComorbidity.notes |
| diagnoses | diagnosed_on | date | — | no | Diagnosis.diagnosed_on |
| diagnoses | disease_group | option | diagnosis-disease-groups | no | Diagnosis.disease_group |
| diagnoses | disease_subgroup | option | diagnosis-disease-subgroups | no | Diagnosis.disease_subgroup |
| diagnoses | primary_site | option | diagnosis-primary-sites | no | Diagnosis.primary_site |
| diagnoses | laterality | option | diagnosis-lateralities | no | Diagnosis.laterality |
| diagnoses | metastatic_sites | option | diagnosis-metastatic-sites | no | MetastaticSiteRecord.site (multiple) |
| diagnoses | diagnosis_in_details | textarea | — | no | Diagnosis.diagnosis_in_details |
| histopathologies | biopsy_date | date | — | no | Histopathology.biopsy_date |
| histopathologies | report_date | date | — | no | Histopathology.report_date |
| histopathologies | histopathology_details | option | histopathology-details | no | Histopathology.histopathology_details |
| histopathologies | histopathology_type | option | histopathology-types | no | Histopathology.histopathology_type |
| histopathologies | histopathology_site | option | histopathology-sites | no | Histopathology.histopathology_site |
| histopathologies | histopathology_grade | option | histopathology-grades | no | Histopathology.histopathology_grade |
| histopathologies | report_summary | textarea | — | no | Histopathology.report_summary |
| histopathologies | any_known_mutation | textarea | — | no | NO DIRECT DESTINATION — retain evidence and require disposition |
| ihc_results | tested_at | date | — | no | IHCResult.tested_at |
| ihc_results | marker | option | ihc-cycles | yes | IHCResult.marker |
| ihc_results | result | option | ihc-cycle-results | yes | IHCResult.result |
| ihc_results | percentage | number | — | no | IHCResult.percentage |
| ihc_results | notes | textarea | — | no | IHCResult.notes |
| pathological_staging_results | assessed_at | date | — | no | PathologicalStagingResult.assessed_at |
| pathological_staging_results | feature | option | ihc-staging-cycles | yes | PathologicalStagingResult.feature |
| pathological_staging_results | result | option | ihc-staging-cycle-results | yes | PathologicalStagingResult.result |
| pathological_staging_results | percentage | number | — | no | PathologicalStagingResult.percentage |
| pathological_staging_results | notes | textarea | — | no | PathologicalStagingResult.notes |
| clinical_tnm_stagings | t | option | tnm-t | no | ClinicalTNMStaging.t |
| clinical_tnm_stagings | n | option | tnm-n | no | ClinicalTNMStaging.n |
| clinical_tnm_stagings | m | option | tnm-m | no | ClinicalTNMStaging.m |
| clinical_tnm_stagings | stage | option | tnm-stages | no | ClinicalTNMStaging.stage |
| clinical_tnm_stagings | staged_on | date | — | no | ClinicalTNMStaging.staged_on |
| clinical_tnm_stagings | notes | textarea | — | no | ClinicalTNMStaging.notes |
| pathological_tnm_stagings | t | option | tnm-t | no | PathologicalTNMStaging.t |
| pathological_tnm_stagings | n | option | tnm-n | no | PathologicalTNMStaging.n |
| pathological_tnm_stagings | m | option | tnm-m | no | PathologicalTNMStaging.m |
| pathological_tnm_stagings | stage | option | tnm-stages | no | PathologicalTNMStaging.stage |
| pathological_tnm_stagings | staged_on | date | — | no | PathologicalTNMStaging.staged_on |
| pathological_tnm_stagings | notes | textarea | — | no | PathologicalTNMStaging.notes |
| molecular_tests | panel | option | molecular-panels | no | Scope for MolecularTest.panel_version |
| molecular_tests | panel_version | option | molecular-panel-versions | no | MolecularTest.panel_version |
| molecular_tests | method | option | molecular-methods | no | MolecularTest.method |
| molecular_tests | specimen | option | molecular-specimens | no | MolecularTest.specimen |
| molecular_tests | specimen_collected_on | date | — | no | MolecularTest.specimen_collected_on |
| molecular_tests | tested_on | date | — | no | MolecularTest.tested_on |
| molecular_tests | reported_on | date | — | no | MolecularTest.reported_on |
| molecular_tests | qc_status | status | — | no | MolecularTest.qc_status |
| molecular_tests | laboratory | text | — | no | MolecularTest.laboratory |
| molecular_tests | accession_number | text | — | no | MolecularTest.accession_number |
| molecular_tests | notes | textarea | — | no | MolecularTest.notes, MolecularTestResult.notes |
| molecular_tests | panel_target | option | molecular-panel-targets | no | MolecularTestResult.panel_target |
| molecular_tests | gene | option | molecular-genes | yes | MolecularTestResult.gene |
| molecular_tests | exon | option | molecular-exons | no | MolecularTestResult.exon |
| molecular_tests | alteration_type | option | molecular-alteration-types | yes | MolecularTestResult.alteration_type |
| molecular_tests | result | option | molecular-results | yes | MolecularTestResult.result |
| molecular_tests | partner_gene | option | molecular-genes | no | MolecularTestResult.partner_gene |
| molecular_tests | clinical_significance | option | molecular-clinical-significances | no | MolecularTestResult.clinical_significance |
| molecular_tests | dna_change | text | — | no | MolecularTestResult.dna_change |
| molecular_tests | protein_change | text | — | no | MolecularTestResult.protein_change |
| molecular_tests | common_name | text | — | no | MolecularTestResult.common_name |
| molecular_tests | variant_allele_frequency | number | — | no | MolecularTestResult.variant_allele_frequency |
| molecular_tests | copy_number | number | — | no | MolecularTestResult.copy_number |
| molecular_tests | origin | status | — | no | MolecularTestResult.origin |
| molecular_tests | result_notes | textarea | — | no | NO DIRECT DESTINATION — retain evidence and require disposition |
| cancer_markers | marker | option | cancer-marker-names | yes | CancerMarkerResult.marker |
| cancer_markers | value | number | — | no | CancerMarkerResult.value |
| cancer_markers | unit | derived | — | no | NO DIRECT DESTINATION — retain evidence and require disposition (derived/read-only) |
| cancer_markers | tested_on | date | — | no | CancerMarkerResult.tested_on |
| cancer_markers | notes | textarea | — | no | CancerMarkerResult.notes |
| treatments | modality | option | treatment-modalities | yes | TreatmentCourse.modality |
| treatments | line_of_treatment | option | lines-of-treatment | no | TreatmentCourse.line_of_treatment |
| treatments | protocol | option | treatment-protocols | yes | TreatmentCourse.protocol |
| treatments | started_on | date | — | no | TreatmentCourse.started_on |
| treatments | ended_on | date | — | no | TreatmentCourse.ended_on |
| treatments | status | status | — | no | TreatmentCourse.status, TreatmentAdministration.status |
| treatments | reason_for_stopping | textarea | — | no | TreatmentCourse.reason_for_stopping |
| treatments | notes | textarea | — | no | TreatmentCourse.notes, TreatmentAdministration.notes |
| treatments | drug | option | treatment-drugs | yes | TreatmentAdministration.drug |
| treatments | administered_on | date | — | no | TreatmentAdministration.administered_on |
| treatments | cycle_number | number | — | no | TreatmentAdministration.cycle_number |
| treatments | day_number | number | — | no | TreatmentAdministration.day_number |
| treatments | dose | number | — | no | TreatmentAdministration.dose |
| treatments | dose_unit | text | — | no | TreatmentAdministration.dose_unit |
| treatments | administration_status | status | — | no | TreatmentAdministration.status |
| treatments | administration_notes | textarea | — | no | TreatmentAdministration.notes |
| surgeries | modality | option | surgery-modalities | yes | SurgeryRecord.modality |
| surgeries | laterality | option | surgery-lateralities | no | SurgeryRecord.laterality |
| surgeries | surgery_date | date | — | no | SurgeryRecord.surgery_date |
| surgeries | status | status | — | no | SurgeryRecord.status |
| surgeries | procedure_details | textarea | — | no | SurgeryRecord.procedure_details |
| surgeries | operative_findings | textarea | — | no | SurgeryRecord.operative_findings |
| surgeries | complications | textarea | — | no | SurgeryRecord.complications |
| surgeries | notes | textarea | — | no | SurgeryRecord.notes |
| radiotherapies | site | option | radiotherapy-sites | yes | RadiotherapyCourse.site |
| radiotherapies | intent | option | radiotherapy-intents | yes | RadiotherapyCourse.intent |
| radiotherapies | modality | option | radiotherapy-modalities | yes | RadiotherapyCourse.modality |
| radiotherapies | started_on | date | — | no | RadiotherapyCourse.started_on |
| radiotherapies | ended_on | date | — | no | RadiotherapyCourse.ended_on |
| radiotherapies | dose_per_fraction_cgy | number | — | no | RadiotherapyCourse.dose_per_fraction_cgy |
| radiotherapies | planned_fractions | number | — | no | RadiotherapyCourse.planned_fractions |
| radiotherapies | completed_fractions | number | — | no | RadiotherapyCourse.completed_fractions |
| radiotherapies | planned_total_dose_cgy | derived | — | no | RadiotherapyCourse.planned_total_dose_cgy (derived/read-only) |
| radiotherapies | delivered_total_dose_cgy | derived | — | no | RadiotherapyCourse.delivered_total_dose_cgy (derived/read-only) |
| radiotherapies | status | status | — | no | RadiotherapyCourse.status |
| radiotherapies | reason_for_stopping | textarea | — | no | RadiotherapyCourse.reason_for_stopping |
| radiotherapies | notes | textarea | — | no | RadiotherapyCourse.notes |
| recist_assessments | assessed_on | date | — | yes | RECIST11Assessment.assessed_on |
| recist_assessments | timepoint | status | — | no | RECIST11Assessment.timepoint |
| recist_assessments | target_lesion | option | recist-target-lesions | no | RECIST11Assessment.target_lesion |
| recist_assessments | non_target_lesion | option | recist-non-target-lesions | no | RECIST11Assessment.non_target_lesion |
| recist_assessments | new_lesion | option | recist-new-lesions | no | RECIST11Assessment.new_lesion |
| recist_assessments | overall_response | option | recist-response-results | yes | RECIST11Assessment.overall_response |
| recist_assessments | estimation_method | option | response-estimation-methods | no | RECIST11Assessment.estimation_method |
| recist_assessments | notes | textarea | — | no | RECIST11Assessment.notes |
| irecist_assessments | assessed_on | date | — | yes | IRECISTAssessment.assessed_on |
| irecist_assessments | timepoint | status | — | no | IRECISTAssessment.timepoint |
| irecist_assessments | target_lesion | option | irecist-target-lesions | no | IRECISTAssessment.target_lesion |
| irecist_assessments | non_target_lesion | option | irecist-non-target-lesions | no | IRECISTAssessment.non_target_lesion |
| irecist_assessments | new_lesion | option | irecist-new-lesions | no | IRECISTAssessment.new_lesion |
| irecist_assessments | overall_response | option | irecist-response-results | yes | IRECISTAssessment.overall_response |
| irecist_assessments | estimation_method | option | response-estimation-methods | no | IRECISTAssessment.estimation_method |
| irecist_assessments | notes | textarea | — | no | IRECISTAssessment.notes |
| pathological_responses | assessed_on | date | — | yes | PathologicalResponseAssessment.assessed_on |
| pathological_responses | timepoint | status | — | no | PathologicalResponseAssessment.timepoint |
| pathological_responses | response_category | option | pathological-response-categories | no | PathologicalResponseAssessment.response_category |
| pathological_responses | residual_viable_tumor_percentage | number | — | no | PathologicalResponseAssessment.residual_viable_tumor_percentage |
| pathological_responses | tumor_regression_grade | option | tumor-regression-grades | no | PathologicalResponseAssessment.tumor_regression_grade |
| pathological_responses | estimation_method | option | response-estimation-methods | no | PathologicalResponseAssessment.estimation_method |
| pathological_responses | notes | textarea | — | no | PathologicalResponseAssessment.notes |
| progression_records | status | option | disease-progression-statuses | yes | DiseaseProgressionRecord.status |
| progression_records | assessed_on | date | — | yes | DiseaseProgressionRecord.assessed_on |
| progression_records | progression_date | date | — | no | DiseaseProgressionRecord.progression_date |
| progression_records | progression_sites | option | progression-sites | no | DiseaseProgressionRecord.progression_sites |
| progression_records | estimation_method | option | response-estimation-methods | no | DiseaseProgressionRecord.estimation_method |
| progression_records | notes | textarea | — | no | DiseaseProgressionRecord.notes |
| survival_records | status | option | survival-statuses | yes | SurvivalFollowUp.status |
| survival_records | followed_up_on | date | — | yes | SurvivalFollowUp.followed_up_on |
| survival_records | death_date | date | — | no | SurvivalFollowUp.death_date |
| survival_records | cause_of_death | text | — | no | SurvivalFollowUp.cause_of_death |
| survival_records | notes | textarea | — | no | SurvivalFollowUp.notes |

Total exposed definitions: 164. Clinical collections: 17.

Known gap: histopathology.any_known_mutation has no Histopathology destination. Do not silently write it to a patient-wide field. Canonical extraction must retain it as an exception until explicitly placed or excluded.
