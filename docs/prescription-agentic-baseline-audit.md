# P0.1 — Prescription pipeline baseline audit

Completed: 2026-10-01 (Asia/Dhaka)

Scope: repository code, local configured PostgreSQL database metadata and option counts, installed local venv, and existing automated checks. This is a baseline audit, not an implementation of the graph. No Gemini requests, migrations, catalog seeding, patient-record changes, or production deployments were performed. The Django test runner created and destroyed its separate test database.

## Result

The existing upload/review/publication system is a usable foundation. Manual clinical intake and prescription publication already share transactional persistence. The missing work is a complete field contract, immutable fact-to-field mapping, exception-focused readiness, durable stage orchestration, and concurrency/quota coordination.

Existing checks pass, but they do not demonstrate clinical extraction accuracy or operational readiness for the proposed agent. Passing tests do not close the gaps listed below.

## Actual read and write paths

| Stage | Entry point / implementation | Reads | Writes and important behavior |
|---|---|---|---|
| Upload | `registry/prescriptions/api_views.py`, `PrescriptionDocumentViewSet.create` | Uploaded bytes and explicit optional patient ID | SHA-256 deduplication; document/file/upload owner. Patient ID is provided by caller; no inferred automatic association. |
| Queue direct extraction | `process`, `reprocess` actions; `registry/prescriptions/tasks.py` | Authorized document and status | Document becomes processing, Celery receives document ID. No row lock/revision check around queue admission. Reprocess protects published documents and retains existing review JSON. |
| Text/OCR | `registry/prescriptions/services/processing.py`, `extract_pages` | Original file | Embedded PDF text first; OCR when cleaned text is under 20 characters; page text/images/metadata. A new processing attempt deletes and recreates current document pages. |
| Deterministic facts | `services/text_analysis.py` and clinical extractors | Current pages and option data | In-memory evidence/candidates, chronology, warnings and field tracking; no clinical record creation. |
| Direct Gemini | `services/extraction.py`, `extract_structured_data` | Page-wise text, system instruction, explicit configured model/key | One `LLMInvocation` linked to the run, raw output/usage/provenance; provider enrichment. JSON MIME type is configured, but no provider response schema is supplied. |
| Draft normalization | `services/draft_schema.py`, `services/intake_draft.py` | Gemini output plus deterministic candidates | Canonical review-only JSON, observation/record temporary IDs and evidence references. Gemini observations and a deterministic legacy observation are both appended. |
| Option mapping | `services/option_resolver.py` | Option models and drug aliases | Resolution metadata: unique exact/normalized/code/approved-drug-alias matches select real IDs; fuzzy matches remain suggestions. Some scoped relationships are checked server-side. |
| Extraction storage | `services/processing.py` | Normalized result | Completed/failed `ExtractionRun`, canonical draft in `structured_data`, issue rows, document status. No clinical observations created by extraction. |
| Start review | `_start_review`, `start-review`, `entry-draft` actions | Latest completed extraction and its canonical draft | One `PrescriptionReview` per document; reviewed JSON is initialized once. Existing canonical reviews remain intact when new extraction output arrives. |
| Review save | `review` PATCH; `PrescriptionReviewUpdateSerializer` | Submitted full reviewed JSON | Shape/selected-option checks, patient synchronization, `in_review` status, leaf/collection change audit. Saves review JSON, not clinical observation rows. No expected revision or optimistic concurrency token. |
| Approval | `approve-review` action | Saved reviewed JSON | Checks readiness; sets approved/reviewer/time and change audit. No client revision binding or row lock for the approval operation. |
| Publication | `services/publish.py`, `publish_review` | Locked approved review and current option rows | Atomic shared canonical persistence; model `full_clean`; provenance; durable `(review, temp_id)` observation mapping; publication timestamps. Repeat publication returns existing observations. |
| Manual entry | `records/api_views.py`, `IntakeSubmissionView`; `records/services/intake.py` | Manual payload | Converts to the same canonical draft then calls `persist_canonical_draft`. Manual draft saves create draft clinical observations; manual published intake uses published status. |
| Batch submission | `PrescriptionBatchJobViewSet.create`; `services/batch.py` | Authorized ready-for-review documents and current extracted pages | Creates job/items/invocation audits, uploads JSONL, and creates provider batch synchronously in the web request. No clinical publication. |
| Batch sync | `sync` action, general Celery task, `sync_batch_job` | Provider batch status/output | Updates item/audit status and mutates the latest completed extraction's `structured_data`, raw response, model and prompt metadata. Existing review JSON is not automatically replaced. |
| Actual form | `PrescriptionCorrectionPage.tsx`, `LongitudinalDraftWorkspace.tsx`, `ObservationFormSections.tsx`, `ClinicalSectionFields.tsx`, `PatientFormSections.tsx` | Review draft and catalog | Local edited draft; save/approve/publish use the above APIs. Original option text is kept in resolution `raw_value` by recent UI changes; limited pathology aliases are applied for display and save. |

