from typing import TypedDict
from django.contrib.admin.sites import site
from django.test import TransactionTestCase
from langgraph.graph import StateGraph, START, END
from prescriptions.models import PrescriptionDocument, PrescriptionWorkflowRun, PrescriptionWorkflowCheckpoint
from prescriptions.services.checkpoint import DjangoCheckpointSaver
from prescriptions.services.workflow_state import acquire_workflow_lease, release_workflow_lease, WorkflowLeaseConflict


class SyntheticState(TypedDict):
    value: int


class DurableCheckpointTests(TransactionTestCase):
    def setUp(self):
        document = PrescriptionDocument.objects.create(file="synthetic.pdf", original_filename="synthetic.pdf", sha256="c" * 64)
        self.run = PrescriptionWorkflowRun.objects.create(document=document, document_sha256=document.sha256)
        self.config = {"configurable": {"thread_id": str(self.run.pk)}}

    def graph(self, first, second):
        builder = StateGraph(SyntheticState)
        builder.add_node("first", first)
        builder.add_node("second", second)
        builder.add_edge(START, "first")
        builder.add_edge("first", "second")
        builder.add_edge("second", END)
        return builder.compile(checkpointer=DjangoCheckpointSaver())

    def test_recreated_graph_resumes_after_failure_without_replaying_completed_node(self):
        calls = []
        def first(state):
            calls.append("first")
            return {"value": state["value"] + 1}
        def failed(state):
            raise RuntimeError("Synthetic interrupted worker")
        with self.assertRaises(RuntimeError):
            self.graph(first, failed).invoke({"value": 0}, self.config)
        self.assertTrue(PrescriptionWorkflowCheckpoint.objects.filter(run=self.run).exists())
        result = self.graph(first, lambda state: {"value": state["value"] + 1}).invoke(None, self.config)
        self.assertEqual(result["value"], 2)
        self.assertEqual(calls, ["first"])
        history = list(DjangoCheckpointSaver().list(self.config, limit=2))
        self.assertEqual(len(history), 2)
        self.assertIsNotNone(history[0].parent_config)

    def test_admin_cannot_add_or_change_operational_state(self):
        request = object()
        for model in (PrescriptionWorkflowRun, PrescriptionWorkflowCheckpoint):
            self.assertFalse(site._registry[model].has_add_permission(request))
            self.assertFalse(site._registry[model].has_change_permission(request))

    def test_retention_deletes_checkpoints_but_keeps_run(self):
        self.graph(lambda state: state, lambda state: state).invoke({"value": 1}, self.config)
        DjangoCheckpointSaver().delete_thread(str(self.run.pk))
        self.assertFalse(self.run.checkpoints.exists())
        self.assertTrue(PrescriptionWorkflowRun.objects.filter(pk=self.run.pk).exists())

    def test_only_the_current_lease_owner_can_finish_a_run(self):
        from uuid import uuid4
        owner = acquire_workflow_lease(self.run.pk)
        with self.assertRaises(WorkflowLeaseConflict):
            acquire_workflow_lease(self.run.pk)
        with self.assertRaises(WorkflowLeaseConflict):
            release_workflow_lease(self.run.pk, uuid4())
        release_workflow_lease(self.run.pk, owner)
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, "needs_review")
        self.assertIsNone(self.run.lease_owner)

    def test_changed_document_identity_cannot_resume(self):
        self.run.document_sha256 = "e" * 64
        self.run.save()
        with self.assertRaises(WorkflowLeaseConflict):
            acquire_workflow_lease(self.run.pk)

    def test_reclaimed_lease_rejects_stale_checkpoint_and_pending_writes(self):
        from datetime import timedelta
        from django.utils import timezone
        from langgraph.checkpoint.base import empty_checkpoint
        owner = acquire_workflow_lease(self.run.pk)
        old_config = {"configurable": {"thread_id": str(self.run.pk), "lease_owner": str(owner)}}
        saver = DjangoCheckpointSaver()
        saved = saver.put(old_config, empty_checkpoint(), {}, {})
        self.assertEqual(saved["configurable"]["lease_owner"], str(owner))
        PrescriptionWorkflowRun.objects.filter(pk=self.run.pk).update(lease_expires_at=timezone.now() - timedelta(seconds=1))
        acquire_workflow_lease(self.run.pk)
        before = self.run.checkpoints.count()
        with self.assertRaises(WorkflowLeaseConflict):
            saver.put(old_config, empty_checkpoint(), {}, {})
        with self.assertRaises(WorkflowLeaseConflict):
            saver.put_writes(saved, [("value", 99)], "synthetic-old-worker")
        self.assertEqual(self.run.checkpoints.count(), before)
        self.assertFalse(self.run.pending_writes.exists())
