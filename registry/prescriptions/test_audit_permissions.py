from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib import admin
from prescriptions.models import LLMInvocation


class RestrictedInvocationAuditPermissionTests(TestCase):
    def test_only_explicit_audit_permission_can_read_and_neither_user_can_mutate(self):
        ordinary = get_user_model().objects.create_user(username="synthetic-ordinary",is_staff=True)
        viewer = get_user_model().objects.create_user(username="synthetic-audit-viewer",is_staff=True)
        viewer.user_permissions.add(Permission.objects.get(content_type__app_label="prescriptions",codename="view_llminvocation"))
        model_admin = admin.site._registry[LLMInvocation]
        request = RequestFactory().get("/admin/prescriptions/llminvocation/")
        for user, allowed in ((ordinary,False),(viewer,True)):
            request.user=user
            self.assertEqual(model_admin.has_view_permission(request),allowed)
            self.assertFalse(model_admin.has_add_permission(request))
            self.assertFalse(model_admin.has_change_permission(request))
            self.assertFalse(model_admin.has_delete_permission(request))
