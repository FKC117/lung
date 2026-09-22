import {
  type ChangeEvent,
  type FormEvent,
  type ReactNode,
  useDeferredValue,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CalendarDays,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Plus,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import {
  type ApiError,
  type EntriesPatientClinicalDetail,
  type EntriesIntakePayload,
  type EntryOption,
  createEntriesIntake,
  fetchEntriesDraft,
  fetchEntriesPatient,
  fetchEntriesPatientClinicalDetail,
  fetchEntriesOptions,
  fetchEntriesPatients,
  lookupEntriesPatient,
  saveEntriesDraft,
} from "../api";

type MolecularRow = {
  panel_version: string;
  panel_target: string;
  gene: string;
  exon: string;
  alteration_type: string;
  partner_gene: string;
  clinical_significance: string;
  method: string;
  specimen: string;
  specimen_collected_on: string;
  result: string;
  tested_at: string;
  reported_on: string;
  qc_status: string;
  laboratory: string;
  accession_number: string;
  dna_change: string;
  protein_change: string;
  common_name: string;
  variant_allele_frequency: string;
  copy_number: string;
  notes: string;
};
type MarkerRow = {
  marker_name: string;
  marker_unit: string;
  marker_value: string;
  tested_at: string;
};
type SmokingRow = {
  smoking_history: string;
  cigarettes_per_day: string;
  smoking_duration_in_years: string;
  quit_smoking_for_years: string;
};
type TbRow = {
  tb_history: string;
  tb_treatment_start_date: string;
  treatment_details: string;
};
type CovidRow = {
  covid_history: string;
  covid_infection_date: string;
  vaccine_name: string;
  vaccination_dose: string;
};
type TnmRow = {
  t: string;
  n: string;
  m: string;
  stage: string;
  staged_at: string;
};
type IHCResultRow = {
  detail_type: string;
  cycle: string;
  result: string;
  tested_at: string;
};
type IHCPanelRow = {
  tested_at: string;
  results: IHCResultRow[];
  staging_results: IHCResultRow[];
};
type PastTreatmentRow = { recorded_at: string; details: string };
type ResponseRow = {
  assessed_at: string;
  target_lesion: string;
  non_target_lesion: string;
  new_lesion: string;
  response_result: string;
  progression_sites: string[];
  estimation_method: string;
  response_category: string;
  residual_viable_tumor_percentage: string;
  tumor_regression_grade: string;
};
type ProtocolBuilderRow = {
  protocol_type: "primary" | "followed_by";
  protocols: string[];
  cycle_no: string;
};
type TreatmentAdministrationRow = {
  drug: string;
  administered_on: string;
  cycle_number: string;
  day_number: string;
  dose: string;
  dose_unit: string;
  status: string;
  notes: string;
};
type ProgressionRecordRow = { status: string; assessed_on: string; progression_date: string; progression_sites: string[]; estimation_method: string; notes: string };
type SurvivalFollowUpRow = { status: string; followed_up_on: string; death_date: string; cause_of_death: string; notes: string };
type TreatmentRow = {
  modalities: string[];
  current_treatment_protocol: string;
  treatment_protocol: string;
  treatment_protocol_cycle: string;
  chemo_cycle_no: string;
  chemotherapy_details: string;
  chronology_notes: string;
  started_at: string;
  ended_at: string;
  line_of_treatment: string;
  status: string;
  reason_for_stopping: string;
  course_notes: string;
  administrations: TreatmentAdministrationRow[];
  recist: ResponseRow;
  irecist: ResponseRow;
  pathological_response: ResponseRow;
  disease_progression_status: string;
  progression_status_date: string;
  survival_status: string;
  survival_status_date: string;
  pfs_months: string;
  overall_survival_months: string;
  protocol_builders: ProtocolBuilderRow[];
};
type SurgeryRow = {
  surgery_modality: string;
  surgery_date: string;
  lateralities: string[];
  status: string;
  procedure_details: string;
  operative_findings: string;
  complications: string;
  notes: string;
};
type RadiotherapyRow = {
  sites: string[];
  radiotherapy_intent: string;
  modalities: string[];
  started_at: string;
  ended_at: string;
  fraction_dose: string;
  fraction_count: string;
  total_dose: string;
  completed_fractions: string;
  status: string;
  reason_for_stopping: string;
  notes: string;
};

const steps = [
  "Patient profile and history",
  "Diagnosis and pathology",
  "Treatment and outcomes",
];
const stepTargets = [0, 2, 3];
const optionResourcesByStep: Record<number, string[]> = {
  0: [
    "sexes",
    "districts",
    "thanas",
    "blood-groups",
    "economic-statuses",
    "patient-types",
    "centers",
    "doctors",
    "marital-statuses",
    "alcohol-histories",
    "smoking-histories",
    "tb-histories",
    "covid-histories",
    "vaccines",
    "vaccination-doses",
    "comorbidities",
  ],
  2: [
    "diagnosis-disease-groups",
    "diagnosis-disease-subgroups",
    "diagnosis-primary-sites",
    "diagnosis-metastatic-sites",
    "diagnosis-lateralities",
    "histopathology-details",
    "histopathology-types",
    "histopathology-sites",
    "histopathology-grades",
    "ihc-cycles",
    "ihc-cycle-results",
    "ihc-staging-cycles",
    "ihc-staging-cycle-results",
    "tnm-t",
    "tnm-n",
    "tnm-m",
    "tnm-stages",
    "molecular-methods",
    "molecular-specimens",
    "molecular-panels",
    "molecular-panel-versions",
    "molecular-panel-targets",
    "molecular-genes",
    "molecular-exons",
    "molecular-alteration-types",
    "molecular-results",
    "molecular-clinical-significances",
    "cancer-marker-names",
  ],
  3: [
    "treatment-modalities",
    "treatment-protocols",
    "treatment-drugs",
    "lines-of-treatment",
    "disease-progression-statuses",
    "survival-statuses",
    "recist-target-lesions",
    "recist-non-target-lesions",
    "recist-new-lesions",
    "recist-response-results",
    "irecist-target-lesions",
    "irecist-non-target-lesions",
    "irecist-new-lesions",
    "irecist-response-results",
    "progression-sites",
    "response-estimation-methods",
    "pathological-response-categories",
    "tumor-regression-grades",
    "surgery-modalities",
    "surgery-lateralities",
    "radiotherapy-sites",
    "radiotherapy-intents",
    "radiotherapy-modalities",
  ],
};

const blankMolecular = (): MolecularRow => ({
  panel_version: "",
  panel_target: "",
  gene: "",
  exon: "",
  alteration_type: "",
  partner_gene: "",
  clinical_significance: "",
  method: "",
  specimen: "",
  specimen_collected_on: "",
  result: "",
  tested_at: "",
  reported_on: "",
  qc_status: "pending",
  laboratory: "",
  accession_number: "",
  dna_change: "",
  protein_change: "",
  common_name: "",
  variant_allele_frequency: "",
  copy_number: "",
  notes: "",
});
const blankMarker = (): MarkerRow => ({
  marker_name: "",
  marker_unit: "",
  marker_value: "",
  tested_at: "",
});
const blankSmoking = (): SmokingRow => ({
  smoking_history: "",
  cigarettes_per_day: "",
  smoking_duration_in_years: "",
  quit_smoking_for_years: "",
});
const blankTb = (): TbRow => ({
  tb_history: "",
  tb_treatment_start_date: "",
  treatment_details: "",
});
const blankCovid = (): CovidRow => ({
  covid_history: "",
  covid_infection_date: "",
  vaccine_name: "",
  vaccination_dose: "",
});
const blankTnm = (): TnmRow => ({
  t: "",
  n: "",
  m: "",
  stage: "",
  staged_at: "",
});
const blankIhcResult = (): IHCResultRow => ({
  detail_type: "",
  cycle: "",
  result: "",
  tested_at: "",
});
const blankIhcPanel = (): IHCPanelRow => ({
  tested_at: "",
  results: [blankIhcResult()],
  staging_results: [],
});
const blankPastTreatment = (): PastTreatmentRow => ({
  recorded_at: "",
  details: "",
});
const blankResponse = (): ResponseRow => ({
  assessed_at: "",
  target_lesion: "",
  non_target_lesion: "",
  new_lesion: "",
  response_result: "",
  progression_sites: [],
  estimation_method: "",
  response_category: "",
  residual_viable_tumor_percentage: "",
  tumor_regression_grade: "",
});
const blankProtocolBuilder = (
  protocol_type: ProtocolBuilderRow["protocol_type"] = "primary",
): ProtocolBuilderRow => ({ protocol_type, protocols: [], cycle_no: "" });
const blankTreatmentAdministration = (): TreatmentAdministrationRow => ({
  drug: "", administered_on: "", cycle_number: "", day_number: "", dose: "", dose_unit: "", status: "planned", notes: "",
});
const blankProgressionRecord = (): ProgressionRecordRow => ({ status: "", assessed_on: "", progression_date: "", progression_sites: [], estimation_method: "", notes: "" });
const blankSurvivalFollowUp = (): SurvivalFollowUpRow => ({ status: "", followed_up_on: "", death_date: "", cause_of_death: "", notes: "" });
const blankTreatment = (): TreatmentRow => ({
  modalities: [],
  current_treatment_protocol: "",
  treatment_protocol: "",
  treatment_protocol_cycle: "",
  chemo_cycle_no: "",
  chemotherapy_details: "",
  chronology_notes: "",
  started_at: "",
  ended_at: "",
  line_of_treatment: "",
  status: "planned",
  reason_for_stopping: "",
  course_notes: "",
  administrations: [],
  recist: blankResponse(),
  irecist: blankResponse(),
  pathological_response: blankResponse(),
  disease_progression_status: "",
  progression_status_date: "",
  survival_status: "",
  survival_status_date: "",
  pfs_months: "",
  overall_survival_months: "",
  protocol_builders: [blankProtocolBuilder()],
});
const blankSurgery = (): SurgeryRow => ({
  surgery_modality: "",
  surgery_date: "",
  lateralities: [],
  status: "planned",
  procedure_details: "",
  operative_findings: "",
  complications: "",
  notes: "",
});
const blankRadiotherapy = (): RadiotherapyRow => ({
  sites: [],
  radiotherapy_intent: "",
  modalities: [],
  started_at: "",
  ended_at: "",
  fraction_dose: "",
  fraction_count: "",
  total_dose: "",
  completed_fractions: "",
  status: "planned",
  reason_for_stopping: "",
  notes: "",
});

function optionLabel(option: EntryOption) {
  return option.name || option.display;
}
function normalizedOptionName(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]/g, "");
}
function uniqueOptions(options: EntryOption[]) {
  return Array.from(
    new Map(
      options.map((option) => [
        normalizedOptionName(optionLabel(option)),
        option,
      ]),
    ).values(),
  );
}
function selectedValues(event: ChangeEvent<HTMLSelectElement>) {
  return Array.from(event.target.selectedOptions, (option) => option.value);
}
function compact<T extends Record<string, unknown>>(value: T): T {
  return Object.fromEntries(
    Object.entries(value).filter(
      ([, item]) => item !== "" && item !== null && item !== undefined,
    ),
  ) as T;
}
function ids(values: string[]) {
  return values.map(Number).filter(Number.isFinite);
}
function toNumber(value: string) {
  return value === "" ? undefined : Number(value);
}
function calculatedAge(dateOfBirth: string, referenceDate: string) {
  if (!dateOfBirth || !referenceDate) return "";
  const birth = new Date(`${dateOfBirth}T00:00:00Z`);
  const reference = new Date(`${referenceDate}T00:00:00Z`);
  let age = reference.getUTCFullYear() - birth.getUTCFullYear();
  if (
    reference.getUTCMonth() < birth.getUTCMonth() ||
    (reference.getUTCMonth() === birth.getUTCMonth() &&
      reference.getUTCDate() < birth.getUTCDate())
  )
    age -= 1;
  return age >= 0 ? String(age) : "";
}
function ageParts(dateOfBirth: string, referenceDate: string) {
  if (!dateOfBirth || !referenceDate) return "";
  const birth = new Date(`${dateOfBirth}T00:00:00Z`);
  const reference = new Date(`${referenceDate}T00:00:00Z`);
  if (birth > reference) return "";
  let years = reference.getUTCFullYear() - birth.getUTCFullYear();
  let months = reference.getUTCMonth() - birth.getUTCMonth();
  let days = reference.getUTCDate() - birth.getUTCDate();
  if (days < 0) {
    months -= 1;
    days += new Date(
      Date.UTC(reference.getUTCFullYear(), reference.getUTCMonth(), 0),
    ).getUTCDate();
  }
  if (months < 0) {
    years -= 1;
    months += 12;
  }
  return `${years}y ${months}m ${days}d`;
}
function dateOfBirthFromPrescriptionAge(
  referenceDate: string,
  years: string,
  months: string,
  days: string,
) {
  if (!referenceDate || years === "" || !Number.isInteger(Number(years)))
    return "";
  const date = new Date(`${referenceDate}T00:00:00Z`);
  date.setUTCFullYear(date.getUTCFullYear() - Number(years));
  date.setUTCMonth(date.getUTCMonth() - (Number(months) || 0));
  date.setUTCDate(date.getUTCDate() - (Number(days) || 0));
  return date.toISOString().slice(0, 10);
}

function inclusiveMonths(start: string, end: string) {
  if (!start || !end) return "";
  const startDate = new Date(`${start}T00:00:00Z`);
  const endDate = new Date(`${end}T00:00:00Z`);
  if (Number.isNaN(startDate.valueOf()) || Number.isNaN(endDate.valueOf()))
    return "";
  if (endDate < startDate) return "";
  return String(
    (endDate.getUTCFullYear() - startDate.getUTCFullYear()) * 12 +
      endDate.getUTCMonth() -
      startDate.getUTCMonth() +
      1,
  );
}

function formatDisplayDate(value: string) {
  const [year, month, day] = value.split("-");
  return year && month && day ? `${day}/${month}/${year}` : "";
}

function parseDisplayDate(value: string) {
  const trimmed = value.trim();
  const displayMatch = trimmed.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  const isoMatch = trimmed.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (!displayMatch && !isoMatch) return null;
  const year = Number(displayMatch ? displayMatch[3] : isoMatch![1]);
  const month = Number(displayMatch ? displayMatch[2] : isoMatch![2]);
  const day = Number(displayMatch ? displayMatch[1] : isoMatch![3]);
  const date = new Date(Date.UTC(year, month - 1, day));
  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  )
    return null;
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function fieldHelper(label: string, type?: string, isOption = false) {
  if (label === "Total dose in cGY")
    return "Calculated automatically as fraction dose × fraction count.";
  if (isOption) return "Choose the option that best matches the recorded clinical information.";
  if (type === "date")
    return "Enter or paste a date as DD/MM/YYYY. You can also choose it from the calendar.";
  if (type === "number") return "Enter a numeric value only.";
  if (/protocol/i.test(label))
    return "Enter the regimen or protocol in free text; there is no character limit.";
  if (/details|notes|history|sites|chronology|mutation/i.test(label))
    return "Enter clinical details in free text; use commas or new lines for multiple items.";
  if (/email/i.test(label)) return "Enter a valid email address, if available.";
  if (/mobile|phone/i.test(label))
    return "Enter the patient's contact number, including the country code if used.";
  return "Enter the value recorded in the patient's clinical record.";
}

function calculatedTotalDose(fractionDose: string, fractionCount: string) {
  const dose = Number(fractionDose);
  const count = Number(fractionCount);
  if (!Number.isFinite(dose) || !Number.isFinite(count)) return "";
  return String(dose * count);
}

