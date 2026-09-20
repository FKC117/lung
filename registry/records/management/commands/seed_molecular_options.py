from django.core.management.base import BaseCommand

from options.models import MolecularPathologyResult


class Command(BaseCommand):
    help = "Create the molecular result required for derived negative findings."

    def handle(self, *args, **options):
        result, created = MolecularPathologyResult.objects.get_or_create(
            code="not_detected",
            defaults={"name": "Not detected"},
        )
        state = "Created" if created else "Already present"
        self.stdout.write(self.style.SUCCESS(f"{state}: {result.code}"))
