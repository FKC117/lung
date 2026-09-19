"""Serializers for the controlled clinical vocabulary used by data entry."""

from rest_framework import serializers


class OptionSerializerBase(serializers.ModelSerializer):
    """Expose a stable label alongside the primary-key values used by forms."""

    display = serializers.SerializerMethodField(read_only=True)

    def get_display(self, instance):
        return str(instance)


def build_option_serializer(model):
    """Create a serializer for each lookup model without duplicating boilerplate."""

    readonly = tuple(
        field.name
        for field in model._meta.fields
        if field.primary_key
        or field.name in {"id", "source_created_at", "source_updated_at"}
    )
    meta = type(
        "Meta",
        (),
        {"model": model, "fields": "__all__", "read_only_fields": readonly},
    )
    return type(f"{model.__name__}Serializer", (OptionSerializerBase,), {"Meta": meta})
