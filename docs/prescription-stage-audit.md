# Prescription stage and invocation auditing

Extraction, mapping and targeted repair graph nodes record lease-fenced stage starts and success/failure outcomes in the existing workflow version metadata. Each replay appends a separate attempt with timestamps. Stage records contain only allowlisted stage names, status and bounded failure category; they never contain source snippets, draft values, prompts, responses or exception messages.

A crash before completion leaves an honest running/interrupted stage entry. This does not imply the worker is still active: inspect the current workflow status and lease using the recovery runbook. A reclaimed or cancelled worker cannot complete its old audit entry. Checkpoint recovery and successful invocation reuse continue to prevent unnecessary redispatch.

LLMInvocation remains the restricted immutable prompt/input/output and usage audit. Direct, batch and repair failures retain available response content there; error fields use sanitized categories. Exact failed/truncated output cannot enter canonical drafts merely because it was recorded. Usage is unavailable when the provider supplies none, rather than invented. Batch submission errors never include provider exception messages in job metadata or chained task exceptions.

No model or migration was added. Existing read-only searchable workflow/invocation administration and explicit view permissions govern access. Operational status continues to expose only its existing whitelist.
