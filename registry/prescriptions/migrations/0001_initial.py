# Generated manually because the local runtime lacks django-environ.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("records", "0008_diseaseprogressionrecord_survivalfollowup"),
    ]

    operations = [
        migrations.CreateModel(
            name="PrescriptionDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="prescriptions/%Y/%m/%d")),
                ("original_filename", models.CharField(max_length=255)),
                ("sha256", models.CharField(editable=False, max_length=64, unique=True)),
                ("page_count", models.PositiveIntegerField(default=0)),
                ("status", models.CharField(choices=[("uploaded", "Uploaded"), ("processing", "Processing"), ("ready_for_review", "Ready for review"), ("failed", "Failed")], db_index=True, default="uploaded", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("processing_started_at", models.DateTimeField(blank=True, null=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("patient", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="prescription_documents", to="records.patient")),
                ("uploaded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="ExtractionRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("schema_version", models.CharField(default="1.0", max_length=32)),
                ("prompt_version", models.CharField(default="unconfigured", max_length=64)),
                ("ai_model", models.CharField(blank=True, max_length=128)),
                ("raw_response", models.TextField(blank=True)),
                ("structured_data", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("completed", "Completed"), ("failed", "Failed")], default="pending", max_length=16)),
                ("error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="extraction_runs", to="prescriptions.prescriptiondocument")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="PrescriptionPage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("page_number", models.PositiveIntegerField()),
                ("raw_text", models.TextField(blank=True)),
                ("cleaned_text", models.TextField(blank=True)),
                ("ocr_confidence", models.FloatField(blank=True, null=True)),
                ("image", models.ImageField(blank=True, null=True, upload_to="prescription_pages/%Y/%m/%d")),
                ("ocr_metadata", models.JSONField(blank=True, default=dict)),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pages", to="prescriptions.prescriptiondocument")),
            ],
            options={"ordering": ("page_number",)},
        ),
        migrations.CreateModel(
            name="ExtractionIssue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=64)),
                ("severity", models.CharField(choices=[("info", "Info"), ("warning", "Warning"), ("error", "Error")], default="warning", max_length=16)),
                ("message", models.TextField()),
                ("page_number", models.PositiveIntegerField(blank=True, null=True)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="issues", to="prescriptions.prescriptiondocument")),
                ("extraction_run", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="issues", to="prescriptions.extractionrun")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddConstraint(
            model_name="prescriptionpage",
            constraint=models.UniqueConstraint(fields=("document", "page_number"), name="unique_prescription_document_page"),
        ),
    ]