## Schema and completeness findings

- Three separate representations currently coexist: provider prompt/JSON validation, backend collection and option maps, and frontend `observationFieldSchema.ts`. There is no generated/parity-checked full field contract.
- `validate_extraction` validates top-level structure, patient evidence, observation temporal context, and forbidden provider IDs. It does not validate every clinical record's field names/types/evidence against the actual form schema.
- `validate_draft` validates draft structure, observation dates, evidence shape/reference membership, and patient existence. Clinical child date/required-field validation is largely deferred to model persistence. Evidence page numbers are positive but not checked against actual document page count or quoted source text.
- The clinical quality gate accepts any nonempty observation property other than `temporal_context`; it does not prove all source-supported clinical sections are represented.
- Metadata-only inspection of the three most recent local runs found pathology records using `histopathology` or `histology_term`/`specimen_site`, confirming field-name drift. No clinical values were printed or copied to this report.
- The recent pathology UI compatibility mapping is useful but frontend-specific. It does not provide complete backend normalization, conflict handling, or a disposition ledger.
- Unknown observation properties become unresolved items in normalization, but unfamiliar nested record fields can survive in `values` and later be ignored by persistence's explicit allowlists. Showing additional facts on screen does not account for their eventual storage/exclusion.
- Evidence references keep source text/page/confidence, but normalized evidence does not independently retain every original extracted scalar. Editable review JSON can also change evidence. Raw output lives in extraction/audit storage; there is no immutable field-level fact ID and reviewer-ownership layer yet.
- Deterministic and Gemini records are both retained without a general reconciliation/deduplication layer. Their legacy field names can differ from canonical fields.
- Patient extraction returns `gender`, whereas form/persistence options use `sex`. Patient selection fields do not use the same resolution/evidence display layer as clinical option fields.

Follow-up tasks: P1.1–P1.7, P2.4–P2.6, P5.1.

## Options and readiness findings

The local option registry has **53 distinct resources referenced by clinical `OPTION_FIELDS`; 30 are empty**. This count excludes patient-only vocabulary resources. Empty resources at audit time:

```text
ihc-cycle-results, ihc-cycles, ihc-staging-cycle-results, ihc-staging-cycles
irecist-new-lesions, irecist-non-target-lesions, irecist-response-results, irecist-target-lesions
lines-of-treatment, pathological-response-categories, progression-sites
radiotherapy-intents, radiotherapy-modalities, radiotherapy-sites
recist-new-lesions, recist-non-target-lesions, recist-response-results, recist-target-lesions
response-estimation-methods, surgery-lateralities, surgery-modalities
tnm-m, tnm-n, tnm-stages, tnm-t
treatment-drugs, treatment-modalities, treatment-protocol-drugs, treatment-protocols
tumor-regression-grades
```

