"""Serializers for registry patient records."""

from rest_framework import serializers


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
