# Evaluation fixtures and release gates

Date: 2026-10-01 (Asia/Dhaka)

The versioned synthetic corpus is `registry/prescriptions/evaluation/corpus.py`. Cases are hand-annotated and reviewed for engineering consistency: expected mappings, source quotes/pages, retained repeated events, prohibited inferences, and exception categories. It contains no real patient document or real identifiers. Text PDFs and raster scans are generated temporarily in tests; OCR routing is verified with a controlled OCR result. Real scanner/OCR quality and clinician-certified ground truth remain production evaluation work.

## Measurements

- Fact accounting: returned leaf facts with mapped, unresolved, or explicitly excluded dispositions / all returned facts.
- Prefill accuracy: correctly populated expected fields / populated expected fields, reported separately for each collection and controlled/text/date/number field class.
- Recall: correctly represented supported gold facts / supported gold facts, including exceptions when a value cannot be safely normalized.
- Incorrect auto-selection: selected canonical options that differ from reviewed gold options / auto-selected options.
- Reviewer burden: number of exception decisions and edited fields; median and p95 active review seconds. Automated tests measure decisions, not human reading time.
- Provider usage: attempted and successful extraction/repair calls, input/output tokens, retries and quota wait duration per document revision.
- Reliability: duplicate local writes, stale-revision approvals, preserved reviewer edits, crash recovery, policy denials and unauthorized access.

## Development acceptance gates (delegated engineering defaults)

- Synthetic corpus: 100% expected mappings and expected exceptions; 100% returned fact accounting; zero invented canonical IDs or patient assignments.
- Controlled option tests: zero incorrect automatic choices, including ambiguity and wrong-parent cases. Fuzzy candidates stay suggestions.
- Evidence: zero accepted facts with nonexistent page or unsupported quote in the evidence test suite.
- Durability/security: zero duplicate clinical writes, stale approvals, protected reviewer overwrites, unapproved outbound calls, or unauthorized artifact access in fault tests.
- Budget: at most one extraction and one targeted repair per new document revision by default; provider/transient retry allowances are separately bounded and reported, never hidden in success counts.
- Routine review: zero required per-record validation clicks for records accepted by current server validation.

## Production gates remain provisional

Do not infer clinical safety from a small synthetic corpus. Before pilot activation, obtain an independent reviewed representative set and approve field-specific thresholds and sample sizes, particularly dates, option choice, administered/planned treatment, patient identity and conflicting diagnoses. Inspect every critical error regardless of aggregate scores. Provider purpose/data arrangements from P0.2 and pilot authorization remain prerequisites.

Run shadow mode and compare corrected facts, exception decisions, and reviewer time against the original workflow. Proposed benefit gate: fewer correction decisions with no increase in critical errors. Record actual time measurements before setting a numerical reviewer-time target. No current claim of clinical accuracy or time savings is made.

## Owner-accepted clinical pass rule - 2026-10-03

The owner selected the strict rule: 100% source-fact accounting; correct every incorrect or missing clinical field; publish zero unresolved patient/date/pathology/treatment/dose/stage errors; clinician validates every saved draft. The gate evaluates reviewed, corrected records rather than asserting that unreviewed Gemini suggestions are error-free. All field/risk classes require correction when wrong or missing; critical classes permit zero unresolved published errors. Field-level raw prefill accuracy/recall/selection errors, correction count and active review time remain separately reported; no observed accuracy or performance result is claimed yet. No minimum raw-provider accuracy or numeric time-saving cutoff is invented.

P0.4 is accepted for definitions/criteria. P6.1 still requires the actual reviewed cohort and measurements. This decision approves no patient record and does not activate a general production pilot/release.