- Catalog absence requires approved catalog administration or an explicit unresolved disposition; an agent cannot invent canonical rows or option IDs.
- Unique exact, normalized, approved drug alias, and ICD-10 matches already work; fuzzy suggestions do not auto-select.
- `resolve_draft_options` skips list/dictionary values; clinical multiselect extraction is not generally auto-resolved.
- Parent scopes are applied when parent resolution exists; unresolved parents do not uniformly suppress child suggestions. Final server validation checks several relationships, but the UI only filters selected dependencies and does not generally clear/revalidate child choices after parent changes.
- Existing server approval rejects unresolved items, records, and option resolutions. UI `recordReady` is weaker: required field presence plus whatever resolutions are already present. A populated controlled field with no resolution may appear ready locally and fail server approval.
- The UI still offers per-record `Mark validated` and does not provide a complete grouped exception resolution workflow.
- `OptionsCatalogAPIView` uses a cached version key and configured TTL (default 900 seconds), but no producer of `options-catalog:version` was found in the repository search. No catalog fingerprint/version is returned with a draft resolution. The settings inspected do not configure a shared Redis cache; the cache comment alone does not prove shared invalidation.
- A catalog request failure is not clearly distinguished from an empty catalog in the correction page: it passes `catalogQuery.data ?? {}` without rendering the catalog error.

Follow-up tasks: P2.1–P2.7, P4.1, P5.1–P5.5.

## State, retries, and concurrency findings

- No LangGraph orchestration/checkpoint integration was found in application source.
- Each `process_document` retry creates a new extraction run and repeats OCR/page replacement, deterministic extraction, and enrichment. There are no stage checkpoints or artifact reuse keys.
- Celery has bounded quota and output retries, but the quota countdown caps the provider delay at the configured maximum; provider `Retry-After` can therefore be shortened. There is no explicit project-wide daily/token budget.
- The task rate limit is configured (`1/m` locally) and the runbook asks for one extraction worker. This is not a shared quota ledger across multiple workers or the batch/web path.
- Generic Gemini failures are caught inside processing and fall back to deterministic review data. Authentication, outage, and malformed/blocked output are not comprehensively separated into actionable states.
- Failed extraction has no distinct durable `waiting for quota` stage. Exhausted quota retries mark the document failed.
- Process queue admission and reprocess admission are not serialized. Review PATCH reads before its transaction, with no locked revision check; approval/reopen/reject also have no shared optimistic revision mechanism.
- Publication itself locks the review and is retry-safe, but that does not prevent a concurrent stale review save from racing approval/publication. Published reviews can be reopened by the current reopen action, which only checks approved status and reason; immutable-publication policy needs an explicit guard.
- Batch output overwrites an existing completed extraction, so comments describing immutable extraction are stronger than the actual behavior. A batch item can be marked completed when no completed extraction run exists to receive its output; missing/unknown output rows are not reconciled into comprehensive job readiness.
- Batch sync has no per-job/item execution lease or row locks for concurrent ingestion; job completion does not communicate a complete/partial-failure distinction. Existing test coverage does not establish replay safety of this ingestion path.
- `LLMInvocation` is read-only through its admin, but its lifecycle is mutable in services and the model does not enforce append-only finished artifacts. Treat immutable evidence as a design requirement to implement, not an already proven database guarantee.

Follow-up tasks: P0.5, P1.5, P3.1–P3.8, P4.1–P4.6, P5.4, P5.6, P6.2.

## Permissions and operational inspection

