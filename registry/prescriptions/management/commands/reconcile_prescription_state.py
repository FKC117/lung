import json
from django.core.management.base import BaseCommand, CommandError
from prescriptions.models import PrescriptionDocument
from prescriptions.services.stale_processing import reconcile_stale_processing


class Command(BaseCommand):
    help = "Dry-run reconciliation of stale processing with newer completed evidence."

    def add_arguments(self, parser):
        parser.add_argument("document_id", type=int)
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--minimum-age-seconds", type=int, default=3600)

    def handle(self, *args, **options):
        try:
            result = reconcile_stale_processing(options["document_id"], apply=options["apply"],
                minimum_age_seconds=options["minimum_age_seconds"])
        except (ValueError, PrescriptionDocument.DoesNotExist) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result))
