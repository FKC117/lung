# Prescription workflow recovery

Run commands from `D:\Lung` with `.\venv\Scripts\python.exe registry\manage.py`. Operator access to the host is required; no public checkpoint or repair payload endpoint is added. Never paste patient source, prompts, keys or responses into terminal logs or incident reports.

## Inspect progress

`prescription_workflow status WORKFLOW_UUID` prints only workflow/document/extraction IDs, queued/running/waiting_provider/failed/needs_review/ready status, lease timing, stage completion flags, invocation status counts and reserved budget counters. Queued means work was admitted to scheduling; it does not promise broker delivery or completion. Needs-review means a saved review/proposal awaits decisions; it is not approval or publication.

## Quota waiting and provider failure

Allow Celery to own the original delayed retry. Retry-After is honored; unguided waits use bounded exponential delay with jitter. Do not manually shorten quota waits or create another workflow to bypass document/project limits. Authentication, configuration and explicit daily exhaustion retain a local-evidence exception draft and need provider/operator correction, not repeated dispatch. Inspect restricted invocation status with the explicit audit permission, using sanitized categories only.

## Failed extraction and restart

For an unleased failed extraction with unchanged document/version/configuration, use `prescription_workflow resume WORKFLOW_UUID`. The graph feature must be enabled. This queues the original identity and reuses checkpoints/OCR/audited answers; it does not reset budgets. The resume task owns bounded quota and structured-output recovery. At exhaustion it finishes an exception draft from local evidence. Running, completed, cancelled and scheduled quota-wait workflows cannot use this shortcut. An unavailable broker rolls back the queued-state change.

After a worker interruption, retain the database and artifacts, inspect the lease and wait for expiry before retrying the same identity. Never clear counters or delete checkpoints to manufacture another allowance. A changed source/model/approved-data partition requires investigation and an explicit new plan; this control does not waive source checks.

## Mapping and repair recovery

Existing `map_prescription_workflow` accepts the original mapping workflow UUID and has no provider or publication node. The internal `repair_prescription_section` task accepts the saved review, stable record and bounded source sections. Requeue only the original repair request: completed audited answers resume storage; uncertain running/failed provider attempts remain exceptions and do not automatically redispatch. Changed saved revisions, reviewer-owned values and approved/published reviews are protected. Repair proposals never automatically overwrite the canonical review. See prescription-targeted-repair.md for configuration and admission requirements.

## Cancel

`prescription_workflow cancel WORKFLOW_UUID` revokes the lease so an old worker cannot commit. Pending evidence remains; completed review workflows cannot be cancelled. Cancellation is not deletion, a publication rollback or a quota refund. Already published provenance is immutable.

## Catalog corrections

Use authorized options administration and explicitly approved drug aliases as described in prescription-catalog-corrections.md. Reload the form, explicitly choose a valid scoped option, save successfully and approve the saved revision. Do not insert guessed IDs or treat pending aliases as rules.

## Feature rollback and retention

Disable `PRESCRIPTION_REPAIR_ENABLED` and `PRESCRIPTION_AGENTIC_EXTRACTION_ENABLED` in the deployment configuration, then restart/drain the corresponding workers through the deployment process. New extraction uses the existing route; preserve current drafts, source/provenance, invocations and workflow/checkpoint rows. Do not disable the independent provider-data policy. Already scheduled graph work requires inspection/cancellation when safe; turning off a flag does not undo published records.

Checkpoint retention defaults off. Use `prune_prescription_checkpoints --retention-days DAYS` for a dry run; only append `--apply` under the agreed retention policy. Active/unpublished review checkpoints and immutable repair request/proposal evidence are protected. Keep source extraction, review, audit and publication data. Production retention duration and clinical/provider pilot decisions remain owner release gates.
