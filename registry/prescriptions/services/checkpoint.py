"""Synchronous LangGraph checkpoint storage in the authoritative Django DB.

Internal worker API only. Thread identities are existing workflow run UUIDs;
there is deliberately no endpoint exposing serialized clinical state.
Ordinary state channels are stored together, without a second blob database.
"""
from django.db import transaction, connections
from django.utils import timezone
from functools import wraps
from threading import current_thread, main_thread
from langgraph.checkpoint.base import BaseCheckpointSaver, CheckpointTuple, WRITES_IDX_MAP, get_checkpoint_metadata
from prescriptions.models import PrescriptionWorkflowCheckpoint, PrescriptionWorkflowRun, PrescriptionWorkflowWrite


def close_worker_connections(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        finally:
            if current_thread() is not main_thread():
                connections.close_all()
    return wrapped


class DjangoCheckpointSaver(BaseCheckpointSaver):
    def _lock_writer(self, values):
        from .workflow_state import WorkflowLeaseConflict
        run = PrescriptionWorkflowRun.objects.select_for_update().get(pk=values["thread_id"])
        if values.get("lease_owner") or run.versions.get("extraction_run_id"):
            if (not values.get("lease_owner") or str(run.lease_owner) != values["lease_owner"]
                    or not run.lease_expires_at or run.lease_expires_at <= timezone.now()
                    or run.status != "running"):
                raise WorkflowLeaseConflict("Checkpoint writer no longer owns an active workflow lease.")
        return run

    def _query(self, config):
        values = config["configurable"]
        return PrescriptionWorkflowCheckpoint.objects.filter(
            run_id=values["thread_id"], namespace=values.get("checkpoint_ns", ""))

    def _config(self, row, checkpoint_id=None):
        return {"configurable": {"thread_id": str(row.run_id), "checkpoint_ns": row.namespace,
                                 "checkpoint_id": checkpoint_id or row.checkpoint_id}}

    def _tuple(self, row):
        return CheckpointTuple(
            config=self._config(row),
            checkpoint=self.serde.loads_typed((row.payload_type, bytes(row.payload))),
            metadata=self.serde.loads_typed((row.metadata_type, bytes(row.metadata))),
            parent_config=self._config(row, row.parent_checkpoint_id) if row.parent_checkpoint_id else None,
            pending_writes=[(item.task_id, item.channel, self.serde.loads_typed((item.payload_type, bytes(item.payload))))
                            for item in PrescriptionWorkflowWrite.objects.filter(run_id=row.run_id, namespace=row.namespace, checkpoint_id=row.checkpoint_id).order_by("task_id", "write_index")],
        )

    def get_tuple(self, config):
        query = self._query(config)
        checkpoint_id = config["configurable"].get("checkpoint_id")
        if checkpoint_id:
            query = query.filter(checkpoint_id=checkpoint_id)
        row = query.order_by("-checkpoint_id").first()
        return self._tuple(row) if row else None

    def list(self, config, *, filter=None, before=None, limit=None):
        query = self._query(config) if config else PrescriptionWorkflowCheckpoint.objects.all()
        if before:
            query = query.filter(checkpoint_id__lt=before["configurable"]["checkpoint_id"])
        count = 0
        for row in query.order_by("-checkpoint_id").iterator():
            item = self._tuple(row)
            if filter and any(item.metadata.get(key) != value for key, value in filter.items()):
                continue
            if limit is not None and count >= limit:
                break
            yield item
            count += 1

    @close_worker_connections
    @transaction.atomic
    def put(self, config, checkpoint, metadata, new_versions):
        values = config["configurable"]
        # Validate identity before storing; checkpointing cannot create runs.
        self._lock_writer(values)
        payload_type, payload = self.serde.dumps_typed(checkpoint)
        metadata_type, metadata_payload = self.serde.dumps_typed(get_checkpoint_metadata(config, metadata))
        row, created = PrescriptionWorkflowCheckpoint.objects.get_or_create(
            run_id=values["thread_id"], namespace=values.get("checkpoint_ns", ""), checkpoint_id=checkpoint["id"],
            defaults={"parent_checkpoint_id": values.get("checkpoint_id", ""),
                      "payload_type": payload_type, "payload": payload,
                      "metadata_type": metadata_type, "metadata": metadata_payload})
        if not created and (row.payload_type != payload_type or bytes(row.payload) != payload):
            raise ValueError("Checkpoint identity cannot be reused for different state.")
        result = self._config(row)
        if values.get("lease_owner"):
            result["configurable"]["lease_owner"] = values["lease_owner"]
        return result

    @close_worker_connections
    @transaction.atomic
    def put_writes(self, config, writes, task_id, task_path=""):
        values = config["configurable"]
        self._lock_writer(values)
        for index, (channel, value) in enumerate(writes):
            payload_type, payload = self.serde.dumps_typed(value)
            write_index = WRITES_IDX_MAP.get(channel, index)
            defaults = {"task_path": task_path, "channel": channel, "payload_type": payload_type, "payload": payload}
            lookup = {"run_id": values["thread_id"], "namespace": values.get("checkpoint_ns", ""),
                      "checkpoint_id": values["checkpoint_id"], "task_id": task_id, "write_index": write_index}
            if write_index < 0:
                PrescriptionWorkflowWrite.objects.update_or_create(**lookup, defaults=defaults)
            else:
                PrescriptionWorkflowWrite.objects.get_or_create(**lookup, defaults=defaults)

    def delete_thread(self, thread_id):
        # Explicit retention action. Preserve run identity/audit and the review.
        PrescriptionWorkflowCheckpoint.objects.filter(run_id=thread_id).delete()
        PrescriptionWorkflowWrite.objects.filter(run_id=thread_id).delete()
