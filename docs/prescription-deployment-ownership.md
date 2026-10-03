# Prescription deployment and ownership

Prepared 2026-10-02, Asia/Dhaka. This is release preparation; production activation is pending owner decisions. No deployment configuration has been changed.

## Runtime and verification

The tested local runtime versions are recorded in requirements-prescription-constraints.txt. Reproduce core versions using `python -m pip install -r requirements.txt -c requirements-prescription-constraints.txt` in a clean deployment environment, then `python -m pip check`. This constraints file pins the orchestration/SDK/database/core framework packages, not every transitive dependency. Record the deployment image/version separately. Local verification does not establish deployment OS/worker compatibility.

From D:\Lung, run `.\venv\Scripts\python.exe registry\manage.py check`, `... manage.py makemigrations --check --dry-run`, and `... manage.py test prescriptions --noinput` against an isolated test database. In D:\Lung\frontend run `npm ci`, the frontend test script and `npm run build`. The existing large bundle warning remains a performance limitation.

## Database and checkpoints

Use the same PostgreSQL database for Django reviews, workflow leases, durable DjangoCheckpointSaver state and project/model quota rows. Memory checkpoints are only used by the synthetic no-write shadow runner. Back up the database and protected source media using the deployment's existing backup process before migrations.

Review `showmigrations prescriptions`, then apply approved migrations with `migrate`. Required prescription migrations include 0007 invocation auditing, 0008 workflow checkpoints, 0009 saved revisions and 0010 provider budget. They were applied locally; verify the actual deployment independently. No additional migration was introduced for stage auditing. Never drop checkpoint, review or immutable provenance tables during rollback.

## Provider configuration and release boundaries

Keep model choice explicit through PRESCRIPTION_EXTRACTION_MODEL and credentials in the deployment secret store. Do not copy a hardcoded model or print GOOGLE_API_KEY. Source content transmission remains independently gated by PRESCRIPTION_GEMINI_DATA_POLICY, approval reference and exact approved input hashes. The current policy supports disabled or explicitly approved non-sensitive inputs; a production patient-data arrangement needs owner approval and suitable enforcement before activation.

PRESCRIPTION_PROVIDER_BUDGET_SCOPE must identify the shared provider project; all processes using that project must share the admission database and configuration. Set WINDOW_SECONDS, REQUESTS, TOKEN_UNITS and PROVIDER_MAX_OUTPUT_TOKENS from verified project settings and conservative admission estimates. Units are input/prompt/schema bytes plus output cap, not measured billed tokens. Record observed provider limits and the verifying operator; no free-tier values are assumed. Calls from other applications are outside this coordinator.

PRESCRIPTION_DOCUMENT_BUDGET_ENABLED and PRESCRIPTION_REPAIR_ENABLED require explicit positive attempt/token-unit/seconds limits and output caps. Keep repair and agentic extraction disabled until the release gates pass. PRESCRIPTION_DATE_ORDER must reflect the confirmed source convention; leave ambiguous dates unresolved otherwise.

## Worker startup and recovery

Run workers from the registry directory so the registry Celery application resolves. A Windows synthetic development worker can use `..\venv\Scripts\python.exe -m celery -A registry worker -Q prescription_extraction --pool=solo --concurrency=1 --loglevel=INFO`. For a supported production host use the supervised Celery worker configuration, queue from PRESCRIPTION_EXTRACTION_QUEUE and appropriate tested pool. Windows solo verification does not prove production process concurrency.

Ensure Redis broker connectivity before dispatch; do not log broker URLs containing credentials. Route prescription work separately, keep prefetch conservative and configure soft/hard worker timeouts to include local OCR plus bounded provider execution. A provider deadline does not bound all local OCR work. Queue presence is not proof of broker delivery.

Use prescription-recovery-runbook.md for status, delayed quotas, same-identity resume, cancellation, restart and rollback. Complete invocation and stage evidence remains restricted. Process-kill/broker recovery on the deployment host must be rehearsed before pilot; isolated tests verify database concurrency and replay semantics.

## Permissions and retention

Assign only required prescription document/review permissions. Invocation inspection requires prescriptions.view_llminvocation; operational workflow/checkpoint/budget view permissions belong to administrators handling incidents. Existing admin records are searchable and read-only where operational immutability applies. Alias proposals require separate explicit authorized approval before automatic matching.

PRESCRIPTION_CHECKPOINT_RETENTION_DAYS defaults to zero (disabled). Agree retention, backups and deletion responsibilities before setting it. `prune_prescription_checkpoints --retention-days DAYS` is dry-run by default; `--apply` is an approved operational action. Active/unpublished workflows and immutable repair request/proposal artifacts remain protected. Source, extraction, review, invocation and published provenance require their own clinical retention policy.

## Responsible roles and open assignments

| Role | Responsibility | Assignment |
| --- | --- | --- |
| Clinical registry owner | Field/risk thresholds, reviewed truth set, patient identity/date convention, pilot cohort and final release acceptance | Owner nomination pending |
| Data/privacy owner | Permitted content class, provider arrangement, access and retention approval | Owner nomination pending |
| Deployment operator | Runtime/image, migrations/backups, Redis/Celery, verified quota settings, restart/rollback rehearsal | Owner nomination pending |
| Catalog administrator | Scoped canonical options and explicit alias approval | Authorized existing administrator; named owner pending |
| Application maintainer | Contract, shared persistence, regression tests, incident fixes and release evidence | Maintainer nomination pending |

These role responsibilities are documented; named personnel, approvals and production values remain open release decisions. Do not treat an unassigned role as approved.

## Final release checklist

Production provider/data policy (P0.2), agreed measured clinical gates (P0.4/P6.1), verified project quota settings (P4.1), named owners/retention, deployment worker recovery rehearsal, limited pilot (P6.4) and explicit final release review (P6.6) remain pending. Synthetic results in prescription-synthetic-shadow-results.json demonstrate engineering fixture parity only. Final human approval of the saved revision remains required for publication.
