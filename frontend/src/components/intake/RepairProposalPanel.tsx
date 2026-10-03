import { observationCollections, type ObservationCollection } from "./draftWorkspace";
import type { LongitudinalIntakeDraft, PrescriptionRepairProposal } from "../../api";

export function adoptRepairProposal(draft: LongitudinalIntakeDraft, proposal: PrescriptionRepairProposal): LongitudinalIntakeDraft {
  if (!observationCollections.includes(proposal.collection as ObservationCollection)) throw new Error("Unsupported repair section.");
  const next = structuredClone(draft);
  for (const observation of next.observations) {
    const records = observation[proposal.collection as ObservationCollection];
    if (!Array.isArray(records)) continue;
    const record = records.find((entry) => entry.temp_id === proposal.record_id);
    if (!record || record.state === "edited") continue;
    for (const [field, patch] of Object.entries(proposal.patches)) {
      record.values[field] = patch.value;
      if (record.resolutions[field]) {
        const resolution = record.resolutions[field];
        resolution.status = "unresolved";
        resolution.raw_value = String(patch.value);
        if ("option_ids" in resolution) resolution.option_ids = [];
        else resolution.option_id = null;
      }
    }
    record.state = "edited";
    return next;
  }
  throw new Error("This record changed; reload the saved review before using its suggestion.");
}

export function RepairProposalPanel({ proposals, disabled, onAdopt }: { proposals: PrescriptionRepairProposal[]; disabled: boolean; onAdopt: (proposal: PrescriptionRepairProposal) => void }) {
  if (!proposals.length) return null;
  return <section className="panel" aria-label="Repair suggestions"><h3>Repair suggestions</h3><p>Check the source, then apply a suggestion to the form. Save and resolve remaining exceptions before final approval.</p>{proposals.map((proposal) => <article key={proposal.id}><h4>{proposal.collection.replaceAll("_", " ")}</h4>{Object.entries(proposal.patches).map(([field, patch]) => <p key={field}><strong>{field.replaceAll("_", " ")}: {String(patch.value)}</strong><br />Page {patch.page}: {patch.source_text}</p>)}<button type="button" className="secondary-button" disabled={disabled} onClick={() => onAdopt(proposal)}>Apply suggestion to form</button></article>)}{disabled && <p>Save current edits before applying a suggestion. Approved reviews are locked.</p>}</section>;
}
