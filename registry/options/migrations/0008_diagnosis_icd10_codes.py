from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("options", "0007_normalize_outcome_status_codes")]

    operations = [
        migrations.AddField(
            model_name="diagnosisdiseasegroup",
            name="icd10_code",
            field=models.CharField(blank=True, db_index=True, max_length=16, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="diagnosisdiseasesubgroup",
            name="icd10_code",
            field=models.CharField(blank=True, db_index=True, max_length=16, null=True),
        ),
    ]
