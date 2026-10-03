"""Compatibility entry point for the canonical longitudinal intake draft."""

from .draft_schema import normalize_extraction
from .option_resolver import resolve_draft_options
from .draft_evidence import validate_source_evidence
from .readiness import mark_ready_records


def build_intake_draft(result, *, document_id, linked_patient_id=None, resolve_options=True, pages=None):
    draft = normalize_extraction(
        result,
        document_id=document_id,
        linked_patient_id=linked_patient_id,
    )
    validate_source_evidence(draft, pages)
    return mark_ready_records(resolve_draft_options(draft)) if resolve_options else draft
