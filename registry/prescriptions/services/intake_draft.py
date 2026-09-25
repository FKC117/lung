"""Compatibility entry point for the canonical longitudinal intake draft."""

from .draft_schema import normalize_extraction
from .option_resolver import resolve_draft_options


def build_intake_draft(result, *, document_id, linked_patient_id=None, resolve_options=True):
    draft = normalize_extraction(
        result,
        document_id=document_id,
        linked_patient_id=linked_patient_id,
    )
    return resolve_draft_options(draft) if resolve_options else draft
