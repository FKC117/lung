import type { ReactNode } from "react";
import type { EntryOption, LongitudinalIntakeDraft } from "../../api";

type Catalog = Record<string, EntryOption[]>;
type PatientDraft = LongitudinalIntakeDraft["patient"];

const fields: Array<{ key: string; label: string; type?: string; resource?: string }> = [
  { key: "patient_id", label: "Registry ID" }, { key: "name", label: "Patient name" },
  { key: "registration_no", label: "Registration no." }, { key: "phone", label: "Mobile no." },
  { key: "email", label: "Email", type: "email" }, { key: "nid", label: "NID" },
  { key: "passport", label: "Passport" }, { key: "date_of_birth", label: "Date of birth", type: "date" },
  { key: "age", label: "Age", type: "number" }, { key: "sex", label: "Sex", resource: "sexes" },
  { key: "district", label: "District", resource: "districts" }, { key: "thana", label: "Thana", resource: "thanas" },
  { key: "blood_group", label: "Blood group", resource: "blood-groups" },
  { key: "economic_status", label: "Economic status", resource: "economic-statuses" },
  { key: "type_of_patient", label: "Patient type", resource: "patient-types" }, { key: "area", label: "Area" },
];

export interface PatientFormSectionsProps {
  patient?: PatientDraft;
  catalog?: Catalog;
  disabled?: boolean;
  onChange?: (patient: PatientDraft) => void;
  children?: ReactNode;
}

export function PatientFormSections({ patient, catalog = {}, disabled, onChange, children }: PatientFormSectionsProps) {
  if (!patient || !onChange) return <>{children}</>;
  const update = (key: string, value: unknown) => onChange({ ...patient, values: { ...patient.values, [key]: value } });
  return <section className="panel entry-block intake-form-section">
    <div className="panel-heading"><div><p className="eyebrow">Patient-level draft</p><h3>Patient profile and matching</h3></div><span className={`intake-state intake-state-${patient.match_status}`}>{patient.match_status}</span></div>
    <div className="entry-grid">
      <label className="filter-field"><span>Match status</span><select className="filter-select" value={patient.match_status} disabled={disabled} onChange={(event) => onChange({ ...patient, match_status: event.target.value as PatientDraft["match_status"], patient_id: event.target.value === "existing" ? patient.patient_id : null })}><option value="unresolved">Unresolved</option><option value="existing">Existing patient</option><option value="new">New patient</option></select></label>
      {patient.match_status === "existing" ? <label className="filter-field"><span>Matched database patient ID</span><input className="auth-input" type="number" value={patient.patient_id ?? ""} disabled={disabled} onChange={(event) => onChange({ ...patient, patient_id: event.target.value ? Number(event.target.value) : null })} /></label> : null}
      {fields.map((field) => {
        let options = catalog[field.resource ?? ""] ?? [];
        if (field.key === "thana" && patient.values.district) options = options.filter((option) => String(option.district) === String(patient.values.district));
        const value = patient.values[field.key] ?? "";
        return field.resource ? <label className="filter-field" key={field.key}><span>{field.label}</span><select className="filter-select" value={String(value)} disabled={disabled} onChange={(event) => update(field.key, event.target.value ? Number(event.target.value) : "")}><option value="">Select {field.label.toLowerCase()}</option>{options.map((option) => <option key={option.id} value={option.id}>{option.name ?? option.display}</option>)}</select></label> : <label className="filter-field" key={field.key}><span>{field.label}</span><input className="auth-input" type={field.type ?? "text"} value={String(value)} disabled={disabled} onChange={(event) => update(field.key, event.target.value)} /></label>;
      })}
    </div>
    {children}
  </section>;
}
