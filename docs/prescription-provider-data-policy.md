# P0.2 — Provider and outbound-data policy

Date: 2026-10-01 (Asia/Dhaka)

Status: development enforcement implemented and verified; production decision pending. P0.2 remains unchecked until the production acceptance criterion is resolved.

## Explicit enabled mode (updated 2026-10-02)

PRESCRIPTION_GEMINI_DATA_POLICY=enabled is supported following the deployment owner's explicit instruction to use the configured API for real-prescription testing with clinician review. It does not require billing, an input hash or a non-sensitive attestation. It does not claim provider terms or institutional requirements are satisfied. Disabled remains the default. The constrained synthetic mode below remains available as an alternative. Restart both Django and Celery after changing configuration.

## Constrained development policy

Gemini development inputs must be synthetic or explicitly reviewed as non-sensitive. Do not assume that deleting a name makes a real prescription non-sensitive: free text, dates, identifiers, unusual histories, contact details, and combinations of facts can still identify a patient.

Ordinary uploaded prescriptions have no outbound approval by default. OCR, deterministic extraction, review drafts, and existing local publication logic remain available. This policy controls outbound text, not local patient-record permissions.

The default `PRESCRIPTION_GEMINI_DATA_POLICY=disabled` prevents direct Gemini calls and batch input uploads. A configured API key/model does not grant transmission permission. This is a deliberate behavior change for existing installations after web/worker restart: until configured, Gemini enrichment is skipped and the draft records a `provider_data_policy` exception.

Development mode `approved_non_sensitive` requires both:

- A review reference in `PRESCRIPTION_GEMINI_DATA_APPROVAL_REFERENCE` documenting the fixture provenance and non-sensitive classification.
- The full lowercase SHA-256 digest of the exact page-wise outbound text in `PRESCRIPTION_GEMINI_APPROVED_INPUT_SHA256` (comma-separated).

The digest is computed over `build_contents(pages)` in `services/extraction.py`, including page headings and whitespace. It is not the uploaded file checksum. Changes to text/OCR require a new review and digest. Hashes are matching controls, not proof of de-identification; the reviewing operator owns classification.

Do not bulk-approve existing patient documents or treat all inputs as synthetic through an environment flag. A prompt instruction to redact identifiers is too late: its input would already have been transmitted.

## Configuration procedure

1. Create synthetic source text with invented identifiers and no real patient facts.
2. Run local extraction with transmission disabled.
3. Review the complete page-wise outbound input locally; document who reviewed it, when, and why it is non-sensitive. Keep real clinical content out of shared logs and this repository.
4. Calculate the SHA-256 digest locally using `sha256(build_contents(pages).encode('utf-8')).hexdigest()`.
5. Set the mode, review reference, and exact approved digests in the deployment's private environment. The existing explicit API key/model settings are also required.
6. Restart the web application and workers consistently. Remove approved digests to revoke future transmission; revocation does not erase content already submitted to a provider.

Example with placeholders only:

```dotenv
PRESCRIPTION_GEMINI_DATA_POLICY=approved_non_sensitive
PRESCRIPTION_GEMINI_DATA_APPROVAL_REFERENCE=synthetic-fixture-review-2026-10-01
PRESCRIPTION_GEMINI_APPROVED_INPUT_SHA256=<full-lowercase-sha256-of-reviewed-outbound-text>
```

Unknown modes, malformed digest lists, missing review references, and unapproved text fail closed. Actual production patient processing is not enabled by this mode.

## Enforcement points

- `services/provider_data_policy.py` implements the common input guard.
- Direct: `extract_structured_data` checks the exact input before constructing the provider client. A blocked attempt finishes its restricted local invocation audit as skipped.
- Processing: a policy block retains deterministic extraction and canonical draft, records `gemini_status=policy_blocked`, and adds a specific unresolved decision. It does not schedule a quota/output retry.
- Batch: each prepared request checks the same exact-input policy before any job/audit creation, provider client construction, or file upload. One unapproved input blocks the entire batch; the API returns a structured policy error.
- Existing batch synchronization only retrieves previously submitted results; this gate does not retroactively cancel provider jobs or delete provider-held files.
- Future graph repair nodes must use this shared guard on their exact outbound input. Their truncated/reformatted source input may have a different digest and must not bypass classification.

## Provider facts and production decision

The current [Gemini API terms](https://ai.google.dev/gemini-api/terms) distinguish unpaid and paid services. Unpaid-service inputs/outputs may be used for product/model improvement and reviewed by people; the terms instruct users not to submit sensitive, confidential, or personal information. Paid-service data handling differs, but an active billing arrangement alone does not establish suitability for this use case. The same terms separately restrict clinical-practice use, medical advice, and regulated medical-device use.

Production disposition is **pending**. The owner must establish:

- Intended purpose: research/administrative registry abstraction versus use in clinical practice, advice, or treatment decisions.
- Provider/service and contractual arrangement permitted for that purpose and data class, including relevant retention, processing location, access, and institutional approval.
- Whether data sent is synthetic, genuinely non-sensitive, or patient-sensitive, and which reviewed classification process supports that decision.

No paid/sensitive mode is implemented until this decision is resolved. If the selected service is unsuitable, use another suitable provider or local processing while retaining the same field contract and review workflow.

## Verification

The no-network backend suite covers default denial before client construction, skipped direct audit, no batch artifacts/uploads on denial, exact-input matching, malformed configuration, a mixed approved/unapproved batch, approved synthetic direct requests through a mock, and preservation of local extraction/drafts.

Verification results:

- `D:\Lung\venv\Scripts\python.exe registry\manage.py test prescriptions --noinput`: 57 tests passed (initial seven policy cases plus existing 50 cases).
- After adding positive batch and API-denial cases, `D:\Lung\venv\Scripts\python.exe registry\manage.py test prescriptions.test_provider_data_policy --noinput`: all nine policy cases passed.
- Django system check: no issues; migration dry-run: no changes detected.
- Frontend TypeScript/Vite production build: passed, with the existing large-chunk warning.
- Fresh-process settings inspection: effective policy disabled; no approval reference or approved digests configured. No private `.env` was edited.
- Provider calls were mocked throughout. No real document text was transmitted, no production workers restarted, and no database migration was needed.

The UI now reports a policy block as such, instead of saying Gemini returned no clinical observations. No production purpose or contract suitability has been verified.
