"""Explicit outbound-data boundary shared by direct and batch Gemini calls.

A hash allowlist is an operator attestation, not an automated de-identification
claim. It approves the exact page-wise outbound text, not an entire deployment.
"""

from hashlib import sha256
import re

from django.conf import settings


class ProviderDataPolicyError(ValueError):
    """An outbound input has not been approved under the configured policy."""


def require_approved_gemini_input(input_text):
    policy = settings.PRESCRIPTION_GEMINI_DATA_POLICY
    # Explicit deployment-owner choice; does not attest that content is non-sensitive.
    # Provider suitability remains the operator's responsibility, not a billing gate.
    if policy == "enabled":
        return
    if policy == "disabled":
        raise ProviderDataPolicyError(
            "Gemini transmission is disabled by the data policy. Local extraction remains available."
        )
    if policy != "approved_non_sensitive":
        raise ProviderDataPolicyError(
            "PRESCRIPTION_GEMINI_DATA_POLICY must be disabled, enabled or approved_non_sensitive; "
            "approved_non_sensitive requires "
            "an approval reference and the exact approved input SHA256. Local extraction remains available."
        )
    if not settings.PRESCRIPTION_GEMINI_DATA_APPROVAL_REFERENCE:
        raise ProviderDataPolicyError("Record the non-sensitive input review reference before enabling Gemini transmission.")
    approved = settings.PRESCRIPTION_GEMINI_APPROVED_INPUT_SHA256
    if not isinstance(approved, (list, tuple)) or any(
        not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
        for value in approved
    ):
        raise ProviderDataPolicyError("The approved Gemini input hash list is invalid.")
    if sha256(input_text.encode("utf-8")).hexdigest() not in approved:
        raise ProviderDataPolicyError(
            "This exact extracted text has not been reviewed and approved as non-sensitive for Gemini."
        )
