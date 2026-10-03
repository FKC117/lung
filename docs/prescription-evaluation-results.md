# Synthetic evaluation evidence and remaining clinical measurements

Recorded 2026-10-02, Asia/Dhaka. Reproduce with `D:\Lung\venv\Scripts\python.exe D:\Lung\registry\manage.py evaluate_prescription_fixtures --shadow`. Detailed per-case/per-field results are in prescription-synthetic-shadow-results.json.

Ten hand-annotated engineering cases cover canonical/legacy pathology, narrative preservation, alias conflict, ambiguous dates, repeated administrations, empty catalog text, unsupported fields, invented evidence and uploaded instruction injection. Eleven expected field values and nineteen source facts pass accounting checks. Six annotated field categories have no observed omission or wrong value on this small fixture set. All ten read-only graph outputs match the shared-service baseline after generated identities are normalized with references preserved.

These outcomes establish mapping/source-check behavior for committed synthetic payloads. They do not measure Gemini extraction accuracy, actual OCR accuracy (the scan boundary fixture mocks OCR), current catalog auto-selection accuracy, reviewer time/corrections, or production failure/call rates. Catalog resolution is disabled deliberately so evaluation is reproducible and reads no production database. Zero provider calls and zero clinical writes describe this runner only. Exception counts are reported individually, not interpreted as observed reviewer burden.

## Required clinical baseline before P6.1 acceptance

The clinical owner must approve a representative truth set and field/risk thresholds. For each approved case record expected facts, original supporting source, canonical mapping/expected exceptions, actual field outcomes, omitted facts, incorrect selections, reviewer changes, elapsed review time, provider calls and observed recoveries. Report results per field and case; retain failed cases for investigation.

| Measurement | Current evidence | Required release decision/evidence |
| --- | --- | --- |
| Supported field prefill | Synthetic eleven-value pass | Field-specific clinical truth set and threshold |
| Fact omissions | Nineteen synthetic facts accounted | Independently annotated source facts, not provider-returned facts alone |
| Incorrect automatic selections | Separate resolver regression tests | Approved catalog and measured selection error rate |
| Reviewer corrections/time | Unmeasured | Agreed baseline and observed comparison |
| Calls/document | Runner makes none | Recorded invocation counts for approved provider trials |
| Recovery failure rate | Isolated fault regression tests | Deployment worker/broker rehearsal and observed pilot results |

No invented IDs, unauthorized writes or duplicate publication are permitted in engineering fault tests. Clinical thresholds and production provider/data permissions remain unapproved; P0.4 and P6.1 stay open. No production pilot is authorized by this report.
