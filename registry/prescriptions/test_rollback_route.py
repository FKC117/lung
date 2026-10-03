from types import SimpleNamespace
from unittest.mock import patch
from django.test import TestCase, override_settings
from prescriptions.models import PrescriptionDocument, PrescriptionWorkflowRun
from prescriptions.tasks import process_prescription_document


class LegacyRouteRollbackTests(TestCase):
    @override_settings(PRESCRIPTION_AGENTIC_EXTRACTION_ENABLED=False)
    def test_disabling_graph_uses_existing_route_without_deleting_saved_workflows(self):
        document=PrescriptionDocument.objects.create(file="synthetic.pdf",sha256="1"*64)
        saved=PrescriptionWorkflowRun.objects.create(document=document,document_sha256=document.sha256,status="needs_review")
        task=process_prescription_document
        task.push_request(id="synthetic-rollback",retries=0)
        try:
            with patch("prescriptions.tasks.process_document",return_value=SimpleNamespace(pk=7,status="completed")) as legacy,patch("prescriptions.services.extraction_graph.execute_extraction_workflow") as graph:
                result=task.run(document.pk)
            legacy.assert_called_once()
            graph.assert_not_called()
            self.assertEqual(result["status"],"completed")
            self.assertTrue(PrescriptionWorkflowRun.objects.filter(pk=saved.pk).exists())
        finally:
            task.pop_request()
