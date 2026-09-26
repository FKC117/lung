from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("prescriptions", "0005_prescriptionbatchjob_prescriptionbatchitem"), ("records", "0008_diseaseprogressionrecord_survivalfollowup")]

    operations = [
        migrations.CreateModel(
            name="PrescriptionPublicationObservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("draft_observation_temp_id", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("observation", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="prescription_publication_mapping", to="records.clinicalobservation")),
                ("review", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="publication_observations", to="prescriptions.prescriptionreview")),
            ],
            options={"constraints": [models.UniqueConstraint(fields=("review", "draft_observation_temp_id"), name="unique_review_draft_observation")]},
        ),
    ]
