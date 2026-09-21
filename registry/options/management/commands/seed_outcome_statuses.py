from django.core.management.base import BaseCommand

from options.models import DiseaseProgressionStatus, SurvivalStatus


class Command(BaseCommand):
    help = "Seed stable disease-progression and survival status codes."

    def handle(self, *args, **options):
        for model, values in (
            (
                DiseaseProgressionStatus,
                (
                    ("no_progression", "No progression"),
                    ("progressed", "Progressed"),
                    ("unknown", "Unknown"),
                ),
            ),
            (
                SurvivalStatus,
                (
                    ("alive", "Alive"),
                    ("dead", "Dead"),
                    ("lost_to_follow_up", "Lost to follow up"),
                ),
            ),
        ):
            for code, name in values:
                model.objects.get_or_create(code=code, defaults={"name": name})

        self.stdout.write(self.style.SUCCESS("Seeded outcome status codes."))
