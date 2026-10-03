# Checkpointed extraction rollout

`PRESCRIPTION_AGENTIC_EXTRACTION_ENABLED=false` preserves the existing upload task. Set it to `true` only in an approved environment and restart the extraction workers to use the graph route. This flag does not bypass the independent provider data-policy gate or provider budget admission.

The graph reuses local page extraction, Gemini enrichment, contract normalization, option resolution, evidence validation and review draft persistence. It creates no clinical observations and never approves or publishes a review. Existing reviewer-owned data is preserved.

Each Celery task ID identifies one workflow and one pending extraction. Retry/redelivery must retain that ID. PostgreSQL checkpoints resume the next incomplete stage; OCR snapshots and completed provider results also persist independently of checkpoints. A matching succeeded invocation can recover an answer after an artifact-save crash. An external response lost before its invocation audit is saved remains ambiguous and may require another provider call; this is not an exactly-once external API guarantee.

Quota waits release the lease and return to Celery's countdown scheduling. The lease expires after one hour if a worker disappears. A competing delivery cannot commit local/provider/draft results under a changed or expired lease. Source SHA and schema/prompt/model/extractor configuration changes reject extraction-stage resume. Start a new workflow for changed configuration; do not modify old evidence or checkpoints.

Checkpoint and pending-write commits also lock the workflow row and check the live owner, expiry and running status. A reclaimed or cancelled worker cannot publish stale checkpoint state. Lease conflicts are excluded from automatic Celery retries. Provider Retry-After guidance is never shortened by the normal exponential-backoff cap.

When configured quota retries are exhausted, the graph completes a local-evidence exception draft without another provider request. The extraction is completed, the document is ready for review, and Gemini remains explicitly unavailable/unresolved. Completion does not mean Gemini succeeded or publication is permitted.

Operator commands (from `D:\Lung`):

```powershell
.\venv\Scripts\python.exe registry\manage.py prescription_workflow status <workflow-uuid>
.\venv\Scripts\python.exe registry\manage.py prescription_workflow cancel <workflow-uuid>
```

Status emits identifiers, status, checkpoint count and lease timing, without clinical payloads. Cancellation is idempotent, revokes the lease, retains pending evidence and leaves completed extraction untouched. Completed review workflows cannot be cancelled. A provider request already in flight may still finish externally, but cannot commit graph artifacts after revocation. Do not delete checkpoints to retry a cancelled workflow; use the existing authorized document reprocessing path to create a new workflow after fixing the cause.

Rollback: restore the flag to `false` and restart workers after draining graph tasks. Saved review drafts and extraction evidence remain readable through the existing APIs. Do not switch a pending graph retry into the legacy route mid-workflow: drain or explicitly resolve outstanding tasks first.

Remaining operational work: worker-kill/checkpoint fault tests, cancellation/recovery controls, retention policy enforcement, bounded targeted repair, stage telemetry and accurate waiting/failed UI progress. Production rollout and patient-content transmission remain subject to their separate owner decisions.


New extraction workflows include a hashed data partition of document identity, uploader and provider policy/approval reference. Completed-stage replay checks source/configuration/partition before returning cached state. A changed model or approval partition requires a new workflow; a matching succeeded invocation can be reused only inside its original extraction and source digest. Local OCR reuse remains document-specific and requires current document SHA/extractor configuration. No provider cache crosses document ownership boundaries.

Checkpoint retention is implemented separately by `prune_prescription_checkpoints`, with explicit duration and dry-run default; see prescription-workflow-state-design.md. No production cleanup schedule is enabled.


Retry ownership: Celery schedules quota delays and one configured structured-output recovery with the changed prompt; the graph checkpoints and routes stages without sleeping. Retry delivery retains the same task/workflow identity. Generic task exceptions have the existing bounded Celery backoff; quota/structured-output/lease exceptions are excluded from that generic wrapper. Quota exhaustion completes a usable local-evidence exception draft without another call. Configuration/authentication/transient-provider classification improvements and targeted field repair are separate unfinished tasks; structured recovery is not advertised as targeted repair.
