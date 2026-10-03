from django.contrib import admin

from .models import ExtractionIssue, ExtractionRun, LLMInvocation, PrescriptionDocument, PrescriptionDrugAlias, PrescriptionPage, PrescriptionReview, PrescriptionReviewChange

admin.site.register((PrescriptionPage, ExtractionRun, ExtractionIssue, PrescriptionReview, PrescriptionReviewChange))


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


from .models import PrescriptionWorkflowRun, PrescriptionWorkflowCheckpoint, PrescriptionWorkflowWrite
from .models import PrescriptionProviderBudget


class ReadOnlyWorkflowAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PrescriptionProviderBudget)
class PrescriptionProviderBudgetAdmin(ReadOnlyWorkflowAdmin):
    list_display = ("scope_key", "model_name", "window_started_at", "requests_reserved", "token_units_reserved", "updated_at")
    search_fields = ("scope_key", "model_name")


@admin.register(PrescriptionWorkflowRun)
class PrescriptionWorkflowRunAdmin(ReadOnlyWorkflowAdmin):
    list_display = ("id", "document", "status", "lease_expires_at", "created_at")
    list_filter = ("status",)
    search_fields = ("=id", "=document__id", "document_sha256")


@admin.register(PrescriptionWorkflowCheckpoint)
class PrescriptionWorkflowCheckpointAdmin(ReadOnlyWorkflowAdmin):
    list_display = ("run", "namespace", "checkpoint_id", "created_at")
    search_fields = ("=run__id", "checkpoint_id")
    exclude = ("payload", "metadata")

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields if field.name not in self.exclude)


@admin.register(PrescriptionWorkflowWrite)
class PrescriptionWorkflowWriteAdmin(ReadOnlyWorkflowAdmin):
    list_display = ("run", "checkpoint_id", "task_id", "channel", "write_index")
    search_fields = ("=run__id", "task_id", "channel")
    exclude = ("payload",)

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields if field.name not in self.exclude)


@admin.register(PrescriptionDrugAlias)
class PrescriptionDrugAliasAdmin(admin.ModelAdmin):
    list_display = ("alias", "drug", "approved_by", "approved_at")
    search_fields = ("alias", "drug__name")
    list_select_related = ("drug", "approved_by")
    readonly_fields = ("approved_by", "approved_at")
    actions = ("approve_aliases",)

    def save_model(self, request, obj, form, change):
        # New/changed proposals require a separate explicit approval action.
        obj.approved_by = None
        super().save_model(request, obj, form, change)

    @admin.action(description="Approve selected drug aliases for automatic matching", permissions=["change"])
    def approve_aliases(self, request, queryset):
        from django.core.exceptions import PermissionDenied
        from django.utils import timezone
        if not self.has_change_permission(request):
            raise PermissionDenied
        queryset.update(approved_by=request.user, approved_at=timezone.now())