function hasResponseData(row: ResponseRow) {
  return Object.values(row).some((value) =>
    Array.isArray(value) ? value.length : Boolean(value),
  );
}

function latestTreatmentProtocol(source?: EntriesPatientClinicalDetail) {
  const observations = source?.observations ?? [];
  for (const observation of [...observations].reverse()) {
    const cycles = Array.isArray(observation.treatment_cycles)
      ? (observation.treatment_cycles as Array<Record<string, unknown>>)
      : [];
    for (const cycle of [...cycles].reverse()) {
      const labels = cycle.labels as Record<string, unknown> | undefined;
      const protocol =
        labels?.current_treatment_protocol ??
        cycle.current_treatment_protocol ??
        labels?.treatment_protocol ??
        cycle.treatment_protocol;
      if (typeof protocol === "string" && protocol.trim()) return protocol;
    }
  }
  return "";
}

function DateInput({
  value,
  onChange,
  readOnly = false,
}: {
  value: string;
  onChange: (value: string) => void;
  readOnly?: boolean;
}) {
  const [displayValue, setDisplayValue] = useState(() => formatDisplayDate(value));
  const pickerRef = useRef<HTMLInputElement>(null);

  useEffect(() => setDisplayValue(formatDisplayDate(value)), [value]);

  return (
    <div className="date-field-control">
      <input
        className="auth-input"
        inputMode="numeric"
        placeholder="DD/MM/YYYY"
        value={displayValue}
        readOnly={readOnly}
        onChange={(event) => {
          const nextValue = event.target.value;
          setDisplayValue(nextValue);
          const parsed = parseDisplayDate(nextValue);
          if (parsed) onChange(parsed);
          else if (!nextValue) onChange("");
        }}
        onBlur={() => setDisplayValue(formatDisplayDate(value))}
      />
      {!readOnly ? (
        <button
          type="button"
          className="date-picker-button"
          aria-label="Choose date from calendar"
          onClick={() => pickerRef.current?.showPicker?.()}
        >
          <CalendarDays size={17} />
        </button>
      ) : null}
      <input
        ref={pickerRef}
        className="date-picker-native"
        type="date"
        tabIndex={-1}
        aria-hidden="true"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange,
  required = false,
}: {
  label: string;
  value: string;
  options: EntryOption[];
  onChange: (value: string) => void;
  required?: boolean;
}) {
  return (
    <label className="filter-field">
      <span>
        {label}
        {required ? " *" : ""}
      </span>
      <select
        className="filter-select"
        value={value}
        required={required}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">Select…</option>
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {optionLabel(option)}
          </option>
        ))}
      </select>
      <p className="entry-field-help">{fieldHelper(label, undefined, true)}</p>
    </label>
  );
}

function StatusField({ label, value, onChange, choices }: { label: string; value: string; onChange: (value: string) => void; choices: Array<[string, string]> }) {
  return <label className="filter-field"><span>{label}</span><select className="filter-select" value={value} onChange={(event) => onChange(event.target.value)}>{choices.map(([key, text]) => <option key={key} value={key}>{text}</option>)}</select><p className="entry-field-help">Uses the current backend status value.</p></label>
}

const courseStatuses: Array<[string, string]> = [["planned", "Planned"], ["active", "Active"], ["completed", "Completed"], ["stopped", "Stopped"], ["held", "Held"], ["cancelled", "Cancelled"]]
const surgeryStatuses: Array<[string, string]> = [["planned", "Planned"], ["performed", "Performed"], ["cancelled", "Cancelled"]]

