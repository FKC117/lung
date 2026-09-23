from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("prescriptions", "0004_prescriptionreview_published_at_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PrescriptionBatchJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("display_name", models.CharField(max_length=160)),
                ("provider", models.CharField(default="gemini", max_length=32)),
                ("provider_job_name", models.CharField(blank=True, db_index=True, max_length=255)),
                ("model_name", models.CharField(max_length=128)),
                ("schema_version", models.CharField(default="2.0", max_length=32)),
                ("prompt_version", models.CharField(max_length=64)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("submitted", "Submitted"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed"), ("cancelled", "Cancelled")], db_index=True, default="draft", max_length=16)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("submitted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="submitted_prescription_batches", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="PrescriptionBatchItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("request_key", models.CharField(max_length=128)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("completed", "Completed"), ("failed", "Failed")], db_index=True, default="queued", max_length=16)),
                ("input_sha256", models.CharField(max_length=64)),
                ("raw_response", models.TextField(blank=True)),
                ("error", models.TextField(blank=True)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("batch_job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="prescriptions.prescriptionbatchjob")),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="batch_items", to="prescriptions.prescriptiondocument")),
            ],
            options={"ordering": ("id",)},
        ),
        migrations.AddConstraint(model_name="prescriptionbatchitem", constraint=models.UniqueConstraint(fields=("batch_job", "document"), name="unique_prescription_batch_document")),
        migrations.AddConstraint(model_name="prescriptionbatchitem", constraint=models.UniqueConstraint(fields=("batch_job", "request_key"), name="unique_prescription_batch_request_key")),
    ]
