from django.test import TestCase, RequestFactory
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from options.models import TreatmentDrug
from prescriptions.models import PrescriptionDrugAlias


class AliasApprovalAdminTests(TestCase):
    def test_only_authorized_action_approves_and_later_edit_revokes_approval(self):
        user = get_user_model().objects.create_user(username="synthetic-unprivileged")
        owner = get_user_model().objects.create_superuser(username="synthetic-owner",email="synthetic@example.invalid",password="synthetic")
        drug = TreatmentDrug.objects.create(name="Synthetic medicine")
        alias = PrescriptionDrugAlias.objects.create(alias="Synthetic brand",drug=drug)
        model_admin = admin.site._registry[PrescriptionDrugAlias]
        request = RequestFactory().post("/admin/prescriptions/prescriptiondrugalias/")
        request.user = user
        with self.assertRaises(PermissionDenied):
            model_admin.approve_aliases(request,PrescriptionDrugAlias.objects.filter(pk=alias.pk))
        alias.refresh_from_db()
        self.assertIsNone(alias.approved_by)
        request.user = owner
        model_admin.approve_aliases(request,PrescriptionDrugAlias.objects.filter(pk=alias.pk))
        alias.refresh_from_db()
        self.assertEqual(alias.approved_by,owner)
        alias.alias = "Changed synthetic brand"
        model_admin.save_model(request,alias,None,True)
        alias.refresh_from_db()
        self.assertIsNone(alias.approved_by)
