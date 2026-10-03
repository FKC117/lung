# Prescription release gate record

Status as of 2026-10-03 (Asia/Dhaka): the owner explicitly authorized real uploaded prescriptions through the existing unpaid Gemini API, with clinician validation, and declined billing. Current testing is enabled. Final production/pilot release remains unapproved; successful service tests are not a clinical accuracy assessment.

| Gate | Required concrete evidence | Current state |
| --- | --- | --- |
| P0.2 Provider/data | Provider arrangement, permitted content class, responsible approver and enforced production policy | Explicit enabled policy and owner-selected unpaid real-prescription testing recorded; broader release data decision remains open |
| P0.4 Clinical thresholds | Reviewed representative truth set and per-field/risk thresholds; observed correction/time baseline | Accepted strict clinician-reviewed release thresholds on 2026-10-03; metric definitions recorded, observed baseline/results remain P6.1 |
| P4.1 Quota deployment | Verified project/model limits, application scope/window/request/token-unit/output configuration, verifying operator | Accepted: owner-reported 15 RPM / 500 RPD / 250K TPM configured; minute/day denial, rollback and worker health verified; token admission is conservative |
| P6.1 Evaluation | Field-level omissions, incorrect auto-selections, corrections/time and provider calls against agreed clinical gates | Synthetic metrics and two real provider responses available; clinician accuracy/correction/time measurements pending |
| P6.4 Pilot | Named clinical/operator owners, approved cohort/content, rollout/rollback plan, worker/broker recovery rehearsal and agreed gate results | Rollback regression and actual isolated queue/restart/replay pass; one local worker ready; clinical pilot gates pending |
| P6.6 Final release | Explicit attributable final review of preceding gates, known limitations and provider policy approval | Unapproved |

Record named clinical, data/privacy, deployment, catalog and maintenance owners using prescription-deployment-ownership.md. Record retention duration and responsible backup/deletion operator. The selected enabled policy supports the owner-authorized current test scope; exact-input allowlisting remains a separate optional policy. Production release decisions and institutional suitability are not inferred from API configuration or passing tests. No billing gate is imposed by this application.

Provider model remains explicitly configured, not guessed. Do not supply credentials in this record. Do not clear budget/checkpoint data to manufacture permission or quota. Keep final human approval bound to the saved review revision and canonical publication atomic.

Engineering evidence: prescription-synthetic-shadow-results.json, prescription-evaluation-results.md, prescription-stage-audit.md, prescription-recovery-runbook.md and the task tracker's completion log. Named approvals and deployment trials cannot be inferred from passing local tests.
