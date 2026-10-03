import type { LongitudinalIntakeDraft } from "../../api";
import { sourceFacts } from "./sourceFacts";
import { observationCollections, type ObservationCollection } from "./draftWorkspace";

export interface DraftException {
  id: string;
  reason: string;
  rawValue?: unknown;
  observationId?: string;
  recordId?: string;
  collection?: ObservationCollection;
  field?: string;
  candidates?: string[];
  source?: string;
  scope?: "patient" | "context";
  action?: string;
}

export function draftExceptions(draft: LongitudinalIntakeDraft): DraftException[] {
  const result: DraftException[] = [];
  for (const observation of draft.observations) {
    for (const collection of observationCollections) {
      for (const record of observation[collection]) {
        for (const [field, resolution] of Object.entries(record.resolutions)) {
          if (resolution.status === "resolved") continue;
          const references = observation.evidence_refs.filter((ref) => record.evidence_refs.includes(ref.evidence_id));
          result.push({ id: `${record.temp_id}:${field}`, reason: resolution.reason || "Choose a valid dropdown option.",
            rawValue: record.extracted_values?.[field] ?? resolution.raw_value, observationId: observation.temp_id,
            recordId: record.temp_id, collection, field, candidates: resolution.candidates.map((item) => item.label),
            action: "Select a valid option in the actual form, or clear the proposed value and record an explained exclusion.",
            source: references.map((ref) => `p. ${ref.page ?? "?"}: ${ref.source_text}`).join(" · ") });
        }
        if (record.state === "unresolved" && !result.some((item) => item.recordId === record.temp_id)) {
          result.push({ id: record.temp_id, reason: "Review this record's unresolved values.", observationId: observation.temp_id, recordId: record.temp_id, collection });
        }
      }
    }
  }
  for (const [index, issue] of draft.unresolved_items.entries()) {
    const recordId = typeof issue.record_temp_id === "string" ? issue.record_temp_id : undefined;
    const observation = recordId
      ? draft.observations.find((item) => observationCollections.some((collection) => item[collection].some((record) => record.temp_id === recordId)))
      : draft.observations.find((item) => item.temp_id === issue.observation_temp_id);
    const collection = observationCollections.find((key) => key === issue.collection || Boolean(observation?.[key].some((item) => item.temp_id === recordId)));
    const record = observation && collection ? observation[collection].find((item) => item.temp_id === recordId) : undefined;
    const fieldPath = typeof issue.field_path === "string" ? issue.field_path : "";
    const field = typeof issue.field === "string" ? issue.field : fieldPath.split(".").at(-1) || undefined;
    const fact = sourceFacts(draft).find((item) => (recordId ? item.record_temp_id === recordId : fieldPath ? item.source_path === fieldPath || item.fact_id === fieldPath : false) && (!field || item.canonical_field === field));
    const raw = issue.raw_value ?? record?.extracted_values?.[field ?? ""] ?? fact?.raw_value;
    const wrapper = raw && typeof raw === "object" && !Array.isArray(raw) ? raw as Record<string, unknown> : undefined;
    const scope = !recordId ? (fieldPath.startsWith("patient.") || fact?.source_path.startsWith("patient.") ? "patient" : "context") : undefined;
    const references = observation?.evidence_refs.filter((ref) => record ? record.evidence_refs.includes(ref.evidence_id) && (!field || ref.field_path.endsWith("." + field)) : Boolean(field && ref.field_path.endsWith("." + field))) ?? [];
    result.push({ id: `issue:${index}`, reason: String(issue.reason ?? "Review this extracted fact."), rawValue: wrapper && "value" in wrapper ? wrapper.value : raw,
      observationId: observation?.temp_id ?? fact?.observation_temp_id, recordId: record?.temp_id, collection, field, scope,
      action: "Correct the affected form value and save, or record an explained exclusion in source decisions.",
      source: wrapper?.source_text ? `p. ${wrapper.page ?? "?"}: ${String(wrapper.source_text)}` : references.map((ref) => `p. ${ref.page ?? "?"}: ${ref.source_text}`).join(" · ") });
  }
  return result;
}

export function exceptionValue(value: unknown): string {
  if (value === undefined || value === null) return "Not supplied";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}
