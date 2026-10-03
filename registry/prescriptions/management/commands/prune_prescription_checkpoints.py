import json
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from prescriptions.services.checkpoint_retention import prune_checkpoints


class Command(BaseCommand):
    help = "Dry-run checkpoint retention cleanup; --apply deletes eligible operational payloads only."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--retention-days", type=int, default=settings.PRESCRIPTION_CHECKPOINT_RETENTION_DAYS)

    def handle(self, *args, **options):
        try:
            result = prune_checkpoints(retention_days=options["retention_days"], apply=options["apply"])
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result))
