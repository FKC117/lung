from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from options.models import TreatmentDrug, TreatmentModality, TreatmentProtocol, TreatmentProtocolDrug
from records.models import ClinicalObservation, Patient, TreatmentAdministration
from prescriptions.services.publish import _persist_record


class TreatmentFormMappingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="synthetic-mapping-test")
        patient = Patient.objects.create(registration_no="SYNTHETIC-001", patient_id="SYNTHETIC-001", name="Synthetic fixture")
        self.observation = ClinicalObservation.objects.create(patient=patient)
        modality = TreatmentModality.objects.create(name="Synthetic modality")
        protocol = TreatmentProtocol.objects.create(name="Synthetic protocol")
        drug = TreatmentDrug.objects.create(name="Synthetic drug")
        TreatmentProtocolDrug.objects.create(protocol=protocol, drug=drug)
        self.record = {"temp_id": "synthetic-treatment", "resolutions": {
            field: {"option_id": option.pk, "status": "resolved"}
            for field, option in (("modality", modality), ("protocol", protocol), ("drug", drug))
        }}
        self.values = {"modality": modality.pk, "protocol": protocol.pk, "drug": drug.pk,
                       "dose": "125.25", "dose_unit": "mg", "cycle_number": 2,
                       "administration_notes": "Synthetic administration note", "status": "active"}

    def test_actual_form_administration_fields_reach_canonical_model(self):
        context = {"review": None, "run": None, "user": self.user, "counts": {}}
        course = _persist_record("treatments", self.values, self.record, self.observation, {}, [], "treatments.0", context)
        administration = TreatmentAdministration.objects.get(treatment_course=course)
        self.assertEqual(administration.dose, Decimal("125.25"))
        self.assertEqual(administration.cycle_number, 2)
        self.assertEqual(administration.notes, "Synthetic administration note")
        self.assertEqual(administration.status, "planned")
        self.assertEqual(course.status, "active")
