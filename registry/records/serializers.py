"""Serializers for registry patient records."""

from rest_framework import serializers

from .models import TreatmentAdministration, TreatmentCourse


class RecordSerializerBase(serializers.ModelSerializer):
    """Shared serializer behavior for all registry record models."""

    display = serializers.SerializerMethodField(read_only=True)

    def get_display(self, instance):
        return str(instance)


def build_record_serializer(model):
    """Create a serializer for a record model without duplicated boilerplate."""

    readonly = tuple(
        field.name
        for field in model._meta.fields
        if field.primary_key or not field.editable
    )
    meta = type(
        "Meta",
        (),
        {"model": model, "fields": "__all__", "read_only_fields": readonly},
    )
    return type(f"{model.__name__}Serializer", (RecordSerializerBase,), {"Meta": meta})


class TreatmentCourseSerializer(RecordSerializerBase):
    class Meta:
        model = TreatmentCourse
        fields = "__all__"

    def validate(self, attrs):
        started_on = attrs.get("started_on", getattr(self.instance, "started_on", None))
        ended_on = attrs.get("ended_on", getattr(self.instance, "ended_on", None))
        if started_on and ended_on and ended_on < started_on:
            raise serializers.ValidationError({"ended_on": "The end date cannot precede the start date."})
        return attrs


class TreatmentAdministrationSerializer(RecordSerializerBase):
    class Meta:
        model = TreatmentAdministration
        fields = "__all__"

    def validate(self, attrs):
        course = attrs.get("treatment_course", getattr(self.instance, "treatment_course", None))
        observation = attrs.get("observation", getattr(self.instance, "observation", None))
        drug = attrs.get("drug", getattr(self.instance, "drug", None))
        administered_on = attrs.get("administered_on", getattr(self.instance, "administered_on", None))
        errors = {}

        if course and observation and course.observation.patient_id != observation.patient_id:
            errors["observation"] = "The administration observation must belong to the course patient."
        if course and drug and not course.protocol.drugs.filter(pk=drug.pk).exists():
            errors["drug"] = "The drug must belong to the treatment course protocol."
        if course and administered_on and course.started_on and administered_on < course.started_on:
            errors["administered_on"] = "The administration date cannot precede the course start date."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs
