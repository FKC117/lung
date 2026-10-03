# Clinician validation of the prescription workflow

Prepared 2026-10-03. Current test arrangement: owner-selected real prescriptions, existing unpaid Gemini API, no billing change. This checklist records actual results; it does not certify clinical accuracy in advance.

## Open the actual form

1. Open http://localhost:5173/prescriptions and sign in with the existing account.
2. Choose Continue review. For the two older untouched drafts (document IDs 22 and 23), click Load latest extraction once. The previous draft is retained in the server review history. Newly processed documents start from their current extraction automatically.
3. Compare the source prescription on the left with each form section. Extracted wording remains visible even when a dropdown option is missing or different. Select a valid catalog option where required; do not invent IDs.
4. Correct wrong or missing values. Resolve each source-fact exception with a supported correction or an explained exclusion. Patient selection remains explicit.
5. Save draft. The clinician checks the saved revision before approval; publishing is a separate action. A test does not require publishing a patient record.

## Record a result for each test document

Keep source quotations and identifiable clinical details inside the authorized application; do not paste them into this repository or a chat report.

| Document ID | Clinician review completed | Supported facts expected | Prefilled correctly | Missing facts | Incorrect dropdown selections | Fields corrected | Active review minutes | Outcome |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 22 | Pending | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Pending |
| 23 | Pending | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Pending |

Inspect diagnosis, pathology and specimen/report dates, IHC/molecular findings, treatment names/doses/dates, surgery/radiotherapy, chronology and patient identity. Preserve explicitly historical/planned facts rather than treating them as current treatment. Extend the cohort with representative text PDFs and scans as supplied by the owner.

Owner-accepted pass rule (2026-10-03): account for every supported source fact; correct every wrong or missing clinical field; publish no unresolved patient/date/pathology/treatment/dose/stage error; clinician validates each saved draft. Measure prefill accuracy, omissions, wrong selections, corrections and active review time separately. No numerical accuracy or time-saving result is asserted until observed.

The final pilot/release review also records the responsible clinician/operator, intended deployment scope and operational retention decision. Local worker startup/replay verification has passed; a general production rollout is not inferred from it.