function TextField({
  label,
  value,
  onChange,
  type = "text",
  required = false,
  readOnly = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
  readOnly?: boolean;
}) {
  if (
    [
      "Registry ID",
      "Registration no.",
      "Mobile no.",
      "Observation registration no.",
    ].includes(label)
  )
    return null;
  return (
    <label className="filter-field">
      <span>
        {label}
        {required ? " *" : ""}
      </span>
      {type === "date" ? (
        <DateInput value={value} onChange={onChange} readOnly={readOnly} />
      ) : (
        <input
          className="auth-input"
          type={type}
          required={required}
          readOnly={readOnly}
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
      <p className="entry-field-help">{fieldHelper(label, type)}</p>
    </label>
  );
}

function TextArea({
  label,
  value,
  onChange,
  fullWidth = true,
  className = "",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  fullWidth?: boolean;
  className?: string;
}) {
  return (
    <label
      className={`${fullWidth ? "filter-field entry-span-full" : "filter-field"} ${className}`.trim()}
    >
      <span>{label}</span>
      <textarea
        className="auth-input entry-textarea"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      <p className="entry-field-help">{fieldHelper(label)}</p>
    </label>
  );
}

function CheckboxGroup({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: EntryOption[];
  value: string[];
  onChange: (value: string[]) => void;
}) {
  return (
    <section className="panel entry-block">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Clinical context</p>
          <h3>{label}</h3>
        </div>
      </div>
      <MultiSelectField
        label={label}
        options={options}
        value={value}
        onChange={onChange}
      />
    </section>
  );
}

function MultiSelectField({
  label,
  options,
  value,
  onChange,
  fullWidth = true,
}: {
  label: string;
  options: EntryOption[];
  value: string[];
  onChange: (value: string[]) => void;
  fullWidth?: boolean;
}) {
  const pickerRef = useRef<HTMLDivElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [opensUpward, setOpensUpward] = useState(false);
  const selected = options.filter((option) =>
    value.includes(String(option.id)),
  );
  const summary = selected.length
    ? selected.slice(0, 2).map(optionLabel).join(", ") +
      (selected.length > 2 ? ` +${selected.length - 2}` : "")
    : "Select one or more";

  useEffect(() => {
    if (!isOpen) return;
    const positionOptions = () => {
      const rect = pickerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const spaceBelow = window.innerHeight - rect.bottom;
      const spaceAbove = rect.top;
      setOpensUpward(spaceBelow < 280 && spaceAbove > spaceBelow);
    };
    const closeIfOutside = (event: MouseEvent) => {
      if (!pickerRef.current?.contains(event.target as Node)) setIsOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsOpen(false);
    };
    positionOptions();
    document.addEventListener("mousedown", closeIfOutside);
    document.addEventListener("keydown", closeOnEscape);
    window.addEventListener("resize", positionOptions);
    window.addEventListener("scroll", positionOptions, true);
    return () => {
      document.removeEventListener("mousedown", closeIfOutside);
      document.removeEventListener("keydown", closeOnEscape);
      window.removeEventListener("resize", positionOptions);
      window.removeEventListener("scroll", positionOptions, true);
    };
  }, [isOpen]);

  return (
    <fieldset
      className={`filter-field${fullWidth ? " entry-span-full" : ""} entry-choice-group`}
    >
      <legend>{label}</legend>
      <div
        ref={pickerRef}
        className={`entry-multi-picker${isOpen ? " is-open" : ""}`}
      >
        <button
          type="button"
          className="entry-multi-trigger"
          aria-expanded={isOpen}
          onClick={() => setIsOpen((open) => !open)}
        >
          <span>{summary}</span>
          <ChevronDown size={18} />
        </button>
        {isOpen ? (
          <div
            className={`entry-multi-options${opensUpward ? " entry-multi-options-upward" : ""}`}
          >
            {options.map((option) => {
              const id = String(option.id);
              const checked = value.includes(id);
              return (
                <label className="entry-multi-option" key={id}>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() =>
                      onChange(
                        checked
                          ? value.filter((item) => item !== id)
                          : [...value, id],
                      )
                    }
                  />
                  <span>{optionLabel(option)}</span>
                </label>
              );
            })}
          </div>
        ) : null}
      </div>
      <p className="entry-field-help">Select all options that apply to this record.</p>
    </fieldset>
  );
}

function InlineCheckboxGroup({
  label,
  options,
  value,
  onChange,
  fullWidth = true,
}: {
  label: string;
  options: EntryOption[];
  value: string[];
  onChange: (value: string[]) => void;
  fullWidth?: boolean;
}) {
  return (
    <MultiSelectField
      label={label}
      options={options}
      value={value}
      onChange={onChange}
      fullWidth={fullWidth}
    />
  );
}

function ResponseAssessmentCard({
  title,
  showTitle = true,
  row,
  onChange,
  getOptions,
  resources,
}: {
  title: string;
  showTitle?: boolean;
  row: ResponseRow;
  onChange: (row: ResponseRow) => void;
  getOptions: (resource: string) => EntryOption[];
  resources: {
    target: string;
    nonTarget: string;
    newLesion: string;
    result: string;
  };
}) {
  return (
    <section className="entry-response-card">
      {showTitle ? <h4>{title}</h4> : null}
      <div className="entry-grid">
        <SelectField
          label="Target lesion"
          value={row.target_lesion}
          options={getOptions(resources.target)}
          onChange={(target_lesion) => onChange({ ...row, target_lesion })}
        />
        <SelectField
          label="Non-target lesion"
          value={row.non_target_lesion}
          options={getOptions(resources.nonTarget)}
          onChange={(non_target_lesion) =>
            onChange({ ...row, non_target_lesion })
          }
        />
        <SelectField
          label="New lesions"
          value={row.new_lesion}
          options={getOptions(resources.newLesion)}
          onChange={(new_lesion) => onChange({ ...row, new_lesion })}
        />
        <TextField
          label="Assessment date"
          type="date"
          value={row.assessed_at}
          onChange={(assessed_at) => onChange({ ...row, assessed_at })}
        />
        <SelectField
          label="Progression site"
          value={row.progression_sites[0] || ""}
          options={getOptions("progression-sites")}
          onChange={(value) =>
            onChange({ ...row, progression_sites: value ? [value] : [] })
          }
        />
        <SelectField
          label="Method of estimation"
          value={row.estimation_method}
          options={getOptions("response-estimation-methods")}
          onChange={(estimation_method) =>
            onChange({ ...row, estimation_method })
          }
        />
        <SelectField
          label="Response result"
          value={row.response_result}
          options={getOptions(resources.result)}
          onChange={(response_result) => onChange({ ...row, response_result })}
        />
      </div>
    </section>
  );
}

function RadioGroup({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: EntryOption[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <fieldset className="filter-field entry-span-full entry-radio-group">
      <legend>{label}</legend>
      <div className="entry-checkbox-grid">
        {options.map((option) => {
          const id = String(option.id);
          return (
            <label className="entry-checkbox" key={id}>
              <input
                type="radio"
                name="histopathology-grade"
                value={id}
                checked={value === id}
                onChange={() => onChange(id)}
              />
              <span>{optionLabel(option)}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

function IHCPanelMatrix({
  panel,
  panelIndex,
  cycles,
  resultOptions,
  onTestedAtChange,
  onResultChange,
}: {
  panel: IHCPanelRow;
  panelIndex: number;
  cycles: EntryOption[];
  resultOptions: EntryOption[];
  onTestedAtChange: (value: string) => void;
  onResultChange: (cycle: string, result: string) => void;
}) {
  const columns = ["Positive", "Negative", "Not Done"];
  const resultId = (label: string) =>
    String(
      resultOptions.find(
        (option) =>
          normalizedOptionName(optionLabel(option)) ===
          normalizedOptionName(label),
      )?.id ?? "",
    );

  return (
    <div className="entry-status-matrix">
      <TextField
        label="IHC date"
        type="date"
        value={panel.tested_at}
        onChange={onTestedAtChange}
      />
      <div className="entry-status-table-wrap">
        <table className="entry-status-table">
          <thead>
            <tr>
              <th>Marker</th>
              {columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {cycles.map((cycle) => {
              const cycleId = String(cycle.id);
              const selected =
                panel.results.find((row) => row.cycle === cycleId)?.result ??
                "";
              return (
                <tr key={cycleId}>
                  <th scope="row">{optionLabel(cycle)}</th>
                  {columns.map((column) => {
                    const id = resultId(column);
                    return (
                      <td key={column}>
                        <input
                          type="radio"
                          name={`ihc-${panelIndex}-${cycleId}`}
                          disabled={!id}
                          checked={selected === id}
                          onChange={() => onResultChange(cycleId, id)}
                          aria-label={`${optionLabel(cycle)} ${column}`}
                        />
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PathologicalStagingMatrix({
  details,
  onChange,
}: {
  details: {
    lvsi: string;
    pni: string;
    margin: string;
    ki67: string;
    staged_at: string;
  };
  onChange: (
    key: "lvsi" | "pni" | "margin" | "ki67" | "staged_at",
    value: string,
  ) => void;
}) {
  const rows = [
    ["lvsi", "LVSI"],
    ["pni", "PNI"],
    ["margin", "Margin"],
    ["ki67", "Ki-67"],
  ] as const;
  const columns = ["Positive", "Negative", "Not Done"];
  return (
    <div className="entry-status-matrix">
      <TextField
        label="Staging detail date"
        type="date"
        value={details.staged_at}
        onChange={(value) => onChange("staged_at", value)}
      />
      <div className="entry-status-table-wrap">
        <table className="entry-status-table">
          <thead>
            <tr>
              <th>Feature</th>
              {columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(([key, label]) => (
              <tr key={key}>
                <th scope="row">{label}</th>
                {columns.map((column) => (
                  <td key={column}>
                    <input
                      type="radio"
                      name={`pathological-${key}`}
                      checked={details[key] === column}
                      onChange={() => onChange(key, column)}
                      aria-label={`${label} ${column}`}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const historicalRecordGroups = [
  ["histories", "Patient history"],
  ["smoking_history_records", "Smoking history"],
  ["tb_history_records", "TB history"],
  ["covid_history_records", "COVID history"],
  ["comorbidities", "Comorbidities"],
  ["diagnoses", "Diagnosis"],
  ["histopathologies", "Histopathology"],
  ["clinical_tnm_stagings", "Clinical TNM staging"],
  ["pathological_tnm_stagings", "Pathological TNM staging"],
  ["pathological_staging_details", "Pathological staging details"],
  ["ihc_panels", "IHC panels"],
  ["ihc_results", "IHC results"],
  ["ihc_staging_results", "Pathological staging results"],
  ["molecular_pathologies", "Molecular pathology"],
  ["cancer_markers", "Cancer markers"],
  ["past_treatment_histories", "Past treatment history"],
  ["treatment_cycles", "Treatment protocols and outcomes"],
  ["surgeries", "Surgery"],
  ["radiotherapy_schedules", "Radiotherapy"],
] as const;

const hiddenHistoricalFields = new Set([
  "id",
  "legacy_id",
  "observation",
  "patient_history",
  "labels",
  "source_created_at",
  "source_updated_at",
  "source_observed_on",
  "source_date",
]);

function historicalLabel(key: string) {
  return key.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function historicalValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Not recorded";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value))
    return value.length ? value.map(historicalValue).join(", ") : "Not recorded";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function HistoricalRecordList({ records }: { records: Array<Record<string, unknown>> }) {
  return (
    <div className="entry-history-record-list">
      {records.map((record, index) => {
        const labels = (record.labels as Record<string, string | string[]> | undefined) ?? {};
        const fields = Object.entries(record).filter(([key, value]) =>
          !hiddenHistoricalFields.has(key) &&
          !key.startsWith("source_") &&
          value !== null &&
          value !== undefined &&
          value !== "",
        );
        return (
          <div className="entry-history-record" key={String(record.id ?? index)}>
            {fields.map(([key, value]) => (
              <div key={key}>
                <span>{historicalLabel(key)}</span>
                <strong>{historicalValue(labels[key] ?? value)}</strong>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}

function PublishedObservationHistory({
  source,
}: {
  source: EntriesPatientClinicalDetail;
}) {
  const observations = source.observations.filter((entry) => {
    const observation = entry.observation as Record<string, unknown> | undefined;
    return Boolean(
      observation &&
        (observation.status === "published" || observation.is_draft === false) &&
        !observation.is_draft,
    );
  });
  if (!observations.length) return null;

  return (
    <section className="panel entry-published-history">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Longitudinal record</p>
          <h3>Previous published observations</h3>
          <p className="entry-inline-note">
            Historical records are read-only. Add only new records in the form below.
          </p>
        </div>
      </div>
      <div className="entry-history-observations">
        {observations.map((entry, index) => {
          const observation = entry.observation as Record<string, unknown>;
          const observedAt = String(observation.observed_at ?? "No observation date").slice(0, 10);
          return (
            <details className="entry-history-observation" key={String(observation.id ?? index)} open>
              <summary>
                <span>
                  <strong>Observation {observedAt}</strong>
                  <small>
                    {String(observation.registration_no ?? "No registration no.")}
                    {observation.cancer_type ? ` · ${String(observation.cancer_type)}` : ""}
                  </small>
                </span>
                <span className="entry-history-readonly">Published record</span>
              </summary>
              <div className="entry-history-groups">
                {historicalRecordGroups.map(([key, label]) => {
                  const records = Array.isArray(entry[key])
                    ? (entry[key] as Array<Record<string, unknown>>)
                    : [];
                  if (!records.length) return null;
                  return (
                    <section className="entry-history-group" key={key}>
                      <h4>{label}</h4>
                      <HistoricalRecordList records={records} />
                    </section>
                  );
                })}
              </div>
            </details>
          );
        })}
      </div>
    </section>
  );
}

export default function EntriesPatientEntryPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const requestedPatientId = Number(searchParams.get("patient_id"));
  const [activeStep, setActiveStep] = useState(0);
  const visibleStepIndex = stepTargets.indexOf(activeStep);
  const [error, setError] = useState("");
  const [lookup, setLookup] = useState("");
  const [existingPatientId, setExistingPatientId] = useState<number | null>(
    () =>
      Number.isSafeInteger(requestedPatientId) && requestedPatientId > 0
        ? requestedPatientId
        : null,
  );
  const [draftObservationId, setDraftObservationId] = useState<number | null>(
    null,
  );
  const [draftNotice, setDraftNotice] = useState("");
  const deferredLookup = useDeferredValue(lookup);
  const [patient, setPatient] = useState({
    patient_id: "",
    registration_no: "",
    name: "",
    phone: "",
    email: "",
    nid: "",
    passport: "",
    date_of_birth: "",
    age: "",
    sex: "",
    district: "",
    thana: "",
    blood_group: "",
    economic_status: "",
    type_of_patient: "",
    area: "",
  });
  const [observation, setObservation] = useState({
    observed_at: "",
    prescription_date: "",
    prescription_age_years: "",
    prescription_age_months: "",
    prescription_age_days: "",
    registration_no: "",
    doctor: "",
    center: "",
    cancer_type: "Lung",
    is_draft: false,
  });
  const [history, setHistory] = useState({
    marital_status: "",
    dietary_habits: "",
    height_cm: "",
    weight_kg: "",
    history_of_alcohol_consumption: "",
    radiotherapy_to_chest: "",
    first_diagnosis_date: "",
    personal_or_family_history_of_cancer: "",
    cancer_history: "",
    family_cancer_history: "",
    any_known_mutations: "",
  });
  const [smoking, setSmoking] = useState<SmokingRow[]>([blankSmoking()]);
  const [tbHistory, setTbHistory] = useState<TbRow[]>([blankTb()]);
  const [covidHistory, setCovidHistory] = useState<CovidRow[]>([blankCovid()]);
  const [comorbidities, setComorbidities] = useState<string[]>([]);
  const [diagnosis, setDiagnosis] = useState({
    disease_group: "",
    disease_subgroup: "",
    primary_site: "",
    laterality: "",
    diagnosis_in_details: "",
    metastatic_sites: [] as string[],
    histopathology_details: "",
    histopathology_type: "",
    histopathology_site: "",
    histopathology_grade: "",
    biopsy_date: "",
  });
  const [clinicalTnm, setClinicalTnm] = useState<TnmRow[]>([blankTnm()]);
  const [pathologicalTnm, setPathologicalTnm] = useState<TnmRow[]>([
    blankTnm(),
  ]);
  const [pathologicalDetails, setPathologicalDetails] = useState({
    lvsi: "",
    pni: "",
    margin: "",
    ki67: "",
    staged_at: "",
  });
  const [ihcPanels, setIhcPanels] = useState<IHCPanelRow[]>([blankIhcPanel()]);
  const [pastTreatments, setPastTreatments] = useState<PastTreatmentRow[]>([
    blankPastTreatment(),
  ]);
  void setClinicalTnm;
  void setPathologicalTnm;
  void setPathologicalDetails;
  void setIhcPanels;
  const [molecular, setMolecular] = useState<MolecularRow[]>([
    blankMolecular(),
  ]);
  const [markers, setMarkers] = useState<MarkerRow[]>([blankMarker()]);
  const [treatments, setTreatments] = useState<TreatmentRow[]>([
    blankTreatment(),
  ]);
  const [progressionRecords, setProgressionRecords] = useState<ProgressionRecordRow[]>([blankProgressionRecord()]);
  const [survivalFollowUps, setSurvivalFollowUps] = useState<SurvivalFollowUpRow[]>([blankSurvivalFollowUp()]);
  const [surgeries, setSurgeries] = useState<SurgeryRow[]>([blankSurgery()]);
  const [radiotherapySchedules, setRadiotherapySchedules] = useState<
    RadiotherapyRow[]
  >([blankRadiotherapy()]);
  // Each entry session gets a fresh draft lookup. Published drafts must never
  // be restored from a previous React Query cache entry.
  const [draftLookupSession] = useState(() => Math.random().toString(36));

  const optionResources = optionResourcesByStep[activeStep] ?? [];
  const optionsQuery = useQuery({
    // Include the actual resource set: this prevents a cached earlier version
    // of a step from omitting newly added controlled vocabularies.
    queryKey: ["entries-options", activeStep, optionResources.join(",")],
    queryFn: () => fetchEntriesOptions(optionResources),
    // Revalidate after returning from option maintenance in Django admin.
    staleTime: 0,
    refetchOnMount: "always",
  });
  const existingQuery = useQuery({
    queryKey: ["entries-patient-search", deferredLookup],
    queryFn: () => fetchEntriesPatients(deferredLookup),
    enabled: deferredLookup.trim().length >= 3,
  });
  const patientLookupQuery = useQuery({
    queryKey: [
      "entries-patient-identifier",
      patient.registration_no,
      patient.phone,
    ],
    queryFn: () => lookupEntriesPatient(patient.registration_no, patient.phone),
    enabled:
      patient.registration_no.trim().length >= 3 ||
      patient.phone.trim().length >= 6,
  });
  const resolvedPatientId =
    existingPatientId ?? patientLookupQuery.data?.match?.id ?? null;
  const selectedPatientQuery = useQuery({
    queryKey: ["entries-patient", resolvedPatientId],
    queryFn: () => fetchEntriesPatient(resolvedPatientId!),
    enabled: resolvedPatientId !== null,
  });
  const clinicalDetailQuery = useQuery({
    queryKey: ["entries-patient-clinical-detail", resolvedPatientId],
    queryFn: () => fetchEntriesPatientClinicalDetail(resolvedPatientId!),
    enabled: resolvedPatientId !== null,
  });
  const previousTreatmentProtocol = useMemo(
    () => latestTreatmentProtocol(clinicalDetailQuery.data),
    [clinicalDetailQuery.data],
  );
  const draftQuery = useQuery({
    queryKey: [
      "entries-observation-draft",
      resolvedPatientId,
      draftLookupSession,
    ],
    queryFn: () => fetchEntriesDraft(resolvedPatientId!),
    enabled: resolvedPatientId !== null,
    gcTime: 0,
    refetchOnMount: "always",
  });
  const options = optionsQuery.data ?? {};
  const getOptions = (key: string) => options[key] ?? [];
  const subgroups = getOptions("diagnosis-disease-subgroups").filter(
    (option) =>
      !diagnosis.disease_group ||
      String(option.disease_group) === diagnosis.disease_group,
  );
  const thanas = getOptions("thanas").filter(
    (option) =>
      !patient.district || String(option.district) === patient.district,
  );

  const queryClient = useQueryClient();
  const saveMutation = useMutation({
    mutationFn: createEntriesIntake,
    onSuccess: async (result) => {
      queryClient.removeQueries({
        queryKey: ["entries-observation-draft", result.patient_id],
      });
      await queryClient.invalidateQueries({
        predicate: (query) =>
          Array.isArray(query.queryKey) &&
          String(query.queryKey[0]).startsWith("analytics"),
      });
      navigate(`/entries/patients/${result.patient_id}`);
    },
    onError: (apiError: ApiError) =>
      setError(apiError.message || "Unable to save the new clinical entry."),
  });
  const draftMutation = useMutation({
    mutationFn: saveEntriesDraft,
    onSuccess: (result) => {
      setDraftObservationId(result.observation_id);
      setExistingPatientId(result.patient_id);
      queryClient.invalidateQueries({
        queryKey: ["entries-observation-draft", result.patient_id],
      });
      setDraftNotice(
        "Draft saved. You can continue editing and publish when ready.",
      );
    },
    onError: (apiError: ApiError) =>
      setError(apiError.message || "Unable to save the draft."),
  });

  useEffect(() => {
    if (
      patient.district &&
      patient.thana &&
      !thanas.some((option) => String(option.id) === patient.thana)
    )
      setPatient((current) => ({ ...current, thana: "" }));
  }, [patient.district, patient.thana, thanas]);
  useEffect(() => {
    setExistingPatientId(
      Number.isSafeInteger(requestedPatientId) && requestedPatientId > 0
        ? requestedPatientId
        : null,
    );
  }, [requestedPatientId]);
  useEffect(() => {
    const selected = selectedPatientQuery.data;
    if (!selected) return;
    setPatient((current) => {
      const next = {
        ...current,
        patient_id: String(selected.patient_id ?? ""),
        name: String(selected.name ?? ""),
        phone: String(selected.phone ?? ""),
        registration_no: String(selected.registration_no ?? ""),
        email: String(selected.email ?? ""),
        nid: String(selected.nid ?? ""),
        passport: String(selected.passport ?? ""),
        date_of_birth: String(selected.date_of_birth ?? ""),
        age: selected.age ? String(selected.age) : "",
        sex: selected.sex ? String(selected.sex) : "",
        district: selected.district ? String(selected.district) : "",
        thana: selected.thana ? String(selected.thana) : "",
        blood_group: selected.blood_group ? String(selected.blood_group) : "",
        economic_status: selected.economic_status
          ? String(selected.economic_status)
          : "",
        type_of_patient: selected.type_of_patient
          ? String(selected.type_of_patient)
          : "",
        area: String(selected.area ?? ""),
      };
      return Object.entries(next).every(
        ([key, value]) => current[key as keyof typeof current] === value,
      )
        ? current
        : next;
    });
  }, [selectedPatientQuery.data?.id]);
  useEffect(() => {
    const selected = patientLookupQuery.data?.match;
    if (!selected) return;
    setExistingPatientId(selected.id);
    setPatient((current) => {
      const next = {
        ...current,
        patient_id: String(selected.patient_id ?? ""),
        name: String(selected.name ?? ""),
        phone: String(selected.phone ?? current.phone),
        registration_no: String(
          selected.registration_no ?? current.registration_no,
        ),
        email: String(selected.email ?? ""),
        nid: String(selected.nid ?? ""),
        passport: String(selected.passport ?? ""),
        date_of_birth: String(selected.date_of_birth ?? ""),
        age: selected.age ? String(selected.age) : "",
        sex: selected.sex ? String(selected.sex) : "",
        district: selected.district ? String(selected.district) : "",
        thana: selected.thana ? String(selected.thana) : "",
        blood_group: selected.blood_group ? String(selected.blood_group) : "",
        economic_status: selected.economic_status
          ? String(selected.economic_status)
          : "",
        type_of_patient: selected.type_of_patient
          ? String(selected.type_of_patient)
          : "",
        area: String(selected.area ?? ""),
      };
      return Object.entries(next).every(
        ([key, value]) => current[key as keyof typeof current] === value,
      )
        ? current
        : next;
    });
  }, [patientLookupQuery.data?.match?.id]);
  useEffect(() => {
    if (!previousTreatmentProtocol) return;
    setTreatments((current) =>
      current.map((row) =>
        row.current_treatment_protocol ||
        row.treatment_protocol ||
        row.chemotherapy_details ||
        row.modalities.length ||
        row.protocol_builders.some(
          (builder) => builder.protocols.length || builder.cycle_no,
        )
          ? row
          : { ...row, current_treatment_protocol: previousTreatmentProtocol },
      ),
    );
  }, [previousTreatmentProtocol]);
  useEffect(() => {
    const draft = draftQuery.data?.draft;
    if (!draftQuery.isSuccess) return;
    if (!draft) {
      setDraftObservationId((current) => (current === null ? current : null));
      return;
    }
    if (draft.observation_id === draftObservationId) return;
    const payload = draft.payload;
    const formState = payload.draft_form_state as
      Record<string, unknown> | undefined;
    if (formState) {
      if (formState.patient) setPatient(formState.patient as typeof patient);
      if (formState.observation)
        setObservation(formState.observation as typeof observation);
      if (formState.history) setHistory(formState.history as typeof history);
      if (formState.smoking) setSmoking(formState.smoking as SmokingRow[]);
      if (formState.tbHistory) setTbHistory(formState.tbHistory as TbRow[]);
      if (formState.covidHistory)
        setCovidHistory(formState.covidHistory as CovidRow[]);
      if (formState.comorbidities)
        setComorbidities(formState.comorbidities as string[]);
      if (formState.diagnosis)
        setDiagnosis(formState.diagnosis as typeof diagnosis);
      if (formState.clinicalTnm)
        setClinicalTnm(formState.clinicalTnm as TnmRow[]);
      if (formState.pathologicalTnm)
        setPathologicalTnm(formState.pathologicalTnm as TnmRow[]);
      if (formState.pathologicalDetails)
        setPathologicalDetails(
          formState.pathologicalDetails as typeof pathologicalDetails,
        );
      if (formState.ihcPanels)
        setIhcPanels(formState.ihcPanels as IHCPanelRow[]);
      if (formState.pastTreatments)
        setPastTreatments(formState.pastTreatments as PastTreatmentRow[]);
      if (formState.molecular)
        setMolecular(formState.molecular as MolecularRow[]);
      if (formState.markers) setMarkers(formState.markers as MarkerRow[]);
      if (formState.treatments)
        setTreatments(formState.treatments as TreatmentRow[]);
      if (formState.surgeries)
        setSurgeries(formState.surgeries as SurgeryRow[]);
      if (formState.radiotherapySchedules)
        setRadiotherapySchedules(
          formState.radiotherapySchedules as RadiotherapyRow[],
        );
    }
    const savedObservation = payload.observation as
      Record<string, unknown> | undefined;
    if (!formState && savedObservation) {
      setObservation((current) => ({
        ...current,
        doctor: String(savedObservation.doctor ?? current.doctor),
        center: String(savedObservation.center ?? current.center),
        cancer_type: String(
          savedObservation.cancer_type ?? current.cancer_type,
        ),
        observed_at: String(savedObservation.observed_at ?? "").slice(0, 10),
        prescription_date: String(savedObservation.prescription_date ?? ""),
        is_draft: true,
      }));
    }
    const savedComorbidities = payload.comorbidities;
    if (!formState && Array.isArray(savedComorbidities)) {
      setComorbidities(
        savedComorbidities
          .map((item) =>
            item && typeof item === "object" && "comorbidity" in item
              ? String((item as { comorbidity: unknown }).comorbidity)
              : "",
          )
          .filter(Boolean),
      );
    }
    if (
      !formState &&
      Array.isArray(payload.diagnoses) &&
      payload.diagnoses[0]
    ) {
      const savedDiagnosis = payload.diagnoses[0] as Record<string, unknown>;
      setDiagnosis((current) => ({
        ...current,
        disease_group: String(savedDiagnosis.disease_group ?? ""),
        disease_subgroup: String(savedDiagnosis.disease_subgroup ?? ""),
        primary_site: String(savedDiagnosis.primary_site ?? ""),
        laterality: String(savedDiagnosis.laterality ?? ""),
        diagnosis_in_details: String(savedDiagnosis.diagnosis_in_details ?? ""),
        metastatic_sites: Array.isArray(savedDiagnosis.metastatic_sites)
          ? savedDiagnosis.metastatic_sites.map(String)
          : [],
      }));
    }
    if (
      !formState &&
      Array.isArray(payload.histopathologies) &&
      payload.histopathologies[0]
    ) {
      const savedHistopathology = payload.histopathologies[0] as Record<
        string,
        unknown
      >;
      setDiagnosis((current) => ({
        ...current,
        biopsy_date: String(savedHistopathology.biopsy_date ?? ""),
        histopathology_details: String(
          savedHistopathology.histopathology_details ?? "",
        ),
        histopathology_type: String(
          savedHistopathology.histopathology_type ?? "",
        ),
        histopathology_site: String(
          savedHistopathology.histopathology_site ?? "",
        ),
        histopathology_grade: String(
          savedHistopathology.histopathology_grade ?? "",
        ),
      }));
    }
    setDraftObservationId(draft.observation_id);
    setDraftNotice("Draft restored. Continue where you left off.");
  }, [draftQuery.data?.draft?.observation_id, draftObservationId]);

  function updateRow<T>(
    setter: React.Dispatch<React.SetStateAction<T[]>>,
    index: number,
    field: keyof T,
    value: T[keyof T],
  ) {
    setter((rows) =>
      rows.map((row, rowIndex) =>
        rowIndex === index ? { ...row, [field]: value } : row,
      ),
    );
  }

  function buildPayload(isDraft = false): EntriesIntakePayload {
    const optionName = (resource: string, id: string) =>
      getOptions(resource).find((option) => String(option.id) === id)?.name ||
      "";
    const protocolSummary = (builders: ProtocolBuilderRow[]) =>
      builders
        .filter((builder) => builder.protocols.length)
        .map((builder) => {
          const names = builder.protocols
            .map((id) => optionName("treatment-protocols", id))
            .filter(Boolean)
            .join(" + ");
          return `${builder.protocol_type === "followed_by" ? "Followed by " : ""}${names}${builder.cycle_no ? ` ${builder.cycle_no} cycle${builder.cycle_no === "1" ? "" : "s"}` : ""}`;
        })
        .join("; ");
    const tnmPayload = (rows: TnmRow[], resource: string) =>
      rows
        .filter((row) => row.t || row.n || row.m || row.stage || row.staged_at)
        .map((row) => {
          const staging = getOptions(resource).find(
            (option) =>
              String(option.t ?? "") === row.t &&
              String(option.n ?? "") === row.n &&
              String(option.m ?? "") === row.m &&
              String(option.stage ?? "") === row.stage,
          );
          return compact({
            staging: staging?.id,
            raw_t: optionName("tnm-t", row.t),
            raw_n: optionName("tnm-n", row.n),
            raw_m: optionName("tnm-m", row.m),
            raw_stage: optionName("tnm-stages", row.stage),
            staged_at: row.staged_at,
          });
        });
    const molecularTests = new Map<string, Record<string, unknown>>();
    molecular
      .filter((row) => row.gene || row.method)
      .forEach((row) => {
        const method = toNumber(row.method);
        const specimen = toNumber(row.specimen);
        const testedAt = row.tested_at || undefined;
        const key = [row.panel_version || "", testedAt ?? "", method ?? "", specimen ?? ""].join("|");
        const test = molecularTests.get(key) ?? {
          panel_version: toNumber(row.panel_version),
          specimen_collected_on: row.specimen_collected_on || undefined,
          tested_on: testedAt,
          reported_on: row.reported_on || undefined,
          qc_status: row.qc_status || undefined,
          laboratory: row.laboratory || undefined,
          accession_number: row.accession_number || undefined,
          notes: row.notes || undefined,
          method,
          specimen,
          results: [] as Array<Record<string, unknown>>,
        };
        (test.results as Array<Record<string, unknown>>).push(
          compact({
            gene: toNumber(row.gene),
            exon: toNumber(row.exon),
            alteration_type: toNumber(row.alteration_type),
            result: toNumber(row.result),
            panel_target: toNumber(row.panel_target),
            partner_gene: toNumber(row.partner_gene),
            clinical_significance: toNumber(row.clinical_significance),
            dna_change: row.dna_change || undefined,
            protein_change: row.protein_change || undefined,
            common_name: row.common_name || undefined,
            variant_allele_frequency: toNumber(row.variant_allele_frequency),
            copy_number: toNumber(row.copy_number),
            notes: row.notes || undefined,
          }),
        );
        molecularTests.set(key, test);
      });
    const responsePayload = (row: ResponseRow) => {
      if (
        !row.assessed_at &&
        !row.target_lesion &&
        !row.non_target_lesion &&
        !row.new_lesion &&
        !row.response_result &&
        !row.response_category &&
        !row.residual_viable_tumor_percentage &&
        !row.tumor_regression_grade
      )
        return [];
      return [
        compact({
          assessed_at: row.assessed_at,
          target_lesion: toNumber(row.target_lesion),
          non_target_lesion: toNumber(row.non_target_lesion),
          new_lesion: toNumber(row.new_lesion),
          response_result: toNumber(row.response_result),
          progression_sites: ids(row.progression_sites),
          estimation_method: toNumber(row.estimation_method),
          response_category: toNumber(row.response_category),
          residual_viable_tumor_percentage: toNumber(row.residual_viable_tumor_percentage),
          tumor_regression_grade: toNumber(row.tumor_regression_grade),
        }),
      ];
    };
    return {
      ...(existingPatientId ? { existing_patient_id: existingPatientId } : {}),
      ...(draftObservationId
        ? { draft_observation_id: draftObservationId }
        : {}),
      ...(isDraft
        ? {
            draft_form_state: {
              patient,
              observation,
              history,
              smoking,
              tbHistory,
              covidHistory,
              comorbidities,
              diagnosis,
              clinicalTnm,
              pathologicalTnm,
              pathologicalDetails,
              ihcPanels,
              pastTreatments,
              molecular,
              markers,
              treatments,
              surgeries,
              radiotherapySchedules,
            },
          }
        : {}),
      patient: compact({
        ...patient,
        sex: toNumber(patient.sex),
        district: toNumber(patient.district),
        thana: toNumber(patient.thana),
        blood_group: toNumber(patient.blood_group),
        economic_status: toNumber(patient.economic_status),
        type_of_patient: toNumber(patient.type_of_patient),
        age: toNumber(patient.age),
      }),
      observation: compact({
        ...observation,
        observed_at: observation.observed_at
          ? `${observation.observed_at}T00:00:00+06:00`
          : undefined,
        prescription_age_years: toNumber(observation.prescription_age_years),
        prescription_age_months: toNumber(observation.prescription_age_months),
        prescription_age_days: toNumber(observation.prescription_age_days),
        is_draft: isDraft,
      }),
      history: compact({
        ...history,
        marital_status: toNumber(history.marital_status),
        history_of_alcohol_consumption: toNumber(
          history.history_of_alcohol_consumption,
        ),
        height_cm: toNumber(history.height_cm),
        weight_kg: toNumber(history.weight_kg),
      }),
      smoking_history_records: smoking
        .filter((row) => row.smoking_history)
        .map((row) =>
          compact({
            smoking_history: toNumber(row.smoking_history),
            cigarettes_per_day: toNumber(row.cigarettes_per_day),
            smoking_duration_in_years: toNumber(row.smoking_duration_in_years),
            quit_smoking_for_years: toNumber(row.quit_smoking_for_years),
          }),
        ),
      tb_history_records: tbHistory
        .filter((row) => row.tb_history)
        .map((row) =>
          compact({
            tb_history: toNumber(row.tb_history),
            tb_treatment_start_date: row.tb_treatment_start_date,
            treatment_details: row.treatment_details,
          }),
        ),
      covid_history_records: covidHistory
        .filter((row) => row.covid_history)
        .map((row) =>
          compact({
            covid_history: toNumber(row.covid_history),
            covid_infection_date: row.covid_infection_date,
            vaccine_name: toNumber(row.vaccine_name),
            vaccination_dose: toNumber(row.vaccination_dose),
          }),
        ),
      comorbidities: ids(comorbidities).map((comorbidity) => ({ comorbidity })),
      diagnoses:
        diagnosis.disease_group || diagnosis.primary_site
          ? [
              compact({
                disease_group: toNumber(diagnosis.disease_group),
                disease_subgroup: toNumber(diagnosis.disease_subgroup),
                primary_site: toNumber(diagnosis.primary_site),
                laterality: toNumber(diagnosis.laterality),
                metastatic_sites: ids(diagnosis.metastatic_sites),
                diagnosis_in_details: diagnosis.diagnosis_in_details,
              }),
            ]
          : [],
      histopathologies:
        diagnosis.histopathology_details || diagnosis.histopathology_type
          ? [
              compact({
                biopsy_date: diagnosis.biopsy_date,
                histopathology_details: toNumber(
                  diagnosis.histopathology_details,
                ),
                histopathology_type: toNumber(diagnosis.histopathology_type),
                histopathology_site: toNumber(diagnosis.histopathology_site),
                histopathology_grade: toNumber(diagnosis.histopathology_grade),
              }),
            ]
          : [],
      clinical_tnm_stagings: tnmPayload(clinicalTnm, "clinical-tnm-stagings"),
      pathological_tnm_stagings: tnmPayload(
        pathologicalTnm,
        "pathological-tnm-stagings",
      ),
      pathological_staging_details: Object.values(pathologicalDetails).some(
        Boolean,
      )
        ? [compact(pathologicalDetails)]
        : [],
      molecular_tests: [...molecularTests.values()],
      cancer_markers: markers
        .filter((row) => row.marker_name)
        .map((row) =>
          compact({
            ...row,
            marker_name: toNumber(row.marker_name),
            marker_unit: toNumber(row.marker_unit),
            marker_value: toNumber(row.marker_value),
          }),
        ),
      ihc_panels: ihcPanels
        .filter(
          (panel) =>
            panel.tested_at ||
            panel.results.some((result) => result.cycle) ||
            panel.staging_results.some((result) => result.cycle),
        )
        .map((panel) =>
          compact({
            tested_at: panel.tested_at,
            results: panel.results
              .filter((result) => result.cycle || result.result)
              .map((result) =>
                compact({
                  ...result,
                  tested_at: panel.tested_at,
                  cycle: toNumber(result.cycle),
                  result: toNumber(result.result),
                }),
              ),
            staging_results: panel.staging_results
              .filter((result) => result.cycle || result.result)
              .map((result) =>
                compact({
                  ...result,
                  tested_at: panel.tested_at,
                  cycle: toNumber(result.cycle),
                  result: toNumber(result.result),
                }),
              ),
          }),
        ),
      past_treatment_histories: pastTreatments
        .filter((row) => row.recorded_at || row.details)
        .map((row) => compact(row)),
      treatment_cycles: treatments
        .filter(
          (row) =>
            row.current_treatment_protocol ||
            row.treatment_protocol ||
            row.chemotherapy_details ||
            row.modalities.length ||
            hasResponseData(row.pathological_response) ||
            row.protocol_builders.some(
              (builder) => builder.protocols.length || builder.cycle_no,
            ),
        )
        .map((row) =>
          compact({
            modalities: ids(row.modalities),
            treatment_protocol: toNumber(
              row.protocol_builders[0]?.protocols[0] || row.treatment_protocol,
            ),
            treatment_protocol_cycle: toNumber(row.treatment_protocol_cycle),
            chemo_cycle_no: toNumber(row.chemo_cycle_no),
            current_treatment_protocol:
              row.current_treatment_protocol ||
              protocolSummary(row.protocol_builders) ||
              getOptions("treatment-protocols").find(
                (option) => String(option.id) === row.treatment_protocol,
              )?.name ||
              "",
            protocol_builders: row.protocol_builders
              .filter((builder) => builder.protocols.length || builder.cycle_no)
              .map((builder) =>
                compact({
                  protocol_type: builder.protocol_type,
                  builder_type: builder.protocol_type,
                  cycle_no: builder.cycle_no || undefined,
                  details: builder.protocols
                    .map((id) => optionName("treatment-protocols", id))
                    .filter(Boolean),
                }),
              ),
            chemotherapy_details: row.chemotherapy_details,
            chronology_notes: row.chronology_notes,
            started_at: row.started_at,
            ended_at: row.ended_at,
            line_of_treatment: toNumber(row.line_of_treatment),
            status: row.status,
            reason_for_stopping: row.reason_for_stopping,
            course_notes: row.course_notes,
            administrations: row.administrations.filter((administration) => administration.drug).map((administration) => compact({
              drug: toNumber(administration.drug),
              administered_on: administration.administered_on,
              cycle_number: toNumber(administration.cycle_number),
              day_number: toNumber(administration.day_number),
              dose: toNumber(administration.dose),
              dose_unit: administration.dose_unit,
              status: administration.status,
              notes: administration.notes,
            })),
            outcome: compact({
              disease_progression_status: toNumber(
                row.disease_progression_status,
              ),
              progression_status_date: row.progression_status_date,
              survival_status: toNumber(row.survival_status),
              survival_status_date: row.survival_status_date,
              pfs_months: toNumber(
                inclusiveMonths(
                  history.first_diagnosis_date,
                  row.progression_status_date,
                ),
              ),
              overall_survival_months: toNumber(
                inclusiveMonths(
                  history.first_diagnosis_date,
                  row.survival_status_date,
                ),
              ),
            }),
            recist11_assessments: responsePayload(row.recist),
            irecist_assessments: responsePayload(row.irecist),
            pathological_response_records: responsePayload(
              row.pathological_response,
            ),
          }),
        ),
      surgeries: surgeries
        .filter(
          (row) =>
            row.surgery_modality ||
            row.surgery_date ||
            row.lateralities.length,
        )
        .map((row) =>
          compact({
            surgery_modality: toNumber(row.surgery_modality),
            surgery_date: row.surgery_date,
            lateralities: ids(row.lateralities),
            status: row.status,
            procedure_details: row.procedure_details,
            operative_findings: row.operative_findings,
            complications: row.complications,
            notes: row.notes,
          }),
        ),
      progression_records: progressionRecords
        .filter((record) => record.status && record.assessed_on)
        .map((record) => compact({
          status: toNumber(record.status), assessed_on: record.assessed_on,
          progression_date: record.progression_date || undefined,
          progression_sites: ids(record.progression_sites),
          estimation_method: toNumber(record.estimation_method), notes: record.notes,
        })),
      survival_followups: survivalFollowUps
        .filter((record) => record.status && record.followed_up_on)
        .map((record) => compact({
          status: toNumber(record.status), followed_up_on: record.followed_up_on,
          death_date: record.death_date || undefined, cause_of_death: record.cause_of_death, notes: record.notes,
        })),
      radiotherapy_schedules: radiotherapySchedules
        .filter(
          (row) =>
            row.radiotherapy_intent ||
            row.sites.length ||
            row.modalities.length ||
            row.started_at ||
            row.ended_at ||
            row.fraction_dose ||
            row.fraction_count ||
            row.total_dose,
        )
        .map((row) =>
          compact({
            sites: ids(row.sites),
            radiotherapy_intent: toNumber(row.radiotherapy_intent),
            modalities: ids(row.modalities),
            started_at: row.started_at,
            ended_at: row.ended_at,
            fraction_dose: row.fraction_dose,
            fraction_count: row.fraction_count,
            total_dose: calculatedTotalDose(
              row.fraction_dose,
              row.fraction_count,
            ),
            completed_fractions: toNumber(row.completed_fractions),
            status: row.status,
            reason_for_stopping: row.reason_for_stopping,
            notes: row.notes,
          }),
        ),
    };
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!existingPatientId && !patient.name.trim()) {
      setActiveStep(0);
      setError(
        "Enter the patient's name or select an existing patient before publishing.",
      );
      return;
    }
    saveMutation.mutate(buildPayload(false));
  }

  function saveDraft() {
    setError("");
    setDraftNotice("");
    draftMutation.mutate(buildPayload(true));
  }
  if (optionsQuery.isLoading)
    return (
      <section className="panel state-card">
        <p>Loading controlled clinical options…</p>
      </section>
    );
  if (optionsQuery.isError)
    return (
      <section className="panel state-card">
        <p>Clinical option lists could not be loaded.</p>
      </section>
    );

  return (
    <section className="page-grid">
      <Link className="back-link" to="/patients">
        <ArrowLeft size={16} />
        Back to registry
      </Link>
      <section className="hero-panel hero-panel-tight entry-hero-compact">
        <div className="hero-copy">
          <p className="eyebrow">New structured entry</p>
          <h2>Create patient observation</h2>
          <p className="hero-text">
            A longitudinal patient record using the current normalized registry records.
          </p>
        </div>
        <div className="header-badges">
          <span className="data-pill">Structured records</span>
          <span className="data-pill">Registry API</span>
        </div>
      </section>
      <section className="panel panel-compact">
        <div className="entry-stepper">
          {steps.map((label, index) => (
            <button
              key={label}
              type="button"
              className={
                index === visibleStepIndex
                  ? "entry-step entry-step-active"
                  : index < visibleStepIndex
                    ? "entry-step entry-step-complete"
                    : "entry-step"
              }
              onClick={() => setActiveStep(stepTargets[index])}
            >
              <span>{index + 1}</span>
              <strong>{label}</strong>
            </button>
          ))}
        </div>
      </section>
      <form className="entry-layout" onSubmit={submit}>
        {error ? (
          <p className="entry-error-message" role="alert">
            {error}
          </p>
        ) : null}
        {draftNotice ? (
          <div
            className="entry-modal-backdrop"
            role="presentation"
            onMouseDown={() => setDraftNotice("")}
          >
            <section
              className="entry-modal"
              role="dialog"
              aria-modal="true"
              aria-labelledby="draft-save-title"
              onMouseDown={(event) => event.stopPropagation()}
            >
              <button
                type="button"
                className="entry-modal-close"
                aria-label="Close message"
                onClick={() => setDraftNotice("")}
              >
                <X size={19} />
              </button>
              <p className="eyebrow">Draft status</p>
              <h3 id="draft-save-title">Draft saved</h3>
              <p>{draftNotice}</p>
            </section>
          </div>
        ) : null}
        {resolvedPatientId && clinicalDetailQuery.data ? (
          <PublishedObservationHistory source={clinicalDetailQuery.data} />
        ) : null}
        {activeStep === 0 ? (
          <section className="panel entry-block">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Patient identification</p>
                <h3>Registration, contact, and visit context</h3>
              </div>
            </div>
            <div className="entry-grid">
              <TextField
                label="Hospital registration no."
                value={patient.registration_no}
                onChange={(value) =>
                  setPatient({ ...patient, registration_no: value })
                }
              />
              <TextField
                label="Mobile number"
                value={patient.phone}
                onChange={(value) => setPatient({ ...patient, phone: value })}
              />
              <SelectField
                label="Consultant"
                value={observation.doctor}
                options={getOptions("doctors")}
                onChange={(value) =>
                  setObservation({ ...observation, doctor: value })
                }
              />
              <TextField
                label="Observation date"
                type="date"
                value={observation.observed_at}
                onChange={(value) =>
                  setObservation({ ...observation, observed_at: value })
                }
              />
              <TextField
                label="Prescription date"
                type="date"
                value={observation.prescription_date}
                onChange={(value) =>
                  setObservation({ ...observation, prescription_date: value })
                }
              />
              <SelectField
                label="Center"
                value={observation.center}
                options={getOptions("centers")}
                onChange={(value) =>
                  setObservation({ ...observation, center: value })
                }
              />
              <TextField
                label="Cancer type"
                value={observation.cancer_type}
                onChange={(value) =>
                  setObservation({ ...observation, cancer_type: value })
                }
              />
            </div>
            {patientLookupQuery.data?.count &&
            !patientLookupQuery.data.match ? (
              <p className="entry-inline-note">
                More than one patient matches these identifiers. Use the
                existing record search to select the correct patient.
              </p>
            ) : null}
            {existingPatientId ? (
              <p className="entry-inline-note">
                Existing patient found. Demographic fields were populated from
                the registry.
              </p>
            ) : null}
          </section>
        ) : null}
        {activeStep === 0 ? (
          <>
            <section className="entry-record-check">
              <div className="entry-record-check-copy">
                <span className="entry-record-check-icon">
                  <Search size={18} />
                </span>
                <div>
                  <p className="eyebrow">Existing record check</p>
                  <h3>Search the new Entries registry</h3>
                </div>
              </div>
              <div className="entry-record-lookup">
                <label className="search-label">Patient lookup</label>
                <input
                  className="search-input"
                  value={lookup}
                  onChange={(event) => setLookup(event.target.value)}
                  placeholder="Registry ID, name, phone, or registration no."
                />
              </div>
              {existingPatientId ? (
                <p className="entry-inline-note">
                  Adding a new observation to the selected patient.{" "}
                  <button
                    type="button"
                    className="entry-link-button"
                    onClick={() => setExistingPatientId(null)}
                  >
                    Create a different patient instead
                  </button>
                </p>
              ) : null}
              {existingQuery.data?.results.map((match) => (
                <button
                  type="button"
                  className="entry-match"
                  key={match.id}
                  onClick={() => setExistingPatientId(match.id)}
                >
                  <span>
                    <strong>{match.name}</strong>
                    <small>
                      {match.patient_id} ·{" "}
                      {match.registration_no || "No registration no."}
                    </small>
                  </span>
                  <span className="entry-match-meta">
                    {match.phone}
                    <span>Use patient</span>
                  </span>
                </button>
              ))}
            </section>
            <section className="panel entry-block">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Patient demography</p>
                  <h3>Core patient profile</h3>
                </div>
              </div>
              <div className="entry-grid">
                <TextField
                  label="Registry ID"
                  value={patient.patient_id}
                  required
                  onChange={(value) =>
                    setPatient({ ...patient, patient_id: value })
                  }
                />
                <TextField
                  label="Patient name"
                  value={patient.name}
                  required
                  onChange={(value) => setPatient({ ...patient, name: value })}
                />
                <TextField
                  label="Registration no."
                  value={patient.registration_no}
                  onChange={(value) =>
                    setPatient({ ...patient, registration_no: value })
                  }
                />
                <TextField
                  label="Mobile no."
                  value={patient.phone}
                  onChange={(value) => setPatient({ ...patient, phone: value })}
                />
                <TextField
                  label="Email"
                  type="email"
                  value={patient.email}
                  onChange={(value) => setPatient({ ...patient, email: value })}
                />
                <TextField
                  label="NID"
                  value={patient.nid}
                  onChange={(value) => setPatient({ ...patient, nid: value })}
                />
                <TextField
                  label="Passport"
                  value={patient.passport}
                  onChange={(value) =>
                    setPatient({ ...patient, passport: value })
                  }
                />
                <TextField
                  label="Date of birth"
                  type="date"
                  value={patient.date_of_birth}
                  onChange={(value) =>
                    setPatient({ ...patient, date_of_birth: value })
                  }
                />
                <TextField
                  label="Age"
                  type="number"
                  value={patient.age}
                  onChange={(value) => setPatient({ ...patient, age: value })}
                />
                <SelectField
                  label="Sex"
                  value={patient.sex}
                  options={getOptions("sexes")}
                  onChange={(value) => setPatient({ ...patient, sex: value })}
                />
                <SelectField
                  label="District"
                  value={patient.district}
                  options={getOptions("districts")}
                  onChange={(value) =>
                    setPatient({ ...patient, district: value })
                  }
                />
                <SelectField
                  label="Thana"
                  value={patient.thana}
                  options={thanas}
                  onChange={(value) => setPatient({ ...patient, thana: value })}
                />
                <SelectField
                  label="Blood group"
                  value={patient.blood_group}
                  options={getOptions("blood-groups")}
                  onChange={(value) =>
                    setPatient({ ...patient, blood_group: value })
                  }
                />
                <SelectField
                  label="Economic status"
                  value={patient.economic_status}
                  options={getOptions("economic-statuses")}
                  onChange={(value) =>
                    setPatient({ ...patient, economic_status: value })
                  }
                />
                <SelectField
                  label="Patient type"
                  value={patient.type_of_patient}
                  options={getOptions("patient-types")}
                  onChange={(value) =>
                    setPatient({ ...patient, type_of_patient: value })
                  }
                />
                <TextField
                  label="Area"
                  value={patient.area}
                  onChange={(value) => setPatient({ ...patient, area: value })}
                />
              </div>
            </section>
            <section className="panel entry-block">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Age timeline</p>
                  <h3>Prescription and diagnosis age calculation</h3>
                </div>
              </div>
              <div className="entry-grid">
                <TextField
                  label="Prescription age (years)"
                  type="number"
                  value={observation.prescription_age_years}
                  onChange={(value) => {
                    const next = {
                      ...observation,
                      prescription_age_years: value,
                    };
                    setObservation(next);
                    const dob = dateOfBirthFromPrescriptionAge(
                      next.prescription_date,
                      value,
                      next.prescription_age_months,
                      next.prescription_age_days,
                    );
                    if (dob)
                      setPatient((current) => ({
                        ...current,
                        date_of_birth: dob,
                        age: value,
                      }));
                  }}
                />
                <TextField
                  label="Prescription age (months)"
                  type="number"
                  value={observation.prescription_age_months}
                  onChange={(value) => {
                    const next = {
                      ...observation,
                      prescription_age_months: value,
                    };
                    setObservation(next);
                    const dob = dateOfBirthFromPrescriptionAge(
                      next.prescription_date,
                      next.prescription_age_years,
                      value,
                      next.prescription_age_days,
                    );
                    if (dob)
                      setPatient((current) => ({
                        ...current,
                        date_of_birth: dob,
                      }));
                  }}
                />
                <TextField
                  label="Prescription age (days)"
                  type="number"
                  value={observation.prescription_age_days}
                  onChange={(value) => {
                    const next = {
                      ...observation,
                      prescription_age_days: value,
                    };
                    setObservation(next);
                    const dob = dateOfBirthFromPrescriptionAge(
                      next.prescription_date,
                      next.prescription_age_years,
                      next.prescription_age_months,
                      value,
                    );
                    if (dob)
                      setPatient((current) => ({
                        ...current,
                        date_of_birth: dob,
                      }));
                  }}
                />
                <TextField
                  label="Date of birth (derived)"
                  type="date"
                  value={patient.date_of_birth}
                  onChange={(value) =>
                    setPatient((current) => ({
                      ...current,
                      date_of_birth: value,
                      age: calculatedAge(value, observation.prescription_date),
                    }))
                  }
                />
                <TextField
                  label="Age at prescription (calculated)"
                  value={ageParts(
                    patient.date_of_birth,
                    observation.prescription_date,
                  )}
                  onChange={() => undefined}
                  readOnly
                />
                <TextField
                  label="First diagnosis date"
                  type="date"
                  value={history.first_diagnosis_date}
                  onChange={(value) =>
                    setHistory({ ...history, first_diagnosis_date: value })
                  }
                />
                <TextField
                  label="Age at diagnosis (calculated)"
                  value={ageParts(
                    patient.date_of_birth,
                    history.first_diagnosis_date,
                  )}
                  onChange={() => undefined}
                  readOnly
                />
              </div>
              <p className="entry-inline-note">
                Prescription age is preserved as recorded. Date of birth and
                both displayed ages are derived from the entered dates.
              </p>
            </section>
            <section className="panel entry-block">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">History</p>
                  <h3>Personal and family background</h3>
                </div>
              </div>
              <div className="entry-grid">
                <SelectField
                  label="Marital status"
                  value={history.marital_status}
                  options={getOptions("marital-statuses")}
                  onChange={(value) =>
                    setHistory({ ...history, marital_status: value })
                  }
                />
                <TextField
                  label="Dietary habits"
                  value={history.dietary_habits}
                  onChange={(value) =>
                    setHistory({ ...history, dietary_habits: value })
                  }
                />
                <TextField
                  label="Height (cm)"
                  type="number"
                  value={history.height_cm}
                  onChange={(value) =>
                    setHistory({ ...history, height_cm: value })
                  }
                />
                <TextField
                  label="Weight (kg)"
                  type="number"
                  value={history.weight_kg}
                  onChange={(value) =>
                    setHistory({ ...history, weight_kg: value })
                  }
                />
                <SelectField
                  label="Alcohol history"
                  value={history.history_of_alcohol_consumption}
                  options={getOptions("alcohol-histories")}
                  onChange={(value) =>
                    setHistory({
                      ...history,
                      history_of_alcohol_consumption: value,
                    })
                  }
                />
                <TextField
                  label="Chest radiotherapy history"
                  value={history.radiotherapy_to_chest}
                  onChange={(value) =>
                    setHistory({ ...history, radiotherapy_to_chest: value })
                  }
                />
                <TextField
                  label="Personal/family cancer history"
                  value={history.personal_or_family_history_of_cancer}
                  onChange={(value) =>
                    setHistory({
                      ...history,
                      personal_or_family_history_of_cancer: value,
                    })
                  }
                />
                <TextField
                  label="Personal cancer history"
                  value={history.cancer_history}
                  onChange={(value) =>
                    setHistory({ ...history, cancer_history: value })
                  }
                />
                <TextField
                  label="Family cancer history"
                  value={history.family_cancer_history}
                  onChange={(value) =>
                    setHistory({ ...history, family_cancer_history: value })
                  }
                />
                <TextField
                  label="Known mutations"
                  value={history.any_known_mutations}
                  onChange={(value) =>
                    setHistory({ ...history, any_known_mutations: value })
                  }
                />
                <label className="filter-field entry-span-full">
                  <span>Comorbidities</span>
                  <select
                    multiple
                    className="filter-select entry-multiselect"
                    value={comorbidities}
                    onChange={(event) =>
                      setComorbidities(selectedValues(event))
                    }
                  >
                    {getOptions("comorbidities").map((option) => (
                      <option key={option.id} value={option.id}>
                        {optionLabel(option)}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </section>
            <RepeatableSection
              title="Smoking history"
              onAdd={() => setSmoking([...smoking, blankSmoking()])}
            >
              {smoking.map((row, index) => (
                <div className="entry-grid repeatable-card" key={index}>
                  <SelectField
                    label="Status"
                    value={row.smoking_history}
                    options={getOptions("smoking-histories")}
                    onChange={(value) =>
                      updateRow(setSmoking, index, "smoking_history", value)
                    }
                  />
                  <TextField
                    label="Cigarettes/day"
                    type="number"
                    value={row.cigarettes_per_day}
                    onChange={(value) =>
                      updateRow(setSmoking, index, "cigarettes_per_day", value)
                    }
                  />
                  <TextField
                    label="Smoking duration (years)"
                    type="number"
                    value={row.smoking_duration_in_years}
                    onChange={(value) =>
                      updateRow(
                        setSmoking,
                        index,
                        "smoking_duration_in_years",
                        value,
                      )
                    }
                  />
                  <TextField
                    label="Quit smoking for (years)"
                    type="number"
                    value={row.quit_smoking_for_years}
                    onChange={(value) =>
                      updateRow(
                        setSmoking,
                        index,
                        "quit_smoking_for_years",
                        value,
                      )
                    }
                  />
                  <RemoveButton
                    show={smoking.length > 1}
                    onClick={() =>
                      setSmoking(
                        smoking.filter((_, rowIndex) => rowIndex !== index),
                      )
                    }
                  />
                </div>
              ))}
            </RepeatableSection>
            <section className="insight-grid insight-grid-dense">
              <RepeatableSection
                title="TB history"
                onAdd={() => setTbHistory([...tbHistory, blankTb()])}
              >
                {tbHistory.map((row, index) => (
                  <div className="entry-grid repeatable-card" key={index}>
                    <SelectField
                      label="Status"
                      value={row.tb_history}
                      options={getOptions("tb-histories")}
                      onChange={(value) =>
                        updateRow(setTbHistory, index, "tb_history", value)
                      }
                    />
                    <TextField
                      label="Treatment started"
                      type="date"
                      value={row.tb_treatment_start_date}
                      onChange={(value) =>
                        updateRow(
                          setTbHistory,
                          index,
                          "tb_treatment_start_date",
                          value,
                        )
                      }
                    />
                    <TextField
                      label="Treatment details"
                      value={row.treatment_details}
                      onChange={(value) =>
                        updateRow(
                          setTbHistory,
                          index,
                          "treatment_details",
                          value,
                        )
                      }
                    />
                    <RemoveButton
                      show={tbHistory.length > 1}
                      onClick={() =>
                        setTbHistory(
                          tbHistory.filter((_, rowIndex) => rowIndex !== index),
                        )
                      }
                    />
                  </div>
                ))}
              </RepeatableSection>
              <RepeatableSection
                title="COVID and vaccination"
                onAdd={() => setCovidHistory([...covidHistory, blankCovid()])}
              >
                {covidHistory.map((row, index) => (
                  <div className="entry-grid repeatable-card" key={index}>
                    <SelectField
                      label="COVID history"
                      value={row.covid_history}
                      options={getOptions("covid-histories")}
                      onChange={(value) =>
                        updateRow(
                          setCovidHistory,
                          index,
                          "covid_history",
                          value,
                        )
                      }
                    />
                    <TextField
                      label="Infection date"
                      type="date"
                      value={row.covid_infection_date}
                      onChange={(value) =>
                        updateRow(
                          setCovidHistory,
                          index,
                          "covid_infection_date",
                          value,
                        )
                      }
                    />
                    <SelectField
                      label="Vaccine"
                      value={row.vaccine_name}
                      options={getOptions("vaccines")}
                      onChange={(value) =>
                        updateRow(setCovidHistory, index, "vaccine_name", value)
                      }
                    />
                    <SelectField
                      label="Vaccination dose"
                      value={row.vaccination_dose}
                      options={getOptions("vaccination-doses")}
                      onChange={(value) =>
                        updateRow(
                          setCovidHistory,
                          index,
                          "vaccination_dose",
                          value,
                        )
                      }
                    />
                    <RemoveButton
                      show={covidHistory.length > 1}
                      onClick={() =>
                        setCovidHistory(
                          covidHistory.filter(
                            (_, rowIndex) => rowIndex !== index,
                          ),
                        )
                      }
                    />
                  </div>
                ))}
              </RepeatableSection>
            </section>
          </>
        ) : null}
        {activeStep === 2 ? (
          <>
            <section className="panel entry-block">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Diagnosis</p>
                  <h3>Disease framing</h3>
                </div>
              </div>
              <div className="entry-grid">
                <SelectField
                  label="Disease group"
                  value={diagnosis.disease_group}
                  options={getOptions("diagnosis-disease-groups")}
                  onChange={(value) =>
                    setDiagnosis({
                      ...diagnosis,
                      disease_group: value,
                      disease_subgroup: "",
                    })
                  }
                />
                <SelectField
                  label="Disease subgroup"
                  value={diagnosis.disease_subgroup}
                  options={subgroups}
                  onChange={(value) =>
                    setDiagnosis({ ...diagnosis, disease_subgroup: value })
                  }
                />
                <SelectField
                  label="Primary site"
                  value={diagnosis.primary_site}
                  options={getOptions("diagnosis-primary-sites")}
                  onChange={(value) =>
                    setDiagnosis({ ...diagnosis, primary_site: value })
                  }
                />
                <SelectField
                  label="Laterality"
                  value={diagnosis.laterality}
                  options={getOptions("diagnosis-lateralities")}
                  onChange={(value) =>
                    setDiagnosis({ ...diagnosis, laterality: value })
                  }
                />
              </div>
            </section>
            <section className="insight-grid insight-grid-dense">
              <section className="panel entry-block">
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">Diagnosis details</p>
                    <h3>Clinical narrative</h3>
                  </div>
                </div>
                <div className="entry-grid">
                  <TextArea
                    label="Diagnosis in details"
                    value={diagnosis.diagnosis_in_details}
                    onChange={(value) =>
                      setDiagnosis({
                        ...diagnosis,
                        diagnosis_in_details: value,
                      })
                    }
                  />
                </div>
              </section>
              <RepeatableSection
                title="Past treatment history"
                onAdd={() =>
                  setPastTreatments([...pastTreatments, blankPastTreatment()])
                }
              >
                {pastTreatments.map((row, index) => (
                  <div className="entry-grid repeatable-card" key={index}>
                    <TextField
                      label="Recorded date"
                      type="date"
                      value={row.recorded_at}
                      onChange={(value) =>
                        updateRow(
                          setPastTreatments,
                          index,
                          "recorded_at",
                          value,
                        )
                      }
                    />
                    <TextArea
                      label="Treatment details"
                      value={row.details}
                      fullWidth={false}
                      className="entry-span-two"
                      onChange={(value) =>
                        updateRow(setPastTreatments, index, "details", value)
                      }
                    />
                    <RemoveButton
                      show={pastTreatments.length > 1}
                      onClick={() =>
                        setPastTreatments(
                          pastTreatments.filter(
                            (_, rowIndex) => rowIndex !== index,
                          ),
                        )
                      }
                    />
                  </div>
                ))}
              </RepeatableSection>
            </section>
            <section className="panel entry-block">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Pathology</p>
                  <h3>Histopathology</h3>
                </div>
              </div>
              <div className="entry-grid">
                <TextField
                  label="Biopsy date"
                  type="date"
                  value={diagnosis.biopsy_date}
                  onChange={(value) =>
                    setDiagnosis({ ...diagnosis, biopsy_date: value })
                  }
                />
                <SelectField
                  label="Histopathology type"
                  value={diagnosis.histopathology_type}
                  options={getOptions("histopathology-types")}
                  onChange={(value) =>
                    setDiagnosis({ ...diagnosis, histopathology_type: value })
                  }
                />
                <SelectField
                  label="Histopathology site"
                  value={diagnosis.histopathology_site}
                  options={getOptions("histopathology-sites")}
                  onChange={(value) =>
                    setDiagnosis({ ...diagnosis, histopathology_site: value })
                  }
                />
                <SelectField
                  label="Histopathology detail"
                  value={diagnosis.histopathology_details}
                  options={getOptions("histopathology-details")}
                  onChange={(value) =>
                    setDiagnosis({
                      ...diagnosis,
                      histopathology_details: value,
                    })
                  }
                />
                <RadioGroup
                  label="Histopathology grade"
                  value={diagnosis.histopathology_grade}
                  options={getOptions("histopathology-grades")}
                  onChange={(value) =>
                    setDiagnosis({ ...diagnosis, histopathology_grade: value })
                  }
                />
              </div>
            </section>
            <section className="insight-grid insight-grid-dense entry-pathology-workflows">
              <CollapsibleSection
                title="IHC cycle"
                onAdd={() => setIhcPanels([...ihcPanels, blankIhcPanel()])}
              >
                {ihcPanels.map((panel, panelIndex) => (
                  <IHCPanelMatrix
                    key={panelIndex}
                    panel={panel}
                    panelIndex={panelIndex}
                    cycles={uniqueOptions(getOptions("ihc-cycles"))}
                    resultOptions={uniqueOptions(
                      getOptions("ihc-cycle-results"),
                    )}
                    onTestedAtChange={(tested_at) =>
                      setIhcPanels((current) =>
                        current.map((item, index) =>
                          index === panelIndex ? { ...item, tested_at } : item,
                        ),
                      )
                    }
                    onResultChange={(cycle, result) =>
                      setIhcPanels((current) =>
                        current.map((item, index) =>
                          index === panelIndex
                            ? {
                                ...item,
                                results: [
                                  ...item.results.filter(
                                    (row) => row.cycle !== cycle,
                                  ),
                                  {
                                    ...blankIhcResult(),
                                    cycle,
                                    result,
                                    tested_at: item.tested_at,
                                  },
                                ],
                              }
                            : item,
                        ),
                      )
                    }
                  />
                ))}
              </CollapsibleSection>
              <CollapsibleSection
                eyebrow="Pathological staging"
                title="LVSI, PNI, margin, and Ki-67"
              >
                <PathologicalStagingMatrix
                  details={pathologicalDetails}
                  onChange={(key, value) =>
                    setPathologicalDetails((current) => ({
                      ...current,
                      [key]: value,
                    }))
                  }
                />
              </CollapsibleSection>
            </section>
            <RepeatableSection
              title="Molecular pathology"
              onAdd={() => setMolecular([...molecular, blankMolecular()])}
            >
              {molecular.map((row, index) => (
                <div className="entry-grid repeatable-card" key={index}>
                  <SelectField
                    label="Panel version"
                    value={row.panel_version}
                    options={getOptions("molecular-panel-versions")}
                    onChange={(value) => updateRow(setMolecular, index, "panel_version", value)}
                  />
                  <SelectField
                    label="Panel target"
                    value={row.panel_target}
                    options={getOptions("molecular-panel-targets").filter(
                      (option) => !row.panel_version || String(option.panel_version) === row.panel_version,
                    )}
                    onChange={(value) => {
                      const target = getOptions("molecular-panel-targets").find(
                        (option) => String(option.id) === value,
                      );
                      setMolecular((rows) => rows.map((item, itemIndex) =>
                        itemIndex === index
                          ? {
                              ...item,
                              panel_target: value,
                              gene: String(target?.gene ?? item.gene),
                              alteration_type: String(target?.alteration_type ?? item.alteration_type),
                            }
                          : item,
                      ));
                    }}
                  />
                  <TextField
                    label="Specimen collected on"
                    type="date"
                    value={row.specimen_collected_on}
                    onChange={(value) =>
                      updateRow(setMolecular, index, "specimen_collected_on", value)
                    }
                  />
                  <TextField label="Tested on" type="date" value={row.tested_at} onChange={(value) => updateRow(setMolecular, index, "tested_at", value)} />
                  <TextField label="Reported on" type="date" value={row.reported_on} onChange={(value) => updateRow(setMolecular, index, "reported_on", value)} />
                  <SelectField
                    label="Method"
                    value={row.method}
                    options={getOptions("molecular-methods")}
                    onChange={(value) =>
                      updateRow(setMolecular, index, "method", value)
                    }
                  />
                  <SelectField
                    label="Specimen"
                    value={row.specimen}
                    options={getOptions("molecular-specimens")}
                    onChange={(value) =>
                      updateRow(setMolecular, index, "specimen", value)
                    }
                  />
                  <SelectField
                    label="Gene"
                    value={row.gene}
                    options={getOptions("molecular-genes")}
                    onChange={(value) =>
                      updateRow(setMolecular, index, "gene", value)
                    }
                  />
                  <SelectField
                    label="Exon"
                    value={row.exon}
                    options={getOptions("molecular-exons").filter(
                      (option) => !row.gene || String(option.gene) === row.gene,
                    )}
                    onChange={(value) =>
                      updateRow(setMolecular, index, "exon", value)
                    }
                  />
                  <SelectField
                    label="Alteration type"
                    value={row.alteration_type}
                    options={getOptions("molecular-alteration-types")}
                    onChange={(value) =>
                      updateRow(setMolecular, index, "alteration_type", value)
                    }
                    required
                  />
                  <SelectField
                    label="Partner gene"
                    value={row.partner_gene}
                    options={getOptions("molecular-genes")}
                    onChange={(value) => updateRow(setMolecular, index, "partner_gene", value)}
                  />
                  <SelectField
                    label="Result"
                    value={row.result}
                    options={getOptions("molecular-results")}
                    onChange={(value) =>
                      updateRow(setMolecular, index, "result", value)
                    }
                  />
                  <SelectField label="Clinical significance" value={row.clinical_significance} options={getOptions("molecular-clinical-significances")} onChange={(value) => updateRow(setMolecular, index, "clinical_significance", value)} />
                  <TextField label="Laboratory" value={row.laboratory} onChange={(value) => updateRow(setMolecular, index, "laboratory", value)} />
                  <TextField label="Accession number" value={row.accession_number} onChange={(value) => updateRow(setMolecular, index, "accession_number", value)} />
                  <TextField label="DNA change" value={row.dna_change} onChange={(value) => updateRow(setMolecular, index, "dna_change", value)} />
                  <TextField label="Protein change" value={row.protein_change} onChange={(value) => updateRow(setMolecular, index, "protein_change", value)} />
                  <TextField label="Common name" value={row.common_name} onChange={(value) => updateRow(setMolecular, index, "common_name", value)} />
                  <TextField label="Variant allele frequency (%)" type="number" value={row.variant_allele_frequency} onChange={(value) => updateRow(setMolecular, index, "variant_allele_frequency", value)} />
                  <TextField label="Copy number" type="number" value={row.copy_number} onChange={(value) => updateRow(setMolecular, index, "copy_number", value)} />
                  <TextArea label="Molecular notes" value={row.notes} onChange={(value) => updateRow(setMolecular, index, "notes", value)} />
                  <RemoveButton
                    show={molecular.length > 1}
                    onClick={() =>
                      setMolecular(
                        molecular.filter((_, rowIndex) => rowIndex !== index),
                      )
                    }
                  />
                </div>
              ))}
            </RepeatableSection>
            <RepeatableSection
              title="Cancer markers"
              onAdd={() => setMarkers([...markers, blankMarker()])}
            >
              {markers.map((row, index) => (
                <div className="entry-grid repeatable-card" key={index}>
                  <SelectField
                    label="Marker"
                    value={row.marker_name}
                    options={getOptions("cancer-marker-names")}
                    onChange={(value) =>
                      updateRow(setMarkers, index, "marker_name", value)
                    }
                  />
                  <TextField
                    label="Unit"
                    value={String(
                      getOptions("cancer-marker-names").find(
                        (option) => String(option.id) === row.marker_name,
                      )?.unit ?? "",
                    )}
                    onChange={() => undefined}
                    readOnly
                  />
                  <TextField
                    label="Value"
                    type="number"
                    value={row.marker_value}
                    onChange={(value) =>
                      updateRow(setMarkers, index, "marker_value", value)
                    }
                  />
                  <TextField
                    label="Test date"
                    type="date"
                    value={row.tested_at}
                    onChange={(value) =>
                      updateRow(setMarkers, index, "tested_at", value)
                    }
                  />
                  <RemoveButton
                    show={markers.length > 1}
                    onClick={() =>
                      setMarkers(
                        markers.filter((_, rowIndex) => rowIndex !== index),
                      )
                    }
                  />
                </div>
              ))}
            </RepeatableSection>
          </>
        ) : null}
        {activeStep === 3 ? (
          <>
            <RepeatableSection
              title="Treatment protocols"
              onAdd={() => setTreatments([...treatments, blankTreatment()])}
            >
              {treatments.map((row, index) => (
                <div className="entry-grid repeatable-card" key={index}>
                  <InlineCheckboxGroup
                    label="Treatment modalities"
                    options={getOptions("treatment-modalities")}
                    value={row.modalities}
                    onChange={(modalities) =>
                      updateRow(setTreatments, index, "modalities", modalities)
                    }
                  />
                  <TextArea
                    label="Current treatment protocol"
                    value={row.current_treatment_protocol}
                    onChange={(value) =>
                      updateRow(
                        setTreatments,
                        index,
                        "current_treatment_protocol",
                        value,
                      )
                    }
                  />
                  <TextField
                    label="Date of starting"
                    type="date"
                    value={row.started_at}
                    onChange={(value) =>
                      updateRow(setTreatments, index, "started_at", value)
                    }
                  />
                  <TextField
                    label="Date of ending"
                    type="date"
                    value={row.ended_at}
                    onChange={(value) =>
                      updateRow(setTreatments, index, "ended_at", value)
                    }
                  />
                  <SelectField
                    label="Line of treatment"
                    value={row.line_of_treatment}
                    options={getOptions("lines-of-treatment")}
                    onChange={(value) =>
                      updateRow(
                        setTreatments,
                        index,
                        "line_of_treatment",
                        value,
                      )
                    }
                  />
                  <StatusField label="Course status" value={row.status} choices={courseStatuses} onChange={(value) => updateRow(setTreatments, index, "status", value)} />
                  <TextArea label="Reason for stopping" value={row.reason_for_stopping} onChange={(value) => updateRow(setTreatments, index, "reason_for_stopping", value)} />
                  <TextArea label="Course notes" value={row.course_notes} onChange={(value) => updateRow(setTreatments, index, "course_notes", value)} />
                  <TextField
                    label="Cycle no."
                    type="number"
                    value={row.chemo_cycle_no}
                    onChange={(value) =>
                      updateRow(setTreatments, index, "chemo_cycle_no", value)
                    }
                  />
                  <section className="entry-protocol-builder entry-span-full">
                    <div className="entry-protocol-builder-head">
                      <div>
                        <p className="eyebrow">Protocol builder</p>
                        <h4>Build the treatment sequence</h4>
                      </div>
                    </div>
                    {row.protocol_builders.map((builder, builderIndex) => (
                      <div className="entry-protocol-phase" key={builderIndex}>
                        <div className="entry-protocol-phase-head">
                          <strong>
                            {builderIndex === 0
                              ? "Treatment protocol"
                              : "Followed by"}
                          </strong>
                          {builderIndex > 0 ? (
                            <button
                              type="button"
                              className="text-button danger-button"
                              onClick={() =>
                                updateRow(
                                  setTreatments,
                                  index,
                                  "protocol_builders",
                                  row.protocol_builders.filter(
                                    (_, phaseIndex) =>
                                      phaseIndex !== builderIndex,
                                  ),
                                )
                              }
                            >
                              Remove
                            </button>
                          ) : null}
                        </div>
                        <div className="entry-grid entry-protocol-phase-fields">
                          <div className="entry-protocol-regimens">
                            {(builder.protocols.length
                              ? builder.protocols
                              : [""]
                            ).map((protocolId, protocolIndex) => (
                              <div
                                className="entry-protocol-regimen-row"
                                key={`${builderIndex}-${protocolIndex}`}
                              >
                                <SelectField
                                  label={
                                    protocolIndex === 0
                                      ? "Protocol"
                                      : "Combined with"
                                  }
                                  value={protocolId}
                                  options={getOptions("treatment-protocols")}
                                  onChange={(value) =>
                                    updateRow(
                                      setTreatments,
                                      index,
                                      "protocol_builders",
                                      row.protocol_builders.map(
                                        (phase, phaseIndex) => {
                                          if (phaseIndex !== builderIndex)
                                            return phase;
                                          const protocols = phase.protocols
                                            .length
                                            ? [...phase.protocols]
                                            : [""];
                                          protocols[protocolIndex] = value;
                                          return {
                                            ...phase,
                                            protocols: protocols.filter(Boolean),
                                          };
                                        },
                                      ),
                                    )
                                  }
                                />
                                <div className="entry-protocol-regimen-actions">
                                  {builder.protocols.length > 1 ? (
                                    <button
                                      type="button"
                                      className="entry-protocol-icon-button entry-protocol-remove-button"
                                      aria-label="Remove protocol from this combined regimen"
                                      title="Remove protocol"
                                      onClick={() =>
                                        updateRow(
                                          setTreatments,
                                          index,
                                          "protocol_builders",
                                          row.protocol_builders.map(
                                            (phase, phaseIndex) =>
                                              phaseIndex === builderIndex
                                                ? {
                                                    ...phase,
                                                    protocols:
                                                      phase.protocols.filter(
                                                        (_, itemIndex) =>
                                                          itemIndex !==
                                                          protocolIndex,
                                                      ),
                                                  }
                                                : phase,
                                          ),
                                        )
                                      }
                                    >
                                      <Trash2 size={17} />
                                    </button>
                                  ) : null}
                                </div>
                              </div>
                            ))}
                            <p className="entry-protocol-helper">
                              Use + to combine protocols in this phase.
                            </p>
                          </div>
                          <button
                            type="button"
                            className="entry-protocol-icon-button entry-protocol-add-button"
                            aria-label="Add protocol to this combined regimen"
                            title="Add protocol to this combined regimen"
                            onClick={() =>
                              updateRow(
                                setTreatments,
                                index,
                                "protocol_builders",
                                row.protocol_builders.map(
                                  (phase, phaseIndex) =>
                                    phaseIndex === builderIndex
                                      ? {
                                          ...phase,
                                          protocols: [...phase.protocols, ""],
                                        }
                                      : phase,
                                ),
                              )
                            }
                          >
                            <Plus size={20} />
                          </button>
                          <TextField
                            label="Cycle no."
                            type="number"
                            value={builder.cycle_no}
                            onChange={(value) =>
                              updateRow(
                                setTreatments,
                                index,
                                "protocol_builders",
                                row.protocol_builders.map(
                                  (phase, phaseIndex) =>
                                    phaseIndex === builderIndex
                                      ? { ...phase, cycle_no: value }
                                      : phase,
                                ),
                              )
                            }
                          />
                        </div>
                      </div>
                    ))}
                    <div className="entry-protocol-builder-actions">
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() =>
                          updateRow(setTreatments, index, "protocol_builders", [
                            ...row.protocol_builders,
                            blankProtocolBuilder("followed_by"),
                          ])
                        }
                      >
                        <Plus size={16} /> Followed by
                      </button>
                    </div>
                    <div className="entry-protocol-summary">
                      <span>Current treatment protocol</span>
                      <strong>
                        {row.protocol_builders
                          .filter((phase) => phase.protocols.length)
                          .map((phase) => {
                            const name = phase.protocols
                              .map((protocolId) => {
                                const protocol = getOptions(
                                  "treatment-protocols",
                                ).find(
                                  (option) =>
                                    String(option.id) === protocolId,
                                );
                                return protocol ? optionLabel(protocol) : "";
                              })
                              .filter(Boolean)
                              .join(" + ");
                            return `${phase.protocol_type === "followed_by" ? "Followed by " : ""}${name}${phase.cycle_no ? ` (${phase.cycle_no} cycle${phase.cycle_no === "1" ? "" : "s"})` : ""}`;
                          })
                          .join("; ") ||
                          "Add a protocol to generate the treatment sequence."}
                      </strong>
                    </div>
                  </section>
                  <TextArea
                    label="Treatment details (chronology)"
                    value={row.chemotherapy_details}
                    onChange={(value) =>
                      updateRow(
                        setTreatments,
                        index,
                        "chemotherapy_details",
                        value,
                      )
                    }
                  />
                  <section className="entry-span-full entry-response-assessments">
                    <div className="entry-response-assessments-head"><div><p className="eyebrow">Treatment administration</p><h4>Drug doses and cycle events</h4></div><button type="button" className="secondary-button" onClick={() => updateRow(setTreatments, index, "administrations", [...row.administrations, blankTreatmentAdministration()])}><Plus size={16} /> Add administration</button></div>
                    {row.administrations.map((administration, administrationIndex) => <div className="entry-grid repeatable-card" key={administrationIndex}>
                      <SelectField label="Drug" value={administration.drug} options={getOptions("treatment-drugs")} onChange={(value) => updateRow(setTreatments, index, "administrations", row.administrations.map((item, itemIndex) => itemIndex === administrationIndex ? { ...item, drug: value } : item))} required />
                      <TextField label="Administered on" type="date" value={administration.administered_on} onChange={(value) => updateRow(setTreatments, index, "administrations", row.administrations.map((item, itemIndex) => itemIndex === administrationIndex ? { ...item, administered_on: value } : item))} />
                      <TextField label="Cycle number" type="number" value={administration.cycle_number} onChange={(value) => updateRow(setTreatments, index, "administrations", row.administrations.map((item, itemIndex) => itemIndex === administrationIndex ? { ...item, cycle_number: value } : item))} />
                      <TextField label="Day number" type="number" value={administration.day_number} onChange={(value) => updateRow(setTreatments, index, "administrations", row.administrations.map((item, itemIndex) => itemIndex === administrationIndex ? { ...item, day_number: value } : item))} />
                      <TextField label="Dose" type="number" value={administration.dose} onChange={(value) => updateRow(setTreatments, index, "administrations", row.administrations.map((item, itemIndex) => itemIndex === administrationIndex ? { ...item, dose: value } : item))} />
                      <TextField label="Dose unit" value={administration.dose_unit} onChange={(value) => updateRow(setTreatments, index, "administrations", row.administrations.map((item, itemIndex) => itemIndex === administrationIndex ? { ...item, dose_unit: value } : item))} />
                      <StatusField label="Administration status" value={administration.status} choices={[["planned", "Planned"], ["given", "Given"], ["delayed", "Delayed"], ["held", "Held"], ["cancelled", "Cancelled"]]} onChange={(value) => updateRow(setTreatments, index, "administrations", row.administrations.map((item, itemIndex) => itemIndex === administrationIndex ? { ...item, status: value } : item))} />
                      <TextArea label="Administration notes" value={administration.notes} onChange={(value) => updateRow(setTreatments, index, "administrations", row.administrations.map((item, itemIndex) => itemIndex === administrationIndex ? { ...item, notes: value } : item))} />
                      <RemoveButton show onClick={() => updateRow(setTreatments, index, "administrations", row.administrations.filter((_, itemIndex) => itemIndex !== administrationIndex))} />
                    </div>)}
                  </section>
                  <section className="entry-response-assessments entry-span-full">
                    <div className="entry-response-assessments-head">
                      <div>
                        <p className="eyebrow">Response assessment</p>
                        <h4>RECIST response assessments</h4>
                      </div>
                    </div>
                    <div className="entry-response-assessment-grid">
                      <ResponseAssessmentCard
                        title="RECIST 1.1"
                        row={row.recist}
                        getOptions={getOptions}
                        resources={{
                          target: "recist-target-lesions",
                          nonTarget: "recist-non-target-lesions",
                          newLesion: "recist-new-lesions",
                          result: "recist-response-results",
                        }}
                        onChange={(recist) =>
                          updateRow(setTreatments, index, "recist", recist)
                        }
                      />
                      <ResponseAssessmentCard
                        title="iRECIST"
                        row={row.irecist}
                        getOptions={getOptions}
                        resources={{
                          target: "irecist-target-lesions",
                          nonTarget: "irecist-non-target-lesions",
                          newLesion: "irecist-new-lesions",
                          result: "irecist-response-results",
                        }}
                        onChange={(irecist) =>
                          updateRow(setTreatments, index, "irecist", irecist)
                        }
                      />
                    </div>
                  </section>
                  {/* LEGACY_UI: superseded by the independent progression and survival forms below. */}
                  <section className="entry-outcome-card entry-span-full" hidden aria-hidden="true">
                    <div className="entry-response-assessments-head">
                      <div>
                        <p className="eyebrow">Treatment outcomes</p>
                        <h4>Progression, survival, and calculated duration</h4>
                      </div>
                    </div>
                    <div className="entry-grid">
                      <SelectField
                        label="Disease progression status"
                        value={row.disease_progression_status}
                        options={getOptions("disease-progression-statuses")}
                        onChange={(value) =>
                          updateRow(
                            setTreatments,
                            index,
                            "disease_progression_status",
                            value,
                          )
                        }
                      />
                      <TextField
                        label="Progression date"
                        type="date"
                        value={row.progression_status_date}
                        onChange={(value) =>
                          updateRow(
                            setTreatments,
                            index,
                            "progression_status_date",
                            value,
                          )
                        }
                      />
                      <SelectField
                        label="Survival status"
                        value={row.survival_status}
                        options={getOptions("survival-statuses")}
                        onChange={(value) =>
                          updateRow(
                            setTreatments,
                            index,
                            "survival_status",
                            value,
                          )
                        }
                      />
                      <TextField
                        label="Survival status date"
                        type="date"
                        value={row.survival_status_date}
                        onChange={(value) =>
                          updateRow(
                            setTreatments,
                            index,
                            "survival_status_date",
                            value,
                          )
                        }
                      />
                      <TextField
                        label="PFS (calculated months)"
                        value={inclusiveMonths(
                          history.first_diagnosis_date,
                          row.progression_status_date,
                        )}
                        onChange={() => undefined}
                        readOnly
                      />
                      <TextField
                        label="Overall survival (calculated months)"
                        value={inclusiveMonths(
                          history.first_diagnosis_date,
                          row.survival_status_date,
                        )}
                        onChange={() => undefined}
                        readOnly
                      />
                    </div>
                    <p className="entry-outcome-note">
                      Calculated from first diagnosis date to the recorded
                      progression or survival date, using the legacy
                      inclusive-month rule.
                    </p>
                  </section>
                  <RemoveButton
                    show={treatments.length > 1}
                    onClick={() =>
                      setTreatments(
                        treatments.filter((_, rowIndex) => rowIndex !== index),
                      )
                    }
                  />
                </div>
              ))}
            </RepeatableSection>
            <RepeatableSection title="Disease progression records" onAdd={() => setProgressionRecords([...progressionRecords, blankProgressionRecord()])}>
              {progressionRecords.map((record, index) => <div className="entry-grid repeatable-card" key={index}>
                <SelectField label="Progression status" value={record.status} options={getOptions("disease-progression-statuses")} onChange={(value) => updateRow(setProgressionRecords, index, "status", value)} required />
                <TextField label="Assessed on" type="date" value={record.assessed_on} onChange={(value) => updateRow(setProgressionRecords, index, "assessed_on", value)} required />
                <TextField label="Progression date" type="date" value={record.progression_date} onChange={(value) => updateRow(setProgressionRecords, index, "progression_date", value)} />
                <InlineCheckboxGroup label="Progression sites" options={getOptions("progression-sites")} value={record.progression_sites} onChange={(value) => updateRow(setProgressionRecords, index, "progression_sites", value)} />
                <SelectField label="Estimation method" value={record.estimation_method} options={getOptions("response-estimation-methods")} onChange={(value) => updateRow(setProgressionRecords, index, "estimation_method", value)} />
                <TextArea label="Progression notes" value={record.notes} onChange={(value) => updateRow(setProgressionRecords, index, "notes", value)} />
                <RemoveButton show={progressionRecords.length > 1} onClick={() => setProgressionRecords(progressionRecords.filter((_, itemIndex) => itemIndex !== index))} />
              </div>)}
            </RepeatableSection>
            <RepeatableSection title="Survival follow-ups" onAdd={() => setSurvivalFollowUps([...survivalFollowUps, blankSurvivalFollowUp()])}>
              {survivalFollowUps.map((record, index) => <div className="entry-grid repeatable-card" key={index}>
                <SelectField label="Survival status" value={record.status} options={getOptions("survival-statuses")} onChange={(value) => updateRow(setSurvivalFollowUps, index, "status", value)} required />
                <TextField label="Followed up on" type="date" value={record.followed_up_on} onChange={(value) => updateRow(setSurvivalFollowUps, index, "followed_up_on", value)} required />
                <TextField label="Death date" type="date" value={record.death_date} onChange={(value) => updateRow(setSurvivalFollowUps, index, "death_date", value)} />
                <TextField label="Cause of death" value={record.cause_of_death} onChange={(value) => updateRow(setSurvivalFollowUps, index, "cause_of_death", value)} />
                <TextArea label="Follow-up notes" value={record.notes} onChange={(value) => updateRow(setSurvivalFollowUps, index, "notes", value)} />
                <RemoveButton show={survivalFollowUps.length > 1} onClick={() => setSurvivalFollowUps(survivalFollowUps.filter((_, itemIndex) => itemIndex !== index))} />
              </div>)}
            </RepeatableSection>
            <RepeatableSection
              title="Surgery"
              onAdd={() => setSurgeries([...surgeries, blankSurgery()])}
            >
              {surgeries.map((row, index) => (
                <div className="entry-grid repeatable-card" key={index}>
                  <TextField
                    label="Surgery date"
                    type="date"
                    value={row.surgery_date}
                    onChange={(value) =>
                      updateRow(setSurgeries, index, "surgery_date", value)
                    }
                  />
                  <SelectField
                    label="Surgery modality"
                    value={row.surgery_modality}
                    options={getOptions("surgery-modalities")}
                    onChange={(value) =>
                      updateRow(setSurgeries, index, "surgery_modality", value)
                    }
                  />
                  <InlineCheckboxGroup
                    label="Surgical laterality"
                    options={getOptions("surgery-lateralities")}
                    value={row.lateralities}
                    fullWidth={false}
                    onChange={(lateralities) =>
                      updateRow(
                        setSurgeries,
                        index,
                        "lateralities",
                        lateralities,
                      )
                    }
                  />
                  <StatusField label="Surgery status" value={row.status} choices={surgeryStatuses} onChange={(value) => updateRow(setSurgeries, index, "status", value)} />
                  <TextArea label="Procedure details" value={row.procedure_details} onChange={(value) => updateRow(setSurgeries, index, "procedure_details", value)} />
                  <TextArea label="Operative findings" value={row.operative_findings} onChange={(value) => updateRow(setSurgeries, index, "operative_findings", value)} />
                  <TextArea label="Complications" value={row.complications} onChange={(value) => updateRow(setSurgeries, index, "complications", value)} />
                  <TextArea label="Surgery notes" value={row.notes} onChange={(value) => updateRow(setSurgeries, index, "notes", value)} />
                  <section className="entry-response-assessments entry-span-full">
                    <div className="entry-response-assessments-head">
                      <div>
                        <p className="eyebrow">Surgical outcome</p>
                        <h4>Pathological response</h4>
                      </div>
                    </div>
                    <ResponseAssessmentCard
                      title="Pathological response"
                      showTitle={false}
                      row={treatments[0]?.pathological_response ?? blankResponse()}
                      getOptions={getOptions}
                      resources={{
                        target: "pathological-response-target-lesions",
                        nonTarget: "pathological-response-non-target-lesions",
                        newLesion: "pathological-response-new-lesions",
                        result: "pathological-response-results",
                      }}
                      onChange={(pathological_response) =>
                        updateRow(
                          setTreatments,
                          0,
                          "pathological_response",
                          pathological_response,
                        )
                      }
                    />
                    <div className="entry-grid">
                      <SelectField label="Response category" value={treatments[0]?.pathological_response.response_category ?? ""} options={getOptions("pathological-response-categories")} onChange={(value) => updateRow(setTreatments, 0, "pathological_response", { ...(treatments[0]?.pathological_response ?? blankResponse()), response_category: value })} />
                      <TextField label="Residual viable tumour (%)" type="number" value={treatments[0]?.pathological_response.residual_viable_tumor_percentage ?? ""} onChange={(value) => updateRow(setTreatments, 0, "pathological_response", { ...(treatments[0]?.pathological_response ?? blankResponse()), residual_viable_tumor_percentage: value })} />
                      <SelectField label="Tumour regression grade" value={treatments[0]?.pathological_response.tumor_regression_grade ?? ""} options={getOptions("tumor-regression-grades")} onChange={(value) => updateRow(setTreatments, 0, "pathological_response", { ...(treatments[0]?.pathological_response ?? blankResponse()), tumor_regression_grade: value })} />
                    </div>
                  </section>
                  <RemoveButton
                    show={surgeries.length > 1}
                    onClick={() =>
                      setSurgeries(
                        surgeries.filter((_, rowIndex) => rowIndex !== index),
                      )
                    }
                  />
                </div>
              ))}
            </RepeatableSection>
            <RepeatableSection
              title="Radiotherapy"
              onAdd={() =>
                setRadiotherapySchedules([
                  ...radiotherapySchedules,
                  blankRadiotherapy(),
                ])
              }
            >
              {radiotherapySchedules.map((row, index) => (
                <div className="entry-grid repeatable-card" key={index}>
                  <InlineCheckboxGroup
                    label="Radiotherapy site"
                    options={getOptions("radiotherapy-sites")}
                    value={row.sites}
                    onChange={(sites) =>
                      updateRow(setRadiotherapySchedules, index, "sites", sites)
                    }
                  />
                  <TextField
                    label="Radiotherapy start"
                    type="date"
                    value={row.started_at}
                    onChange={(value) =>
                      updateRow(
                        setRadiotherapySchedules,
                        index,
                        "started_at",
                        value,
                      )
                    }
                  />
                  <TextField
                    label="Radiotherapy end"
                    type="date"
                    value={row.ended_at}
                    onChange={(value) =>
                      updateRow(
                        setRadiotherapySchedules,
                        index,
                        "ended_at",
                        value,
                      )
                    }
                  />
                  <SelectField
                    label="Radiotherapy intent"
                    value={row.radiotherapy_intent}
                    options={getOptions("radiotherapy-intents")}
                    onChange={(value) =>
                      updateRow(
                        setRadiotherapySchedules,
                        index,
                        "radiotherapy_intent",
                        value,
                      )
                    }
                  />
                  <InlineCheckboxGroup
                    label="Radiotherapy modality"
                    options={getOptions("radiotherapy-modalities")}
                    value={row.modalities}
                    onChange={(modalities) =>
                      updateRow(
                        setRadiotherapySchedules,
                        index,
                        "modalities",
                        modalities,
                      )
                    }
                  />
                  <TextField
                    label="Fraction dose"
                    value={row.fraction_dose}
                    onChange={(value) =>
                      updateRow(
                        setRadiotherapySchedules,
                        index,
                        "fraction_dose",
                        value,
                      )
                    }
                  />
                  <TextField
                    label="Fraction count"
                    value={row.fraction_count}
                    onChange={(value) =>
                      updateRow(
                        setRadiotherapySchedules,
                        index,
                        "fraction_count",
                        value,
                      )
                    }
                  />
                  <TextField
                    label="Total dose in cGY"
                    value={calculatedTotalDose(
                      row.fraction_dose,
                      row.fraction_count,
                    )}
                    onChange={() => undefined}
                    readOnly
                  />
                  <TextField label="Completed fractions" type="number" value={row.completed_fractions} onChange={(value) => updateRow(setRadiotherapySchedules, index, "completed_fractions", value)} />
                  <StatusField label="Radiotherapy status" value={row.status} choices={courseStatuses} onChange={(value) => updateRow(setRadiotherapySchedules, index, "status", value)} />
                  <TextArea label="Reason for stopping" value={row.reason_for_stopping} onChange={(value) => updateRow(setRadiotherapySchedules, index, "reason_for_stopping", value)} />
                  <TextArea label="Radiotherapy notes" value={row.notes} onChange={(value) => updateRow(setRadiotherapySchedules, index, "notes", value)} />
                  <RemoveButton
                    show={radiotherapySchedules.length > 1}
                    onClick={() =>
                      setRadiotherapySchedules(
                        radiotherapySchedules.filter(
                          (_, rowIndex) => rowIndex !== index,
                        ),
                      )
                    }
                  />
                </div>
              ))}
            </RepeatableSection>
          </>
        ) : null}
        {activeStep === 0 ? (
          <CheckboxGroup
            label="Comorbidities"
            options={getOptions("comorbidities")}
            value={comorbidities}
            onChange={setComorbidities}
          />
        ) : null}
        {activeStep === 2 ? (
          <>
            <section className="panel entry-block">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">TNM staging</p>
                  <h3>Clinical and pathological staging</h3>
                </div>
              </div>
              <div className="insight-grid insight-grid-dense">
                <section className="entry-grid entry-staging-section">
                  <h4 className="entry-span-full">Clinical TNM</h4>
                  <SelectField
                    label="T"
                    value={clinicalTnm[0].t}
                    options={getOptions("tnm-t")}
                    onChange={(value) =>
                      updateRow(setClinicalTnm, 0, "t", value)
                    }
                  />
                  <SelectField
                    label="N"
                    value={clinicalTnm[0].n}
                    options={getOptions("tnm-n")}
                    onChange={(value) =>
                      updateRow(setClinicalTnm, 0, "n", value)
                    }
                  />
                  <SelectField
                    label="M"
                    value={clinicalTnm[0].m}
                    options={getOptions("tnm-m")}
                    onChange={(value) =>
                      updateRow(setClinicalTnm, 0, "m", value)
                    }
                  />
                  <SelectField
                    label="Stage"
                    value={clinicalTnm[0].stage}
                    options={getOptions("tnm-stages")}
                    onChange={(value) =>
                      updateRow(setClinicalTnm, 0, "stage", value)
                    }
                  />
                  <TextField
                    label="Staging date"
                    type="date"
                    value={clinicalTnm[0].staged_at}
                    onChange={(value) =>
                      updateRow(setClinicalTnm, 0, "staged_at", value)
                    }
                  />
                </section>
                <section className="entry-grid entry-staging-section">
                  <h4 className="entry-span-full">Pathological TNM</h4>
                  <SelectField
                    label="T"
                    value={pathologicalTnm[0].t}
                    options={getOptions("tnm-t")}
                    onChange={(value) =>
                      updateRow(setPathologicalTnm, 0, "t", value)
                    }
                  />
                  <SelectField
                    label="N"
                    value={pathologicalTnm[0].n}
                    options={getOptions("tnm-n")}
                    onChange={(value) =>
                      updateRow(setPathologicalTnm, 0, "n", value)
                    }
                  />
                  <SelectField
                    label="M"
                    value={pathologicalTnm[0].m}
                    options={getOptions("tnm-m")}
                    onChange={(value) =>
                      updateRow(setPathologicalTnm, 0, "m", value)
                    }
                  />
                  <SelectField
                    label="Stage"
                    value={pathologicalTnm[0].stage}
                    options={getOptions("tnm-stages")}
                    onChange={(value) =>
                      updateRow(setPathologicalTnm, 0, "stage", value)
                    }
                  />
                  <TextField
                    label="Staging date"
                    type="date"
                    value={pathologicalTnm[0].staged_at}
                    onChange={(value) =>
                      updateRow(setPathologicalTnm, 0, "staged_at", value)
                    }
                  />
                </section>
              </div>
            </section>
          </>
        ) : null}
        <div className="entry-form-actions">
          <button
            type="button"
            className="secondary-button"
            disabled={draftMutation.isPending || saveMutation.isPending}
            onClick={saveDraft}
          >
            {draftMutation.isPending ? "Saving draft…" : "Save draft"}
          </button>
          <button
            type="button"
            className="secondary-button"
            disabled={visibleStepIndex === 0}
            onClick={(event) => {
              event.preventDefault();
              setActiveStep(stepTargets[visibleStepIndex - 1]);
            }}
          >
            <ChevronLeft size={16} />
            Previous
          </button>
          {visibleStepIndex < steps.length - 1 ? (
            <button
              type="button"
              className="primary-button"
              onClick={(event) => {
                event.preventDefault();
                setActiveStep(stepTargets[visibleStepIndex + 1]);
              }}
            >
              Next
              <ChevronRight size={16} />
            </button>
          ) : (
            <button
              type="submit"
              className="primary-button"
              disabled={saveMutation.isPending}
            >
              {saveMutation.isPending
                ? "Publishing clinical record…"
                : "Publish observation"}
            </button>
          )}
        </div>
      </form>
    </section>
  );
}

function CollapsibleSection({
  eyebrow = "Structured records",
  title,
  onAdd,
  children,
}: {
  eyebrow?: string;
  title: string;
  onAdd?: () => void;
  children: ReactNode;
}) {
  return (
    <details className="panel entry-block entry-collapsible">
      <summary>
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h3>{title}</h3>
        </div>
        <ChevronDown size={20} />
      </summary>
      <div className="entry-collapsible-content">
        {onAdd ? (
          <div className="entry-collapsible-action">
            <button type="button" className="secondary-button" onClick={onAdd}>
              <Plus size={16} />
              Add record
            </button>
          </div>
        ) : null}
        {children}
      </div>
    </details>
  );
}

function RepeatableSection({
  title,
  onAdd,
  children,
}: {
  title: string;
  onAdd: () => void;
  children: ReactNode;
}) {
  return (
    <section className="panel entry-block">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Structured records</p>
          <h3>{title}</h3>
        </div>
        <button type="button" className="secondary-button" onClick={onAdd}>
          <Plus size={16} />
          Add record
        </button>
      </div>
      <div className="entry-repeatable-list">{children}</div>
    </section>
  );
}

function RemoveButton({
  show,
  onClick,
}: {
  show: boolean;
  onClick: () => void;
}) {
  return show ? (
    <button
      type="button"
      className="secondary-button entry-remove-button"
      onClick={onClick}
    >
      <Trash2 size={16} />
      Remove
    </button>
  ) : null;
}
