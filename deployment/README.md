# Production prescription media

Prescription PDFs and rendered page images contain patient data. They must
never be exposed by a web server's general `MEDIA_ROOT` mapping.

The application exposes these files only through authenticated, authorized
API actions:

- `/api/prescriptions/documents/<document_id>/source-file/`
- `/api/prescriptions/documents/<document_id>/pages/<page_id>/image/`

Non-staff access is limited to the uploader or an assigned/completed reviewer.
Staff and superusers retain registry-wide access. The API deliberately returns
API URLs instead of raw `/media/` URLs.

## Required reverse-proxy rule

Use the applicable checked-in example:

- [`nginx.conf.example`](nginx.conf.example)
- [`apache.conf.example`](apache.conf.example)

The denial must cover both paths before or in addition to the general media
mapping:

- `/media/prescriptions/`
- `/media/prescription_pages/`

Do not replace these rules with `X-Accel-Redirect`, `X-Sendfile`, or a public
object-storage URL unless the replacement preserves the same per-request API
authorization. If prescription media is moved to object storage, use private
objects and short-lived URLs issued only after the API authorization check.

## Deployment verification

1. Test the server configuration before reload:
   - Nginx: `sudo nginx -t`
   - Apache: `sudo apachectl configtest`
2. Reload the web server.
3. Verify both direct paths return `403` or `404`, even with a valid application
   session:
   - `curl -I https://registry.example.org/media/prescriptions/test.pdf`
   - `curl -I https://registry.example.org/media/prescription_pages/test.png`
4. Verify an unauthorized account receives `404` from each API file endpoint.
5. Verify the uploader, assigned reviewer, or staff user can retrieve the same
   file through its API endpoint.

The Django URL denial remains as defense in depth for development and any
deployment that routes media requests through Django. It does not replace the
Nginx or Apache rule.

## Gemini free-tier extraction worker

Before enabling outbound Gemini traffic, configure the [provider data policy](../docs/prescription-provider-data-policy.md). Transmission defaults to disabled. The explicit enabled mode supports owner-selected real-prescription testing; approved_non_sensitive separately supports reviewed exact-input fixtures. Configuring an API key alone does not select a data policy. Apply the same environment to web and workers and restart both after configuration changes. Existing submitted provider batches are not canceled by this gate.

Prescription extraction has its own Celery queue, `prescription_extraction`.
Run exactly one worker for that queue while the project uses Gemini's free tier:

```powershell
python.exe -m celery -A registry worker --loglevel=INFO --pool=solo --concurrency=1 --queues=prescription_extraction --hostname=prescription-extraction@%h
```

This makes uploads wait in Redis and processes a single prescription at a time.
The task is additionally rate-limited by `PRESCRIPTION_GEMINI_RATE_LIMIT`
(default `1/m`) and retries Gemini `429 RESOURCE_EXHAUSTED` responses with
bounded exponential backoff. Do not run a second worker consuming this queue
unless you have deliberately raised the configured Gemini capacity.

Run a separate general worker for non-extraction Celery tasks, such as Gemini
batch-job polling:

```powershell
python.exe -m celery -A registry worker --loglevel=INFO --pool=solo --concurrency=1 --queues=celery --hostname=registry-general@%h
```

The queue name, rate limit, retry count, and backoff are environment settings.
Set them according to the active limits shown for this project in Google AI
Studio; do not hard-code a provider quota into application code.
# Shared prescription provider admission

Apply `prescriptions.0010_prescriptionproviderbudget` before enabling the shared
admission guard. Configure project/model limits explicitly; do not infer them
from a free-tier label. See [provider budget runbook](../docs/prescription-provider-budget.md).
Keep provider data-policy approval separate from budget configuration.

## Local Windows startup and verification

From D:\Lung, run `./deployment/start-prescription-worker.ps1` to retain the existing Ubuntu Redis runtime and start one hidden solo extraction worker. It checks for an existing consumer before starting another. Worker logs/process metadata are under the ignored registry/logs directory. The script does not install Redis, change network/security settings, modify credentials or configure billing.

`./venv/Scripts/python.exe registry/manage.py verify_prescription_admission` checks configured request/token-unit/day denials in rolled-back synthetic scopes without provider calls. Local limits were supplied by the owner: 15 RPM, 500 RPD, 250K TPM; token admission intentionally overestimates usage. The daily counter resets at Pacific midnight. Restart web and workers after environment changes.

For a stale processing row with newer completed evidence and no runnable workflow, use `reconcile_prescription_state DOCUMENT_ID` for a dry run. Only add `--apply` after inspection; the command protects recent processing and newer pending runs, retains original structured evidence, and does not alter a review or dispatch a provider call.
