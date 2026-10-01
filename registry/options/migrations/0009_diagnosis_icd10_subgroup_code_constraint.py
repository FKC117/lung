import re

from django.db import migrations


def canonical_icd10_code(value):
    raw = str(value or "").split("-", 1)[0].strip().upper().replace(" ", "")
    compact = re.sub(r"[^A-Z0-9]", "", raw)
    match = re.fullmatch(r"([A-Z])(\d{2})(\d{0,2})", compact)
    if not match:
        return None
    letter, category, suffix = match.groups()
    return f"{letter}{category}.{suffix}" if suffix else f"{letter}{category}"


def backfill_icd10_codes(apps, schema_editor):
    group_model = apps.get_model("options", "DiagnosisDiseaseGroup")
    subgroup_model = apps.get_model("options", "DiagnosisDiseaseSubgroup")

    for group in group_model.objects.all().order_by("pk"):
        group.icd10_code = canonical_icd10_code(group.name)
        group.save(update_fields=["icd10_code"])

    for subgroup in subgroup_model.objects.all().order_by("pk"):
        subgroup.icd10_code = canonical_icd10_code(subgroup.name)
        subgroup.save(update_fields=["icd10_code"])

    malignant_lung = group_model.objects.filter(icd10_code="C34").first()
    if not malignant_lung:
        return
    for subgroup in subgroup_model.objects.select_related("disease_group").filter(icd10_code__startswith="C34."):
        duplicate = subgroup_model.objects.filter(
            disease_group=malignant_lung,
            icd10_code=subgroup.icd10_code,
        ).exclude(pk=subgroup.pk).exists()
        if duplicate:
            # Preserve an already-referenced legacy row without letting it
            # compete with the correct C34 catalog option.
            subgroup.icd10_code = None
        else:
            subgroup.disease_group = malignant_lung
        subgroup.save(update_fields=["icd10_code", "disease_group"])


class Migration(migrations.Migration):
    dependencies = [("options", "0008_diagnosis_icd10_codes")]

    operations = [migrations.RunPython(backfill_icd10_codes, migrations.RunPython.noop)]