- Prescription API requires authentication and restricts non-staff access to uploader, assigned reviewer, or completed reviewer. Staff/superusers have registry-wide document access. Batch visibility is submitter-or-staff.
- Source PDFs/page images are streamed through authorized APIs; deployment examples deny direct public prescription media paths. Actual reverse-proxy deployment was not inspected.
- Approval/publication permission is currently based on document access, not a separate approver role. Patient/records intake APIs use authentication, with broader registry-wide access; do not assume prescription ownership extends to all clinical endpoints.
- Local audit admin registration and `prescriptions.view_llminvocation` permission both exist. **Zero groups hold that audit permission**. Individual user grants/superuser access were not enumerated, so this does not mean nobody can view it.
- `ExtractionRun` is registered with generic editable admin. `PrescriptionBatchJob`, `PrescriptionBatchItem`, and `PrescriptionPublicationObservation` are not registered in admin.
- Runtime key/model/date-order configuration exists locally; no values or credentials were printed. Production provider/data classification and live AI Studio quota were not verified.
- Normal telemetry avoids printing clinical prompts/responses, but provider exception tracebacks and `str(exc)` stored in some errors can expose provider text. Data access and sanitized error rules need end-to-end verification.

Follow-up tasks: P0.2, P4.4–P4.6, P5.5–P5.6, P6.2, P6.5.

## Local runtime and migration verification

| Check | Result |
|---|---|
| Database engine | PostgreSQL |
| Prescriptions migrations | 0001–0007 applied, including 0006 publication identity and 0007 invocation audit |
| Options migrations | Through 0010 applied |
| Records migrations | Through 0008 applied |
| Invocation table/admin/view permission | Present |
| Installed LangGraph | 1.2.11 |
| Installed langgraph-checkpoint | 4.2.0 |
| Installed google-genai | 2.24.0 |
| Installed Django / Celery | 6.1.1 / 5.6.3 |
| Persistent checkpoint adapters | `langgraph-checkpoint-postgres` and `langgraph-checkpoint-sqlite` not installed |
| Dependency declaration | Root `requirements.txt` lists dependencies without version pins |
| Gemini SDK schema support | Local SDK supports `response_schema` and `response_json_schema`; application does not yet supply one |

Existing migrations were already applied before the audit; no migration was applied as part of P0.1. Earlier memory that 0007 was unapplied is superseded by this local verification. Production migration state remains unverified.

## Verification evidence

Commands run from `D:\Lung` unless a working directory is specified:

```powershell
.\venv\Scripts\python.exe registry\manage.py check
.\venv\Scripts\python.exe registry\manage.py showmigrations prescriptions options records
.\venv\Scripts\python.exe registry\manage.py makemigrations --check --dry-run
.\venv\Scripts\python.exe -m pip check
.\venv\Scripts\python.exe -m pip show langgraph langgraph-checkpoint langgraph-checkpoint-postgres langgraph-checkpoint-sqlite google-genai Django celery
.\venv\Scripts\python.exe registry\manage.py test prescriptions --noinput
# Working directory: D:\Lung\frontend
npm run test
npm run build
```

Results:

- Django system check: no issues.
- Migration dry-run: no changes detected.
- Package dependency check: no broken requirements.
- Existing prescription backend suite: **50 tests passed**; separate PostgreSQL test database created and destroyed.
- Existing frontend suite: **14 tests passed** across two test files.
- TypeScript and Vite production build: passed; existing large-chunk warning remains.
- Local no-network LangGraph smoke: typed `StateGraph` with in-memory checkpoint compiled and executed a deterministic node successfully. This proves local basic integration capability, not production durability.
- Read-only Django metadata queries confirmed database engine, invocation table/admin/permission, group grant count, clinical option counts, configured-setting presence, and recent payload key sets. No patient values or secrets included in output.

## Explicitly not verified in P0.1

- Live Gemini response quality, billing/data arrangement, project limits, or provider availability.
- Production deployment/migrations, active workers/broker health, proxy rules, or checkpoint infrastructure.
- Browser visual inspection or full manual reviewer journeys in this audit.
- Clinical ground-truth accuracy, field-specific release thresholds, or reviewer-time reduction.
- All concurrency/fault scenarios and batch ingestion correctness; these require targeted implementation and tests in subsequent tasks.

## Next task

**P0.2 — Establish provider/data handling rules.** Record allowed development/production data classes and enforce them at both direct and batch request boundaries before testing the new graph with patient documents. Use synthetic fixtures for graph development while production provider suitability is resolved.
