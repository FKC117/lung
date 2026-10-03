from pathlib import Path

from django.core.management.base import BaseCommand
from records import models
from prescriptions.services.field_contract import contract


MODELS = {
    "patient": [models.Patient], "observation": [models.ClinicalObservation], "anthropometry": [models.PatientAnthropometry],
    "comorbidities": [models.PatientComorbidity], "diagnoses": [models.Diagnosis, models.MetastaticSiteRecord],
    "histopathologies": [models.Histopathology], "ihc_results": [models.IHCResult],
    "pathological_staging_results": [models.PathologicalStagingResult], "clinical_tnm_stagings": [models.ClinicalTNMStaging],
    "pathological_tnm_stagings": [models.PathologicalTNMStaging], "molecular_tests": [models.MolecularTest, models.MolecularTestResult],
    "cancer_markers": [models.CancerMarkerResult], "treatments": [models.TreatmentCourse, models.TreatmentAdministration],
    "surgeries": [models.SurgeryRecord], "radiotherapies": [models.RadiotherapyCourse], "recist_assessments": [models.RECIST11Assessment],
    "irecist_assessments": [models.IRECISTAssessment], "pathological_responses": [models.PathologicalResponseAssessment],
    "progression_records": [models.DiseaseProgressionRecord], "survival_records": [models.SurvivalFollowUp],
}
SPECIAL = {("diagnoses", "metastatic_sites"): "MetastaticSiteRecord.site (multiple)", ("treatments", "administration_status"): "TreatmentAdministration.status", ("treatments", "administration_notes"): "TreatmentAdministration.notes", ("molecular_tests", "panel"): "Scope for MolecularTest.panel_version", ("treatments", "protocol_drug"): "Validated protocol/drug membership (scope)", ("molecular_tests", "status"): "MolecularTest finalization service", ("molecular_tests", "qc_status"): "MolecularTest.qc_status"}


class Command(BaseCommand):
    help = "Inventory actual form definitions against Django destinations, without database writes."

    def add_arguments(self, parser):
        parser.add_argument("--output")

    def handle(self, **options):
        sections = {key: contract()[key] for key in ("patient", "observation", "anthropometry")}
        sections.update(contract()["collections"])
        lines = ["# Actual prescription form field inventory", "", f"Contract: `{contract()['version']}`. Generated from the shared JSON and Django model metadata.", "", "Model existence is a destination check, not proof of persistence coverage; service tests verify actual writes.", "", "| Section | Field | Type | Option resource | Required | Destination |", "|---|---|---|---|---|---|"]
        count = 0
        for section, definition in sections.items():
            for field in definition["fields"]:
                count += 1
                key = field["key"]
                destination = SPECIAL.get((section, key))
                if not destination:
                    candidates = [f"{model.__name__}.{key}" for model in MODELS[section] if key in {f.name for f in model._meta.get_fields()}]
                    destination = ", ".join(candidates) or "NO DIRECT DESTINATION — retain evidence and require disposition"
                if field.get("readOnly"):
                    destination += " (derived/read-only)"
                lines.append(f"| {section} | {key} | {field.get('type', 'option' if field.get('resource') else 'text')} | {field.get('resource', '—')} | {'yes' if field.get('required') else 'no'} | {destination} |")
        lines += ["", f"Total exposed definitions: {count}. Clinical collections: {len(contract()['collections'])}.", "", "Known gap: histopathology.any_known_mutation has no Histopathology destination. Do not silently write it to a patient-wide field. Canonical extraction must retain it as an exception until explicitly placed or excluded."]
        output = "\n".join(lines) + "\n"
        if options["output"]:
            Path(options["output"]).write_text(output, encoding="utf-8")
            self.stdout.write(f"Wrote {count} field definitions to {options['output']}.")
        else:
            self.stdout.write(output)
