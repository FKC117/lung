import type { LongitudinalIntakeDraft } from "../../api";

export type SourceFact = { fact_id: string; source_path: string; raw_value: unknown; disposition: string; canonical_field?: string; observation_temp_id?: string; record_temp_id?: string; collection?: string };
export function sourceFacts(draft: LongitudinalIntakeDraft): SourceFact[] {
  return (Array.isArray(draft.source_facts) ? draft.source_facts : []) as SourceFact[];
}
export function originalContextValues(draft: LongitudinalIntakeDraft, section: "patient" | "observation" | "anthropometry", observationId?: string): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const fact of sourceFacts(draft)) {
    if (!fact.canonical_field || fact.record_temp_id) continue;
    const matches = section === "patient" ? fact.source_path.startsWith("patient.") : fact.observation_temp_id === observationId &&
      (section === "anthropometry" ? fact.source_path.includes(".anthropometry.") : !fact.source_path.includes(".anthropometry."));
    if (matches) result[fact.canonical_field] = fact.raw_value;
  }
  return result;
}
export function originalValueText(value: unknown): string {
  if (value == null || value === "") return "Not supplied";
  if (Array.isArray(value)) return value.map(originalValueText).join(", ");
  if (typeof value === "object") return "value" in value ? originalValueText(value.value) : JSON.stringify(value);
  return String(value);
}
