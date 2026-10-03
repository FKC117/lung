import { useState } from "react";
import { Search } from "lucide-react";
import { fetchEntriesPatients, type EntriesPatientMatch, type EntryOption, type LongitudinalIntakeDraft } from "../../api";
import { IntakeSelectField, IntakeTextField } from "./SharedIntakeFields";
import { patientFieldSchema } from "./observationFieldSchema";
import { applyPatientMatch } from "./patientMatching";
import { originalValueText } from "./sourceFacts";

type Catalog = Record<string, EntryOption[]>;
type PatientDraft = LongitudinalIntakeDraft["patient"];
type SearchPatients = (query: string) => Promise<{ results: EntriesPatientMatch[] }>;

const fields = patientFieldSchema;

export interface PatientFormSectionsProps {
  patient: PatientDraft;
  catalog?: Catalog;
  disabled?: boolean;
  extractedValues?: Record<string, unknown>;
  onChange: (patient: PatientDraft) => void;
  searchPatients?: SearchPatients;
}

export function PatientFormSections({ patient, catalog = {}, disabled, extractedValues, onChange, searchPatients = (query) => fetchEntriesPatients(query, 1, 8) }: PatientFormSectionsProps) {
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<EntriesPatientMatch[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const update = (key: string, value: unknown) => onChange({ ...patient, values: { ...patient.values, [key]: value, ...(key === "district" ? { thana: "" } : {}) } });
  const runSearch = async () => {
    setSearching(true);
    setSearchError("");
    try { setMatches((await searchPatients(query.trim())).results); }
    catch { setMatches([]); setSearchError("Patient search could not be completed."); }
    finally { setSearching(false); }
  };

  return <section className="panel entry-block intake-form-section">
    <div className="panel-heading"><div><p className="eyebrow">Patient-level draft</p><h3>Patient profile and matching</h3></div><span className={`intake-state intake-state-${patient.match_status}`}>{patient.match_status}</span></div>
    <div className="entry-grid">
      <label className="filter-field"><span>Match status</span><select className="filter-select" value={patient.match_status} disabled={disabled} onChange={(event) => onChange({ ...patient, match_status: event.target.value as PatientDraft["match_status"], patient_id: event.target.value === "existing" ? patient.patient_id : null })}><option value="unresolved">Unresolved</option><option value="existing">Existing patient</option><option value="new">New patient</option></select></label>
    </div>
    {patient.match_status === "existing" ? <div className="entry-record-check" data-testid="patient-match-search">
      <div className="entry-record-lookup"><IntakeTextField label="Find existing patient" value={query} disabled={disabled} onChange={setQuery} help="Search by registry ID, registration number, name, or mobile number." /><button type="button" className="secondary-button" disabled={disabled || searching} onClick={runSearch}><Search size={15} />{searching ? "Searching…" : "Search"}</button></div>
      {searchError ? <p className="entry-error-message" role="alert">{searchError}</p> : null}
      <div className="entry-match-list">{matches.map((match) => <button type="button" className={`entry-match-card${patient.patient_id === match.id ? " is-selected" : ""}`} key={match.id} disabled={disabled} onClick={() => onChange(applyPatientMatch(patient, match))}><strong>{match.name || "Unnamed patient"}</strong><span>{match.patient_id || match.registration_no || "No registry identifier"}</span><small>{match.phone || "No mobile number"}</small></button>)}</div>
      {patient.patient_id ? <p className="entry-inline-note">Matched to the selected registry patient.</p> : null}
    </div> : null}
    <div className="entry-grid">
      {fields.map((field) => {
        let options = catalog[field.resource ?? ""] ?? [];
        if (field.key === "thana") options = typeof patient.values.district === "number" ? options.filter((option) => String(option.district) === String(patient.values.district)) : [];
        const value = patient.values[field.key] ?? "";
        const evidence = extractedValues && field.key in extractedValues ? <p className="entry-field-help clinical-extracted-value"><strong>Extracted value:</strong> {originalValueText(extractedValues[field.key])}</p> : undefined;
        return field.resource
          ? <IntakeSelectField key={field.key} label={field.label} evidence={evidence} value={String(value)} options={options} disabled={disabled} onChange={(selected, option) => update(field.key, option ? option.id : selected)} />
          : <IntakeTextField key={field.key} label={field.label} evidence={evidence} type={field.type} value={String(value)} disabled={disabled} onChange={(next) => update(field.key, next)} />;
      })}
    </div>
  </section>;
}
