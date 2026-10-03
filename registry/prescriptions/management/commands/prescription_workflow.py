import json
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from prescriptions.models import PrescriptionWorkflowRun
from prescriptions.services.workflow_recovery import cancel_workflow, workflow_status, queue_failed_extraction_resume
from prescriptions.services.workflow_state import WorkflowLeaseConflict


class Command(BaseCommand):
    help = "Inspect or cancel a prescription workflow without exposing clinical payloads."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["status", "cancel", "resume"])
        parser.add_argument("workflow_id")

    def handle(self, *args, **options):
        try:
            if options["action"] == "cancel":
                cancel_workflow(options["workflow_id"])
            if options["action"] == "resume":
                queue_failed_extraction_resume(options["workflow_id"])
            result = workflow_status(options["workflow_id"])
        except (ValueError, ValidationError, PrescriptionWorkflowRun.DoesNotExist, WorkflowLeaseConflict) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result))
