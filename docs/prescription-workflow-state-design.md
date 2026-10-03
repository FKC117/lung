# Durable state and concurrency decision (P0.5)

Date: 2026-10-01 (Asia/Dhaka)

## Decision

Use the existing Django/PostgreSQL deployment for orchestration models and a LangGraph checkpointer compatible with the installed base API. Implement a small synchronous Django-backed saver with serialized checkpoint payloads and pending writes, verified against the installed LangGraph in restart/replay tests. This avoids introducing a second database or an uninstalled service adapter. Pin and verify the current LangGraph integration; move to the official PostgreSQL adapter later only if compatibility or maintenance evidence warrants it.

The inspected deployment runbook uses one solo Celery extraction worker and a separate general worker. Live worker/broker state was not inspected. The implementation must nevertheless serialize runs across multiple workers; a runbook alone is not a lock.

## Ownership

- `PrescriptionReview.reviewed_data` and its version are authoritative for reviewer edits and approval.
- `ExtractionRun` and associated immutable evidence artifacts describe one extraction result. Batch import must create a new result, not mutate finished evidence.
- A workflow run references one document/input hash and schema/prompt/model versions, tracks stage/status/budget, and keeps the originating draft/evidence artifact.
- Graph checkpoints and pending writes contain operational state. They never constitute a second clinical persistence service.
- Clinical observations and patient updates are written only by the established canonical transactional persistence service after explicit authorized actions.

## Identity and protection

- Stable workflow identity is a server-generated UUID; clients cannot select another document's thread identity.
- One active workflow per document revision is enforced by database locking/constraints and a bounded execution lease.
- Checkpoint namespace/ID/task write identity is unique per workflow; checkpoint reads require the workflow's document ownership scope.
- Retry reuse keys include document SHA, schema/prompt/model versions and relevant source artifact hashes. Changed source is a new revision.
- Review mutations require expected revision; save/approve/reopen/reject and publication serialize on the review row. Approval binds to the saved revision and repair checks the revision before applying anything.
- Pending writes use an upsert policy compatible with LangGraph; interrupted nodes must not perform non-idempotent clinical writes before a resume point.
- Worker replay may repeat an ambiguous provider attempt. Record uncertainty; do not claim exactly-once remote execution. Local writes use stable operation identities.

## Lifecycle and access

- Operational models have read-only searchable admin and explicit view permissions; no public raw-checkpoint endpoint.
- Checkpoints inherit clinical-data restrictions, private database backup rules, and configurable retention. Keep artifacts used by active reviews or publication provenance; do not cascade-delete published provenance.
- A cleanup command will handle completed operational checkpoints after a configured retention period, never prune active/paused workflows, and report counts without clinical payloads.
- Cancellation and quota waits are durable states; Celery schedules resumption rather than holding a worker asleep.

## Verification required before enabling the graph

Tests must recreate the saver instance/process state and resume the same graph; replay writes; resume a reviewer interrupt; fail before/after checkpoint; attempt concurrent admission and stale review updates; deny another user's artifacts; and verify database transaction rollback. New tables must have migrations and admin inspection. No new models or migrations are authorized as production deployment merely by this design document.


## Implemented checkpoint retention

`PRESCRIPTION_CHECKPOINT_RETENTION_DAYS=0` disables unconfigured cleanup. Operators select an approved positive duration; no automatic cleanup schedule is enabled. Run `python manage.py prune_prescription_checkpoints --retention-days 30` for sanitized counts only, then the same command with `--apply` after reviewing eligibility. This example duration is not a clinical retention policy.

Cleanup locks each workflow and review, protects running/waiting/queued/leased/recent runs and unpublished active reviews, and prunes aged operational checkpoint/write payloads only. It preserves source extraction, review data, publication provenance and run identity. Ready/needs-review runs require published or rejected review before pruning. Commands are restricted server-operator tools; checkpoint payloads have no public endpoint, and Django admin uses explicit view permissions with read-only metadata and hidden binary payloads. PostgreSQL backups must use the existing clinical-data access controls.
