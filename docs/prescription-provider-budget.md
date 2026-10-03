# Shared provider admission budget

Implemented 2026-10-02; owner-reported active limits configured and verified 2026-10-03.

Direct generation and batch submission reserve against one PostgreSQL row per
configured project scope/model. Row locking serializes admission across workers.
Batch items count individually. Reservations happen after the provider data-policy
gate and before provider clients/upload. Failed or ambiguous external attempts keep
their reservation, conservatively. No request content or API key is stored in the
budget row. Django admin exposes counters through read-only view permissions.

Configure `PRESCRIPTION_PROVIDER_BUDGET_ENABLED=true`, a non-secret project
`PRESCRIPTION_PROVIDER_BUDGET_SCOPE`, positive `WINDOW_SECONDS`, and at least one
of `REQUESTS` or `TOKEN_UNITS` (all names prefixed `PRESCRIPTION_PROVIDER_BUDGET_`).
Zero disables that limit. Invalid enabled configuration fails closed. Defaults
leave admission budgeting disabled; the separate provider data policy still applies.

The window starts at its first reservation. These are configured application
budgets, not hardcoded Gemini free-tier quotas, provider daily-reset semantics,
or provider-measured token counts. Token admission units conservatively include
UTF-8 input/instruction bytes plus a configured output cap. Token budgeting
requires positive `PRESCRIPTION_PROVIDER_MAX_OUTPUT_TOKENS`, enforced in both
provider request configurations. Actual usage remains in LLMInvocation auditing.
The estimate may over-reserve; calibrate against reviewed provider settings before
a pilot. Daily requests are also reserved atomically under PRESCRIPTION_PROVIDER_BUDGET_DAILY_REQUESTS (zero disables it). The calendar reset uses PRESCRIPTION_PROVIDER_BUDGET_DAILY_TIMEZONE, default America/Los_Angeles, matching Gemini Pacific midnight. Day exhaustion rolls back minute admission. New day counters conservatively include existing non-skipped model audits. Provider usage from other applications is not visible here.

Temporary exhaustion raises a quota error with the remaining window time. Celery
honors that local wait without shortening it to its ordinary provider backoff cap.
Batch API admission returns HTTP 429 and Retry-After without creating a batch.
An individual request/batch larger than the entire window returns a configuration
error rather than repeatedly waiting. Do not clear counters to evade a provider
quota. Migration `0010_prescriptionproviderbudget` is required and applied locally.

P4.1 accepted 2026-10-03: owner reported 15 RPM/500 RPD/250K TPM, deployed settings and local worker health verified, isolated direct/batch admission and concurrent-worker tests pass. verify_prescription_admission checks actual configured caps in rolled-back synthetic scopes without provider calls. No counters are cleared or provider usage is represented as known.
