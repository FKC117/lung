from django.contrib import admin

from .models import ExtractionIssue, ExtractionRun, LLMInvocation, PrescriptionDocument, PrescriptionDrugAlias, PrescriptionPage, PrescriptionReview, PrescriptionReviewChange

admin.site.register((PrescriptionPage, ExtractionRun, ExtractionIssue, PrescriptionDrugAlias, PrescriptionReview, PrescriptionReviewChange))


@admin.register(PrescriptionDocument)
class PrescriptionDocumentAdmin(admin.ModelAdmin):
    """Delete a prescription as one authorized unit, including its audit chain."""

    list_display = ("id", "original_filename", "status", "patient", "uploaded_by", "created_at")
    list_filter = ("status",)
    search_fields = ("=id", "original_filename", "sha256", "patient__patient_id", "patient__registration_no")
    list_select_related = ("patient", "uploaded_by")
    ordering = ("-created_at",)

    def get_deleted_objects(self, objs, request):
        deleted_objects, model_count, perms_needed, protected = super().get_deleted_objects(objs, request)
        # A user authorised to delete the document is authorised to remove its
        # dependent OCR, extraction, review, and LLM audit rows. Direct LLM
        # audit deletion remains disabled in LLMInvocationAdmin.
        if self.has_delete_permission(request):
            perms_needed.clear()
        return deleted_objects, model_count, perms_needed, protected


@admin.register(LLMInvocation)
class LLMInvocationAdmin(admin.ModelAdmin):
    """Immutable audit trail for direct and batch Gemini requests."""

    list_display = (
        "id", "document", "request_kind", "provider", "model_name", "status",
        "input_tokens", "output_tokens", "total_tokens", "requested_at", "completed_at",
    )
    list_filter = ("status", "provider", "request_kind", "model_name")
    search_fields = ("=id", "=document__id", "document__original_filename", "provider_request_id", "input_sha256", "output_sha256")
    readonly_fields = (
        "document", "extraction_run", "batch_item", "provider", "request_kind", "model_name", "prompt_version",
        "system_instruction", "input_text", "input_sha256", "input_characters", "input_tokens",
        "output_text", "output_sha256", "output_characters", "output_tokens", "total_tokens",
        "usage_metadata", "provider_request_id", "status", "error", "requested_at", "completed_at",
    )
    fields = readonly_fields
    date_hierarchy = "requested_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("prescriptions.view_llminvocation")

    def has_delete_permission(self, request, obj=None):
        return False
