import { useState } from "react";
import type { LongitudinalIntakeDraft } from "../../api";
import { exceptionValue } from "./draftExceptions";
import { observationCollections } from "./draftWorkspace";
import { originalValueText, type SourceFact } from "./sourceFacts";
import { patientFieldSchema } from "./observationFieldSchema";

type Fact = SourceFact & { reason: string };
type Decision = { fact_id: string; action: "reviewed" | "exclude"; reason: string };

function DecisionRow({ fact, decision, disabled, onRecord, onRemove }: {
  fact: Fact; decision?: Decision; disabled?: boolean; onRecord: (decision: Decision) => void; onRemove: () => void;
}) {
  const [action, setAction] = useState<Decision["action"]>(decision?.action ?? "reviewed");
  const [reason, setReason] = useState(decision?.reason ?? "");
  return <section className="panel entry-block">
    <strong>{fact.source_path.replaceAll("_", " ")}</strong>
    <p>Original extracted value: {exceptionValue(fact.raw_value)}</p><p>{fact.reason}</p>
    {decision ? <p>Recorded decision: {decision.action === "exclude" ? "Exclude" : "Reviewed"} — {decision.reason}</p> : null}
    <label className="filter-field"><span>Decision for {fact.source_path}</span><select className="filter-select" disabled={disabled} value={action} onChange={(event) => setAction(event.target.value as Decision["action"])}><option value="reviewed">Reviewed / corrected in form</option><option value="exclude">Exclude this source fact</option></select></label>
    <label className="filter-field"><span>Reason for {fact.source_path}</span><textarea className="auth-input entry-textarea" disabled={disabled} value={reason} onChange={(event) => setReason(event.target.value)} /></label>
    <button type="button" className="secondary-button" disabled={disabled || !reason.trim()} onClick={() => onRecord({ fact_id: fact.fact_id, action, reason: reason.trim() })}>Record decision</button>
    {decision ? <button type="button" className="text-button" disabled={disabled} onClick={onRemove}>Remove decision</button> : null}
  </section>;
}

export function FactDecisionPanel({ draft, disabled, onChange }: { draft: LongitudinalIntakeDraft; disabled?: boolean; onChange: (draft: LongitudinalIntakeDraft) => void }) {
  const facts = (Array.isArray(draft.source_facts) ? draft.source_facts : []) as Fact[];
  const decisions = (Array.isArray(draft.fact_decisions) ? draft.fact_decisions : []) as Decision[];
  const unresolved = facts.filter((fact) => {
    if (fact.disposition === "excluded") return false;
    if (fact.disposition === "unresolved") return true;
    if (!fact.canonical_field) return false;
    if (!fact.record_temp_id) {
      if (originalValueText(fact.raw_value) === "Not supplied") return false;
      if (fact.source_path.startsWith("patient.")) {
        const value = draft.patient.values[fact.canonical_field];
        const field = patientFieldSchema.find((item) => item.key === fact.canonical_field);
        return value == null || value === "" || Boolean(field?.resource && typeof value !== "number");
      }
      const observation = draft.observations.find((item) => item.temp_id === fact.observation_temp_id);
      if (!observation) return true;
      const values = fact.source_path.includes(".anthropometry.") ? observation.anthropometry : observation;
      const value = values && (values as unknown as Record<string, unknown>)[fact.canonical_field];
      return value == null || value === "";
    }
    if (!fact.collection) return false;
    const collection = observationCollections.find((key) => key === fact.collection);
    if (!collection) return false;
    const record = draft.observations.flatMap((observation) => observation[collection]).find((item) => item.temp_id === fact.record_temp_id);
    if (!record) return true;
    if (originalValueText(fact.raw_value) !== "Not supplied" && (record.values[fact.canonical_field] == null || record.values[fact.canonical_field] === "")) return true;
    const status = record.resolutions[fact.canonical_field]?.status;
    return status === "unresolved" || status === "ambiguous";
  });
  if (!unresolved.length) return null;
  return <details className="clinical-unresolved"><summary>Source fact decisions · {unresolved.length}</summary>
    <p>Correct or clear the actual form first, then record your decision. Decisions are checked when you save and retain the original evidence. Other issues and patient confirmation may still need your attention.</p>
    {unresolved.map((fact) => <DecisionRow key={`${draft.document_id}:${fact.fact_id}`} fact={fact} decision={decisions.find((item) => item.fact_id === fact.fact_id)} disabled={disabled}
      onRecord={(decision) => onChange({ ...draft, fact_decisions: [...decisions.filter((item) => item.fact_id !== fact.fact_id), decision] })}
      onRemove={() => onChange({ ...draft, fact_decisions: decisions.filter((item) => item.fact_id !== fact.fact_id) })} />)}
  </details>;
}
