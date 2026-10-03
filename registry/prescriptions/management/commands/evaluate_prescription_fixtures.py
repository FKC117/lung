"""Synthetic mapping metrics and optional read-only graph comparison."""
import json
from django.core.management.base import BaseCommand, CommandError
from prescriptions.evaluation.runner import evaluate_synthetic


class Command(BaseCommand):
    help = "Evaluate committed synthetic fixtures; never calls a provider or writes clinical data."

    def add_arguments(self, parser):
        parser.add_argument("--shadow", action="store_true", help="Compare a read-only LangGraph with the shared-service baseline.")

    def handle(self, **options):
        report = evaluate_synthetic(shadow=options["shadow"])
        self.stdout.write(json.dumps(report, indent=2))
        if not report["passed"]:
            raise CommandError("Synthetic mapping acceptance gate failed.")
