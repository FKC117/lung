"""Exercise configured admission caps in rolled-back synthetic scopes."""
import json
from hashlib import sha256
from uuid import uuid4
from zoneinfo import ZoneInfo
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.test import override_settings
from django.utils import timezone
from prescriptions.models import PrescriptionProviderBudget
from prescriptions.services.provider_budget import reserve_provider_budget, ProviderBudgetExhausted


class Command(BaseCommand):
    help = "Verify configured request/token/day denial without provider calls or retained counters."

    def handle(self, *args, **options):
        if not settings.PRESCRIPTION_PROVIDER_BUDGET_ENABLED or not all([
            settings.PRESCRIPTION_PROVIDER_BUDGET_REQUESTS, settings.PRESCRIPTION_PROVIDER_BUDGET_TOKEN_UNITS,
            settings.PRESCRIPTION_PROVIDER_BUDGET_DAILY_REQUESTS]):
            raise CommandError("Enable and configure all three admission limits first.")
        result = {}
        for kind in ["rpm", "token_units", "rpd"]:
            scope = "synthetic-admission-verification-" + str(uuid4())
            model = settings.PRESCRIPTION_EXTRACTION_MODEL
            key = sha256((scope + "\0" + model).encode()).hexdigest()
            with override_settings(PRESCRIPTION_PROVIDER_BUDGET_SCOPE=scope), transaction.atomic():
                row = PrescriptionProviderBudget.objects.create(scope_key=key, model_name=model, window_started_at=timezone.now(),
                    requests_reserved=settings.PRESCRIPTION_PROVIDER_BUDGET_REQUESTS if kind == "rpm" else 0,
                    token_units_reserved=settings.PRESCRIPTION_PROVIDER_BUDGET_TOKEN_UNITS if kind == "token_units" else 0)
                if kind == "rpd":
                    start = timezone.now().astimezone(ZoneInfo(settings.PRESCRIPTION_PROVIDER_BUDGET_DAILY_TIMEZONE)).replace(hour=0, minute=0, second=0, microsecond=0)
                    PrescriptionProviderBudget.objects.create(scope_key=sha256((scope + "\0" + model + "\0daily").encode()).hexdigest(),
                        model_name=model, window_started_at=start, requests_reserved=settings.PRESCRIPTION_PROVIDER_BUDGET_DAILY_REQUESTS)
                before = (row.requests_reserved, row.token_units_reserved)
                try:
                    reserve_provider_budget(["Synthetic verification only"], system_instruction="Synthetic verification")
                except ProviderBudgetExhausted as exc:
                    row.refresh_from_db()
                    result[kind] = {"denied": True, "reservation_unchanged": before == (row.requests_reserved, row.token_units_reserved), "retry_after_seconds": exc.retry_after_seconds}
                else:
                    raise CommandError("The configured admission cap was not enforced.")
                transaction.set_rollback(True)
        self.stdout.write(json.dumps({"checks": result, "provider_calls": 0, "retained_test_counters": 0}))
