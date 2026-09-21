from django.db import migrations, models


def normalize_status_codes(apps, schema_editor):
    progression_model = apps.get_model("options", "DiseaseProgressionStatus")
    survival_model = apps.get_model("options", "SurvivalStatus")

    mappings = (
        (progression_model, {
            "no progression": "no_progression",
            "no_progression": "no_progression",
            "progressed": "progressed",
            "progression": "progressed",
            "unknown": "unknown",
        }),
        (survival_model, {
            "alive": "alive",
            "dead": "dead",
            "deceased": "dead",
            "lost to follow up": "lost_to_follow_up",
            "lost_to_follow_up": "lost_to_follow_up",
        }),
    )

    for model, code_map in mappings:
        for record in model.objects.all().order_by("pk"):
            code = code_map.get(record.name.strip().casefold(), f"legacy_{record.pk}")
            if model.objects.exclude(pk=record.pk).filter(code=code).exists():
                code = f"legacy_{record.pk}"
            record.code = code
            record.save(update_fields=["code"])


class Migration(migrations.Migration):
    dependencies = [("options", "0006_diseaseprogressionstatus_code_survivalstatus_code")]

    operations = [
        migrations.RunPython(normalize_status_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="diseaseprogressionstatus",
            name="code",
            field=models.CharField(max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name="survivalstatus",
            name="code",
            field=models.CharField(max_length=50, unique=True),
        ),
    ]
