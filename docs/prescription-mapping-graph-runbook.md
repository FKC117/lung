# Durable mapping graph: development operation

Verified locally on 2026-10-01. This graph maps an already completed extraction;
it is not yet the default upload/OCR/Gemini workflow.

## Current behavior

`prepare_mapping_workflow(extraction_run)` creates an explicit run identity and
captures document/source hashes and schema/prompt/model versions.
`execute_mapping_workflow(run.pk)` acquires a lease, resumes Django checkpoints,
and runs normalization, scoped resolution, evidence/domain validation and review
draft creation. `map_prescription_workflow.delay(str(run.pk))` schedules this
explicit workflow on the existing extraction queue. It does not call Gemini,
approve a review, associate an inferred patient or publish clinical records.

Existing reviewed data is preserved. Replaying a completed mapping keeps one
review. Changed extraction artifacts require a new run. There is no new public
checkpoint endpoint; call these internal functions only after verifying access
to the source document through the existing document ownership scope.

## Database and permissions

Migrations `0008_prescriptionworkflowrun_and_more` and
`0009_prescriptionreview_approved_revision_and_more` were applied locally.
Deployments must apply them before loading code that selects the new fields.
Workflow runs/checkpoints/pending writes have searchable read-only Django admin.
Grant their view permissions only to authorized operational reviewers. Binary
payloads are omitted from admin lists/forms; database backups contain clinical
state and follow the existing private database controls.

## Recovery

Re-execute the same workflow ID after a mapping failure. A live lease prevents
another worker from running that ID; an expired lease can be reclaimed. Never
rewrite checkpoint IDs or payloads. Nodes close background database connections.
The saver accepts pending writes arriving before their checkpoint and preserves
LangGraph special-write replacement rules.

`DjangoCheckpointSaver().delete_thread(str(run.pk))` is an explicit administrative
retention operation that removes checkpoints/writes while retaining the run and
canonical review. Do not prune active/review-paused runs. Scheduled configurable
retention and cancellation controls are not implemented yet.

## Review revisions and rollout limits

The current correction UI sends `expected_revision` for save, approval and
publication. Stale requests return HTTP 409; save-then-approve uses the revision
returned by the successful save. Approval records its revision. Published reviews
cannot be reopened or rejected. Legacy API clients may omit the revision for
compatibility, and pre-existing approvals with null approved revision remain
readable; strict revision enforcement for all clients is still a rollout task.

The production provider policy still defaults to disabled. Live worker restart,
broker delivery, graph extraction stages, quota coordination, targeted repair,
interrupt/resume, cross-user graph APIs, retention scheduling and clinical pilot
evaluation remain unverified or unimplemented. Do not enable a production pilot
on the strength of the synthetic mapping tests.

## Local artifacts and quota retry reuse (2026-10-02)

The existing extraction worker now uses `ensure_page_artifact`. Complete ordered
pages carry the document SHA and extractor configuration version. A retry reuses
them, including their page IDs, rather than repeating PDF/OCR work. A changed
configuration rebuilds the artifact; a failed extraction preserves prior pages.
New ExtractionRun results keep a source-page snapshot. Mapping validates against
that snapshot, preserving the original evidence if current OCR pages change.

Quota errors propagate to Celery's existing delayed-retry handler. This is local
artifact reuse only: it does not implement shared project quotas, stage-by-stage
extraction checkpoints, or exactly-once external provider calls. Those tracker
tasks remain open.
