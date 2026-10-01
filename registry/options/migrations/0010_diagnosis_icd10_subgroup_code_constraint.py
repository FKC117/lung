from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("options", "0009_diagnosis_icd10_subgroup_code_constraint")]

    operations = [
        migrations.AlterUniqueTogether(
            name="diagnosisdiseasesubgroup",
            unique_together={("disease_group", "name"), ("disease_group", "icd10_code")},
        ),
    ]
