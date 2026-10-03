"""Shared conservative admission budget; no guessed Gemini tier limits."""
from datetime import timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from hashlib import sha256
import math
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from prescriptions.models import PrescriptionProviderBudget, LLMInvocation
from prescriptions.services.extraction import GeminiRateLimitError


class ProviderBudgetConfigurationError(ValueError):
    pass


class ProviderBudgetExhausted(GeminiRateLimitError):
    local_budget = True


@transaction.atomic
def reserve_provider_budget(texts, *, system_instruction):
    if not settings.PRESCRIPTION_PROVIDER_BUDGET_ENABLED:
        return
    scope = settings.PRESCRIPTION_PROVIDER_BUDGET_SCOPE
    model = settings.PRESCRIPTION_EXTRACTION_MODEL
    seconds = settings.PRESCRIPTION_PROVIDER_BUDGET_WINDOW_SECONDS
    requests = settings.PRESCRIPTION_PROVIDER_BUDGET_REQUESTS
    tokens = settings.PRESCRIPTION_PROVIDER_BUDGET_TOKEN_UNITS
    output = settings.PRESCRIPTION_PROVIDER_MAX_OUTPUT_TOKENS
    daily = settings.PRESCRIPTION_PROVIDER_BUDGET_DAILY_REQUESTS
    if not scope or not model or seconds <= 0 or requests < 0 or tokens < 0 or daily < 0 or not (requests or tokens) or (tokens and output <= 0):
        raise ProviderBudgetConfigurationError("Configure scope, model, positive window and budget limits; token budgeting also requires an output cap.")
    texts = list(texts)
    if not texts:
        return
    # Conservative admission units, not claimed provider-measured token usage.
    overhead = len(system_instruction.encode("utf-8"))
    units = sum(len(text.encode("utf-8")) + overhead + output for text in texts) if tokens else 0
    if (requests and len(texts) > requests) or (tokens and units > tokens):
        raise ProviderBudgetConfigurationError("This request exceeds the entire configured budget window; reduce the batch/input or adjust verified limits.")
    key = sha256((scope + "\0" + model).encode()).hexdigest()
    now = timezone.now()
    row, _ = PrescriptionProviderBudget.objects.get_or_create(scope_key=key, defaults={"model_name": model, "window_started_at": now})
    row = PrescriptionProviderBudget.objects.select_for_update().get(pk=row.pk)
    end = row.window_started_at + timedelta(seconds=seconds)
    if now >= end:
        row.window_started_at = now
        row.requests_reserved = row.token_units_reserved = 0
        end = now + timedelta(seconds=seconds)
    if (requests and row.requests_reserved + len(texts) > requests) or (tokens and row.token_units_reserved + units > tokens):
        raise ProviderBudgetExhausted(retry_after_seconds=max(1, math.ceil((end - now).total_seconds())))
    row.requests_reserved += len(texts)
    row.token_units_reserved += units
    row.save()

    if daily:
        if len(texts) > daily:
            raise ProviderBudgetConfigurationError("This batch exceeds the configured daily request budget.")
        try:
            local = now.astimezone(ZoneInfo(settings.PRESCRIPTION_PROVIDER_BUDGET_DAILY_TIMEZONE))
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ProviderBudgetConfigurationError("Configure a valid daily quota reset timezone.") from exc
        start = local.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = start + timedelta(days=1)
        day_key = sha256((scope + "\0" + model + "\0daily").encode()).hexdigest()
        day_row, _ = PrescriptionProviderBudget.objects.get_or_create(scope_key=day_key,
            defaults={"model_name": model, "window_started_at": start,
                      "requests_reserved": LLMInvocation.objects.filter(model_name=model, requested_at__gte=start).exclude(status=LLMInvocation.Status.SKIPPED).count()})
        day_row = PrescriptionProviderBudget.objects.select_for_update().get(pk=day_row.pk)
        if day_row.window_started_at != start:
            day_row.window_started_at = start
            day_row.requests_reserved = day_row.token_units_reserved = 0
        if day_row.requests_reserved + len(texts) > daily:
            # The enclosing transaction rolls back the minute reservation as well.
            raise ProviderBudgetExhausted(retry_after_seconds=max(1, math.ceil((day_end - now).total_seconds())))
        day_row.requests_reserved += len(texts)
        day_row.save()
