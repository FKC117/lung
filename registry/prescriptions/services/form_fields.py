"""Map explicitly labelled prescription text to the real intake-form field paths."""
import re

ALIASES = {
 "name":"patient.name","sex":"patient.sex","dob":"patient.date_of_birth","date of birth":"patient.date_of_birth","age":"patient.age","email":"patient.email","nid":"patient.nid","passport":"patient.passport","address":"patient.area","blood group":"patient.blood_group",
 "date of diagnosis":"diagnosis.diagnosed_on","diagnosis date":"diagnosis.diagnosed_on","primary site":"diagnosis.primary_site","laterality":"diagnosis.laterality","metastatic site":"diagnosis.metastatic_sites",
 "biopsy date":"histopathology.biopsy_date","report date":"histopathology.report_date","histology":"histopathology.histopathology_type","pathology site":"histopathology.histopathology_site",
 "method":"molecular.method","specimen":"molecular.specimen","laboratory":"molecular.laboratory","accession number":"molecular.accession_number","dna change":"molecular.findings.dna_change","protein change":"molecular.findings.protein_change","vaf":"molecular.findings.variant_allele_frequency","copy number":"molecular.findings.copy_number",
 "treatment start":"treatment.started_at","treatment end":"treatment.ended_at","cycle":"treatment.administrations.cycle_number","day":"treatment.administrations.day_number","dose":"treatment.administrations.dose","dose unit":"treatment.administrations.dose_unit",
 "assessed on":"response.assessed_at","progression date":"progression.progression_date","followed up on":"survival.followed_up_on","death date":"survival.death_date","cause of death":"survival.cause_of_death",
 "surgery date":"surgery.surgery_date","procedure details":"surgery.procedure_details","operative findings":"surgery.operative_findings","complications":"surgery.complications",
 "radiotherapy start":"radiotherapy.started_at","radiotherapy end":"radiotherapy.ended_at","fraction dose":"radiotherapy.fraction_dose","fraction count":"radiotherapy.fraction_count","total dose":"radiotherapy.total_dose","completed fractions":"radiotherapy.completed_fractions",
}
LINE = re.compile(r"^\s*(?P<label>[A-Za-z][A-Za-z /-]{1,60})\s*[:=]\s*(?P<value>.+?)\s*$")

def extract_form_fields(pages):
    candidates = []
    for page in pages:
        for line in (page.cleaned_text or page.raw_text).splitlines():
            match = LINE.match(line)
            if not match: continue
            label = re.sub(r"\s+", " ", match.group("label").casefold()).strip()
            path = ALIASES.get(label)
            if path:
                candidates.append({"field_path": path, "value": match.group("value").strip(), "source_text": line.strip(), "page": page.page_number, "confidence": 0.94})
    return candidates
