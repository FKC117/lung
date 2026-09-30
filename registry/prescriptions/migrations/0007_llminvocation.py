# Generated manually for immutable Gemini request/response auditing.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("prescriptions", "0006_prescriptionpublicationobservation"),
    ]

    operations = [
        migrations.CreateModel(
            name="LLMInvocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(default="gemini", max_length=32)),
                ("request_kind", models.CharField(default="generate_content", max_length=32)),
                ("model_name", models.CharField(blank=True, max_length=128)),
                ("prompt_version", models.CharField(blank=True, max_length=64)),
                ("system_instruction", models.TextField(blank=True)),
                ("input_text", models.TextField(blank=True)),
                ("input_sha256", models.CharField(blank=True, db_index=True, max_length=64)),
                ("input_characters", models.PositiveIntegerField(default=0)),
                ("input_tokens", models.PositiveIntegerField(blank=True, null=True)),
                ("output_text", models.TextField(blank=True)),
                ("output_sha256", models.CharField(blank=True, db_index=True, max_length=64)),
                ("output_characters", models.PositiveIntegerField(default=0)),
                ("output_tokens", models.PositiveIntegerField(blank=True, null=True)),
                ("total_tokens", models.PositiveIntegerField(blank=True, null=True)),
                ("usage_metadata", models.JSONField(blank=True, default=dict)),
                ("provider_request_id", models.CharField(blank=True, db_index=True, max_length=255)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("running", "Running"), ("succeeded", "Succeeded"), ("failed", "Failed"), ("skipped", "Skipped")], db_index=True, default="queued", max_length=16)),
                ("error", models.TextField(blank=True)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("batch_item", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="llm_invocations", to="prescriptions.prescriptionbatchitem")),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="llm_invocations", to="prescriptions.prescriptiondocument")),
                ("extraction_run", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="llm_invocations", to="prescriptions.extractionrun")),
            ],
            options={"ordering": ("-requested_at", "-id")},
        ),
    ]
