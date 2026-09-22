"""Serializers for registry patient records."""

from rest_framework import serializers

from .models import RadiotherapyCourse, TreatmentAdministration, TreatmentCourse


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


class AssessmentSerializerBase(RecordSerializerBase):
    """Validate that a response assessment belongs to its treatment patient."""

    def validate(self, attrs):
        observation = attrs.get("observation", getattr(self.instance, "observation", None))
        treatment_course = attrs.get("treatment_course", getattr(self.instance, "treatment_course", None))
        if (
            observation
            and treatment_course
            and observation.patient_id != treatment_course.observation.patient_id
        ):
            raise serializers.ValidationError(
                {"observation": "The assessment observation and treatment course must belong to the same patient."}
            )
        return attrs


def build_assessment_serializer(model):
    meta = type("Meta", (), {"model": model, "fields": "__all__"})
    return type(f"{model.__name__}Serializer", (AssessmentSerializerBase,), {"Meta": meta})


class OutcomeSerializerBase(RecordSerializerBase):
    def validate(self, attrs):
        status_value = attrs.get("status", getattr(self.instance, "status", None))
        errors = {}

        if "progression_date" in self.fields:
            assessed_on = attrs.get("assessed_on", getattr(self.instance, "assessed_on", None))
            progression_date = attrs.get("progression_date", getattr(self.instance, "progression_date", None))
            observation = attrs.get("observation", getattr(self.instance, "observation", None))
            treatment_course = attrs.get("treatment_course", getattr(self.instance, "treatment_course", None))
            if (
                observation
                and treatment_course
                and observation.patient_id != treatment_course.observation.patient_id
            ):
                errors["observation"] = "The progression observation and treatment course must belong to the same patient."
            if status_value and status_value.code == "progressed" and not progression_date:
                errors["progression_date"] = "A progression date is required when status is progressed."
            if progression_date and assessed_on and progression_date > assessed_on:
                errors["progression_date"] = "The progression date cannot exceed the assessment date."

        if "death_date" in self.fields:
            followed_up_on = attrs.get("followed_up_on", getattr(self.instance, "followed_up_on", None))
            death_date = attrs.get("death_date", getattr(self.instance, "death_date", None))
            if status_value and status_value.code == "dead" and not death_date:
                errors["death_date"] = "A death date is required when status is dead."
            if status_value and status_value.code == "alive" and death_date:
                errors["death_date"] = "An alive follow-up cannot contain a death date."
            if death_date and followed_up_on and death_date > followed_up_on:
                errors["death_date"] = "The death date cannot exceed the follow-up date."

        if errors:
            raise serializers.ValidationError(errors)
        return attrs


def build_outcome_serializer(model):
    meta = type("Meta", (), {"model": model, "fields": "__all__"})
    return type(f"{model.__name__}Serializer", (OutcomeSerializerBase,), {"Meta": meta})


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


class RadiotherapyCourseSerializer(RecordSerializerBase):
    """Expose radiotherapy course validation as clean API 400 responses."""

    class Meta:
        model = RadiotherapyCourse
        fields = "__all__"
        read_only_fields = ("planned_total_dose_cgy", "delivered_total_dose_cgy")

    def validate(self, attrs):
        started_on = attrs.get("started_on", getattr(self.instance, "started_on", None))
        ended_on = attrs.get("ended_on", getattr(self.instance, "ended_on", None))
        planned_fractions = attrs.get(
            "planned_fractions", getattr(self.instance, "planned_fractions", None)
        )
        completed_fractions = attrs.get(
            "completed_fractions", getattr(self.instance, "completed_fractions", None)
        )
        errors = {}

        if started_on and ended_on and ended_on < started_on:
            errors["ended_on"] = "End date cannot precede start date."
        if (
            planned_fractions is not None
            and completed_fractions is not None
            and completed_fractions > planned_fractions
        ):
            errors["completed_fractions"] = "Completed fractions cannot exceed planned fractions."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs
