"""Sanitized recovery categories; never return provider messages or input content."""
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import math


@dataclass(frozen=True)
class ProviderFailure:
    category: str
    retryable: bool
    retry_after_seconds: int | None = None


def classify_provider_failure(error, *, now=None):
    response = getattr(error, "response", None)
    code = next((value for value in (getattr(error, "code", None), getattr(error, "status_code", None), getattr(response, "status_code", None)) if isinstance(value, int)), None)
    headers = getattr(response, "headers", {}) or {}
    value = headers.get("retry-after") or headers.get("Retry-After")
    delay = None
    if value:
        try:
            delay = max(1, math.ceil(float(value)))
        except (TypeError, ValueError, OverflowError):
            try:
                clock = now or datetime.now(timezone.utc)
                parsed = parsedate_to_datetime(value)
                if parsed.utcoffset() is not None:
                    delay = max(1, math.ceil((parsed - clock).total_seconds()))
            except (TypeError, ValueError, OverflowError):
                pass
    if code in {401, 403}:
        return ProviderFailure("authentication", False)
    if code in {400, 404, 422}:
        return ProviderFailure("configuration", False)
    if code == 429:
        # Only explicit structured quota identifiers establish a daily limit.
        details = getattr(error, "details", None)
        if isinstance(details, list):
            for detail in details:
                if not isinstance(detail, dict):
                    continue
                for violation in detail.get("violations", []):
                    if isinstance(violation, dict) and "perday" in str(violation.get("quotaId", "")).replace("_", "").lower():
                        return ProviderFailure("daily_exhaustion", False, delay)
        return ProviderFailure("quota", True, delay)
    if code in {408, 500, 502, 503, 504} or isinstance(error, (TimeoutError, ConnectionError)):
        return ProviderFailure("transient_service", True, delay)
    return ProviderFailure("unknown", False)


def audit_failure_category(error):
    """Bounded audit vocabulary; arbitrary exception attributes are never telemetry."""
    category = getattr(error, "category", None)
    allowed = {"authentication", "configuration", "daily_exhaustion", "quota",
               "transient_service", "provider_blocked", "truncated", "incomplete"}
    if isinstance(category, str) and category in allowed:
        return category
    if isinstance(error, ValueError):
        return "invalid_output"
    return classify_provider_failure(error).category
