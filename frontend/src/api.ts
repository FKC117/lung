import { reportFrontendError } from './error-reporting';

export interface DashboardSummary {
  patients: number;
  observations: number;
  published_patients: number;
  draft_patients: number;
  published_observations: number;
  draft_observations: number;
}

export interface SiteSettings {
  site_title: string;
  header_eyebrow: string;
  site_description: string;
  logo_url: string;
  logo_alt_text: string;
  favicon_url: string;
}

export function fetchSiteSettings() {
  return request<SiteSettings>("/api/site-settings/");
}

export interface AnalyticsFilterOptions {
  centers: Array<{ center_id: number; center__name: string }>;
  doctors: Array<{ doctor_id: number; doctor__name: string }>;
  diagnoses: string[];
  stages: string[];
  biomarkers: string[];
  treatments: string[];
  regimens: string[];
  outcomes: string[];
}

export interface AnalyticsSummary {
  kpis: Record<string, number | null>;
  definitions: Record<string, string>;
}

export interface AnalyticsDistributions {
  stage: Array<{ label: string; count: number }>;
  histopathology: Array<{ label: string; count: number }>;
  grade: Array<{ label: string; count: number }>;
  pathological_stage: Array<{ label: string; count: number }>;
  pathological_margin: Array<{ label: string; count: number }>;
  pathological_lvsi: Array<{ label: string; count: number }>;
  pathological_pni: Array<{ label: string; count: number }>;
  primary_site: Array<{ label: string; count: number }>;
  diagnosis_subgroup: Array<{ label: string; count: number }>;
  diagnosis_laterality: Array<{ label: string; count: number }>;
  metastatic_site: Array<{ label: string; count: number }>;
  biomarker: Array<{ label: string; count: number }>;
  molecular_status: Array<{ label: string; count: number }>;
  molecular_exon: Array<{ label: string; count: number }>;
  molecular_method: Array<{ label: string; count: number }>;
  molecular_specimen: Array<{ label: string; count: number }>;
  ihc_marker: Array<{ label: string; count: number }>;
  cancer_marker: Array<{ label: string; count: number }>;
  treatment: Array<{ label: string; count: number }>;
  treatment_line: Array<{ label: string; count: number }>;
  treatment_modality: Array<{ label: string; count: number }>;
  response: Array<{ label: string; count: number }>;
  progression_status: Array<{ label: string; count: number }>;
  survival_status: Array<{ label: string; count: number }>;
  progression_site: Array<{ label: string; count: number }>;
  radiotherapy_intent: Array<{ label: string; count: number }>;
  radiotherapy_site: Array<{ label: string; count: number }>;
  radiotherapy_modality: Array<{ label: string; count: number }>;
  surgery_modality: Array<{ label: string; count: number }>;
  surgery_laterality: Array<{ label: string; count: number }>;
  smoking_status: Array<{ label: string; count: number }>;
  alcohol_history: Array<{ label: string; count: number }>;
  comorbidity: Array<{ label: string; count: number }>;
  gender: Array<{ label: string; count: number }>;
  district: Array<{ label: string; count: number }>;
  socio_economic_status: Array<{ label: string; count: number }>;
  patient_type: Array<{ label: string; count: number }>;
  tb_status: Array<{ label: string; count: number }>;
  covid_status: Array<{ label: string; count: number }>;
  completeness: Array<{ label: string; count: number; total: number }>;
}

export interface AnalyticsFacet {
  subject: string;
  measure: string;
  unit: string;
  count_mode: string;
  items: Array<{ label: string; count: number }>;
  filters: Record<string, string[]>;
}

export interface AnalyticsMolecularSummary {
  patients_tested: number;
  test_events: number;
  result_entries: number;
  methods_recorded: number;
  definition: string;
}

export interface AnalyticsMolecularChronology {
  count_mode: string;
  unit: string;
  items: Array<{ label: string; count: number }>;
}

export interface AnalyticsMolecularResultBreakdown {
  count_mode: string;
  unit: string;
  statuses: string[];
  rows: Array<{ method: string; gene: string; status: string; count: number }>;
}

export interface AnalyticsSurvival {
  survival: Array<{
    metric: string;
    available: number;
    median_days: number | null;
    values: number[];
  }>;
  definitions: Record<string, string>;
}

export interface AnalyticsPatientMatches {
  subject: string;
  scope: string;
  count: number;
  items: Array<{
    registry_id: string | null;
    name: string;
    registration_no: string;
    phone: string;
    email: string;
    age: number | null;
    gender: string;
    district: string;
    matching_records: number;
    latest_observation: string | null;
    molecular_methods: string;
    diagnosis: string;
    primary_site: string;
    diagnosis_subgroup: string;
    diagnosis_laterality: string;
    stage: string;
    pathological_stage: string;
    pathology: string;
    grade: string;
    metastatic_site: string;
    biomarker: string;
    molecular_status: string;
    molecular_exon: string;
    molecular_method: string;
    molecular_specimen: string;
    cancer_marker: string;
    treatment: string;
    treatment_line: string;
    treatment_modality: string;
    response: string;
    progression_status: string;
    survival_status: string;
    radiotherapy_intent: string;
    radiotherapy_site: string;
    radiotherapy_modality: string;
    surgery_modality: string;
    surgery_laterality: string;
    smoking_status: string;
    comorbidity: string;
    diagnosis_date: string | null;
    treatment_start: string | null;
    progression_date: string | null;
    death_date: string | null;
    last_follow_up: string | null;
  }>;
}

export interface LongitudinalAnalyticsOverview {
  name: string;
  metrics: Record<string, number>;
  chronology: Array<{ month: string; event_type: string; count: number }>;
  distributions: Record<string, Array<{ label: string; count: number }>>;
  breakdowns: Record<string, Array<{ label: string; count: number }>>;
  molecular_combinations: Array<{
    method: string;
    specimen: string;
    gene: string;
    exon: string;
    result: string;
    count: number;
  }>;
  molecular_patient_rows: Array<{
    registry_id: string;
    patient_source_id: number;
    age: number | null;
    sex: string;
    observation_source_id: number | null;
    molecular_test_source_id: number;
    molecular_result_source_id: number;
    tested_at: string | null;
    method: string;
    specimen: string;
    gene: string;
    exon: string;
    result: string;
  }>;
  molecular_quality: {
    test_total: number;
    result_total: number;
    missing_test_date: number;
    missing_method: number;
    missing_specimen: number;
    missing_gene: number;
    missing_exon: number;
    missing_result: number;
  };
  molecular_repeats: Array<{
    registry_id: string;
    patient_source_id: number;
    age: number | null;
    sex: string;
    gene: string;
    test_events: number;
    result_categories: number;
    first_tested_at: string | null;
    last_tested_at: string | null;
    discordant: boolean;
  }>;
  data_quality: Record<
    string,
    { missing_event_dates: number; total_rows: number }
  >;
  freshness: { status: 'current' | 'stale'; reason: string; differences: Array<{ dataset: string; entries_rows: number; analytics_rows: number }> };
  definitions: Record<string, string>;
}
export interface AnalyticsReviewTask {
  task_key: string;
  patient_source_id: number;
  registry_id: string;
  observation_id: number | null;
  review_section: string | null;
  review_type: string;
  title: string;
  reason: string;
  status: string;
  notes: string;
  correction_targets: Array<{ label: string; url: string }>;
  history: Array<{
    action: string;
    from_status: string;
    to_status: string;
    notes: string;
    changed_by: string;
    changed_at: string;
  }>;
}

export interface PatientDemographicsLookup {
  genders: string[];
  blood_groups: string[];
  districts: string[];
  police_stations: string[];
  socio_economic_statuses: string[];
  patient_types: string[];
  marital_statuses: string[];
  alcohol_history_options: string[];
  smoking_statuses: string[];
  tb_statuses: string[];
  covid_statuses: string[];
  covid_vaccine_names: string[];
  covid_vaccination_doses: string[];
  diagnosis_disease_groups: string[];
  diagnosis_disease_subgroups: string[];
  diagnosis_primary_sites: string[];
  diagnosis_lateralities: string[];
  diagnosis_metastatic_sites: string[];
  histopathology_details: string[];
  histopathology_types: string[];
  ihc_marker_types: string[];
  molecular_pathology_options: Record<string, string[]>;
}

export interface AuthUser {
  id: number;
  username: string;
  full_name: string;
  email: string;
  role: "admin" | "doctor" | "user";
  default_redirect: string;
  is_staff: boolean;
  is_superuser: boolean;
}

export interface PatientListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Patient[];
}

export interface LegacyUnlinkedHistory {
  legacy_history_id: number;
  missing_observation_id: number;
  marital_status: string;
  first_diagnosis_date: string | null;
  created_at: string | null;
  updated_at: string | null;
  resolution_status: "open" | "reviewed" | "resolved";
}

export interface LegacyUnlinkedHistoryResponse {
  count: number;
  page: number;
  per_page: number;
  next: number | null;
  previous: number | null;
  results: LegacyUnlinkedHistory[];
}

export interface Patient {
  id: number;
  legacy_id: number | null;
  registry_id: string;
  legacy_unique_id: string | null;
  registration_no: string | null;
  name: string;
  phone: string | null;
  age: number | null;
  gender: string | null;
  district: string | null;
  socio_economic_status: string | null;
  observation_count: number;
  latest_observation: ClinicalObservationSummary | null;
  can_edit: boolean;
}

export interface PatientDetail {
  id: number;
  legacy_id: number | null;
  registry_id: string;
  legacy_unique_id: string | null;
  registration_no: string | null;
  name: string;
  phone: string | null;
  email: string | null;
  nid: string | null;
  date_of_birth: string | null;
  age: number | null;
  gender: string | null;
  blood_group: string | null;
  area: string | null;
  police_station: string | null;
  district: string | null;
  socio_economic_status: string | null;
  passport: string | null;
  patient_type: string | null;
  is_draft: boolean;
  can_edit: boolean;
  observations: ClinicalObservation[];
}

export interface ClinicalObservationSummary {
  id: number;
  legacy_id: number | null;
  registration_no: string | null;
  observed_at: string | null;
  consulting_doctor_name: string | null;
  center_name: string | null;
  cancer_type: string | null;
  diagnosis_disease_group: string | null;
  diagnosis_subgroup: string | null;
  diagnosis_primary_site: string | null;
  diagnosis_laterality: string | null;
  grade: string | null;
  is_draft: boolean;
  can_edit: boolean;
}

export interface ClinicalObservation extends ClinicalObservationSummary {
  history: PatientHistory | null;
  diagnoses: Diagnosis[];
  metastatic_sites: ValueItem[];
  comorbidities: DetailItem[];
  histopathologies: Histopathology[];
  molecular_pathologies: MolecularPathology[];
  cancer_markers: CancerMarker[];
  clinical_stagings: Staging[];
  pathological_stagings: Staging[];
  pathological_staging_details: PathologicalStagingDetail[];
  ihc_panels: IHCPanel[];
  treatment_cycles: TreatmentCycle[];
  past_treatment_histories: PastTreatmentHistory[];
  radiotherapy_schedules: RadiotherapySchedule[];
  surgeries: Surgery[];
}

export interface PatientHistory {
  id: number;
  marital_status: string | null;
  dietary_habit: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  bmi: number | null;
  alcohol_history: string | null;
  radiotherapy_to_chest: string | null;
  family_cancer_history: string | null;
  known_mutation: string | null;
  first_diagnosis_date: string | null;
  smoking_histories: SmokingHistory[];
  tb_histories: TuberculosisHistory[];
  covid_histories: CovidHistory[];
}

export interface SmokingHistory {
  id: number;
  status: string | null;
  cigarettes_per_day: number | null;
  duration_years: number | null;
  pack_years: number | null;
  quit_period_years: number | null;
}

export interface TuberculosisHistory {
  id: number;
  status: string | null;
  date: string | null;
  treatment: string | null;
}

export interface CovidHistory {
  id: number;
  status: string | null;
  date: string | null;
  vaccine_name: string | null;
  vaccination_dose: string | null;
}

export interface Diagnosis {
  id: number;
  detail: string | null;
}

export interface ValueItem {
  id: number;
  value: string | null;
}

export interface DetailItem {
  id: number;
  detail: string | null;
}

export interface Histopathology {
  id: number;
  detail: string | null;
  site: string | null;
  histology_type: string | null;
  observed_on: string | null;
}

export interface MolecularPathology {
  id: number;
  specimen: string | null;
  method: string | null;
  gene: string | null;
  exon: string | null;
  status: string | null;
  observed_on: string | null;
}

export interface CancerMarker {
  id: number;
  name: string | null;
  value: string | null;
  unit: string | null;
  observed_on: string | null;
}

export interface Staging {
  id: number;
  t: string | null;
  n: string | null;
  m: string | null;
  result: string | null;
  staged_on: string | null;
}

export interface PathologicalStagingDetail {
  id: number;
  lvsi: string | null;
  pni: string | null;
  margin: string | null;
  ki67: string | null;
  staged_on: string | null;
}

export interface IHCDetail {
  id: number;
  marker_type: string | null;
  value: string | null;
}

export interface IHCPanel {
  id: number;
  observed_on: string | null;
  details: IHCDetail[];
}

export interface TreatmentCycle {
  id: number;
  current_chemo_protocol: string | null;
  chemo_cycle_no: string | null;
  chemo_detail: string | null;
  chemo_starting_date: string | null;
  chemo_end_date: string | null;
  line_of_treatment: string | null;
  disease_progression_status: string | null;
  disease_progression_status_date: string | null;
  survival_status: string | null;
  survival_status_date: string | null;
  recist_1_target_lesion: string | null;
  recist_1_non_target_lesion: string | null;
  recist_1_new_lesion: string | null;
  recist_1_result: string | null;
  recist_1_date: string | null;
  recist_1_method_of_estimation: string | null;
  irecist_target_lesion: string | null;
  irecist_non_target_lesion: string | null;
  irecist_new_lesion: string | null;
  irecist_result: string | null;
  irecist_date: string | null;
  irecist_method_of_estimation: string | null;
  pathological_response_rate_target_lesion: string | null;
  pathological_response_rate_non_target_lesion: string | null;
  pathological_response_rate_new_lesion: string | null;
  pathological_response_rate_result: string | null;
  pathological_response_rate_date: string | null;
  pathological_method_of_estimation: string | null;
  progression_free_survival: string | null;
  overall_survival: string | null;
  chemotherapy_protocols: ChemotherapyProtocol[];
  chemotherapy_modalities: ChemotherapyModality[];
}

export interface ChemotherapyProtocol {
  id: number;
  cycle_no: string | number | null;
  protocol_type: string | null;
}

export interface ChemotherapyModality {
  id: number;
  detail: string | null;
}

export interface PastTreatmentHistory {
  id: number;
  detail: string | null;
  date: string | null;
}

export interface RadiotherapySchedule {
  id: number;
  start_date: string | null;
  end_date: string | null;
  intent: string | null;
  fraction: string | null;
  fraction_number: string | null;
  total_dose: string | null;
  sites: ValueItem[];
  modalities: ValueItem[];
}

export interface Surgery {
  id: number;
  surgery_date: string | null;
  modality: string | null;
  lateralities: ValueItem[];
}

export interface PatientEntryPayload {
  observation_id?: number;
  registry_id?: string;
  legacy_unique_id?: string;
  registration_no?: string;
  name: string;
  phone?: string;
  email?: string;
  nid?: string;
  date_of_birth?: string | null;
  age?: number | null;
  gender?: string;
  blood_group?: string;
  area?: string;
  police_station?: string;
  district?: string;
  socio_economic_status?: string;
  passport?: string;
  patient_type?: string;
  patient_is_draft?: boolean;
  observed_at?: string | null;
  consulting_doctor_name?: string;
  center_name?: string;
  cancer_type?: string;
  diagnosis_disease_group?: string;
  diagnosis_subgroup?: string;
  diagnosis_primary_site?: string;
  diagnosis_laterality?: string;
  grade?: string;
  laterality_notes?: string;
  observation_is_draft?: boolean;
  history?: {
    marital_status?: string;
    dietary_habit?: string;
    height_cm?: string | number | null;
    weight_kg?: string | number | null;
    bmi?: string | number | null;
    alcohol_history?: string;
    radiotherapy_to_chest?: string;
    family_cancer_history?: string;
    known_mutation?: string;
    first_diagnosis_date?: string | null;
  };
  smoking_histories?: Array<{
    status?: string;
    cigarettes_per_day?: number | null;
    duration_years?: string | number | null;
    pack_years?: string | number | null;
    quit_period_years?: string | number | null;
  }>;
  tb_histories?: Array<{
    status?: string;
    date?: string | null;
    treatment?: string;
  }>;
  covid_histories?: Array<{
    status?: string;
    date?: string | null;
    vaccine_name?: string;
    vaccination_dose?: string;
  }>;
  diagnoses?: string[];
  metastatic_sites?: string[];
  comorbidities?: string[];
  histopathologies?: Array<{
    detail?: string;
    site?: string;
    histology_type?: string;
    observed_on?: string | null;
  }>;
  molecular_pathologies?: Array<{
    specimen?: string;
    method?: string;
    gene?: string;
    exon?: string;
    status?: string;
    observed_on?: string | null;
  }>;
  cancer_markers?: Array<{
    name: string;
    value: string;
    unit?: string;
    observed_on: string;
  }>;
  clinical_staging?: {
    t?: string;
    n?: string;
    m?: string;
    result?: string;
    staged_on?: string | null;
  };
  pathological_staging?: {
    t?: string;
    n?: string;
    m?: string;
    result?: string;
    staged_on?: string | null;
  };
  pathological_staging_detail?: {
    lvsi?: string;
    pni?: string;
    margin?: string;
    ki67?: string;
    staged_on?: string | null;
  };
  ihc_panels?: Array<{
    observed_on?: string | null;
    details?: Array<{
      marker_type?: string;
      value?: string;
    }>;
  }>;
  treatment_cycles?: Array<{
    current_chemo_protocol?: string;
    chemo_cycle_no?: string;
    chemo_detail?: string;
    chemo_starting_date?: string | null;
    chemo_end_date?: string | null;
    line_of_treatment?: string;
    disease_progression_status?: string;
    disease_progression_status_date?: string | null;
    survival_status?: string;
    survival_status_date?: string | null;
  }>;
  past_treatment_histories?: Array<{
    detail?: string;
    date?: string | null;
  }>;
  radiotherapy_schedules?: Array<{
    start_date?: string | null;
    end_date?: string | null;
    intent?: string;
    fraction?: string;
    fraction_number?: string;
    total_dose?: string;
    sites?: string[];
    modalities?: string[];
  }>;
  surgeries?: Array<{
    surgery_date: string;
    modality?: string;
    lateralities?: string[];
  }>;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

function getCookie(name: string) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop()?.split(";").shift() ?? "";
  }
  return "";
}

function validationMessage(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value))
    return value.map(validationMessage).filter(Boolean).join(" ");
  if (value && typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .map(([field, message]) => `${field}: ${validationMessage(message)}`)
      .filter(Boolean)
      .join(" | ");
  }
  return "";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers ?? {});
  const method = (init?.method ?? "GET").toUpperCase();
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (method !== "GET" && method !== "HEAD" && !headers.has("X-CSRFToken")) {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) {
      headers.set("X-CSRFToken", csrfToken);
    }
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      credentials: "include",
      headers,
    });
  } catch (error) {
    reportFrontendError(error, { kind: "network-request", method, path });
    throw error;
  }

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      const payload = (await response.json()) as { detail?: string } & Record<
        string,
        unknown
      >;
      message = payload.detail || validationMessage(payload) || message;
    }
    const error = new ApiError(message, response.status);
    reportFrontendError(error, { kind: "api-request", method, path, status: response.status });
    throw error;
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function fetchCsrfToken() {
  // LEGACY_UI: the current backend uses Django's admin login, not an SPA CSRF endpoint.
  return Promise.resolve({ detail: "Django admin session authentication is in use." });
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  // A protected current endpoint is the reliable session probe exposed by this backend.
  await request<{ count: number }>("/api/records/patients/?page_size=1");
  return {
    id: 0,
    username: "registry-user",
    full_name: "Registry user",
    email: "",
    role: "user" as const,
    default_redirect: "/patients",
    is_staff: false,
    is_superuser: false,
  };
}

export async function loginUser(
  username: string,
  password: string,
  role: "admin" | "doctor" | "user",
) {
  // LEGACY_UI: username/password/role were sent to a retired SPA auth API.
  // Keep authentication with the backend that actually exists.
  void username;
  void password;
  void role;
  const next = `${window.location.pathname}${window.location.search}`;
  window.location.assign(`/admin/login/?next=${encodeURIComponent(next === "/login" ? "/patients" : next)}`);
  return new Promise<AuthUser>(() => undefined);
}

export async function logoutUser() {
  window.location.assign("/admin/logout/?next=/login");
  return new Promise<void>(() => undefined);
}

/**
 * LEGACY_API: the following analytics/workspace helpers point at endpoints
 * removed from the current backend. Their calling pages are listed in
 * `legacy-ui.ts`; do not use these helpers in new frontend work.
 */
export function fetchDashboardSummary() {
  return request<DashboardSummary>("/api/entries/workspace/dashboard/");
}

function analyticsQuery(filters: Record<string, string>) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  return params.toString();
}

export function fetchAnalyticsFilters(filters: Record<string, string> = {}) {
  const query = analyticsQuery(filters);
  return request<AnalyticsFilterOptions>(
    `/api/entries/analytics/filters/${query ? `?${query}` : ""}`,
  );
}

export function fetchAnalyticsSummary(filters: Record<string, string>) {
  return request<AnalyticsSummary>(
    `/api/entries/analytics/summary/?${analyticsQuery(filters)}`,
  );
}

export function fetchAnalyticsDistributions(filters: Record<string, string>) {
  return request<AnalyticsDistributions>(
    `/api/entries/analytics/distributions/?${analyticsQuery(filters)}`,
  );
}

export function fetchAnalyticsFacet(
  subject: string,
  filters: Record<string, string>,
  countMode = "records",
) {
  const params = new URLSearchParams(analyticsQuery(filters));
  params.set("subject", subject);
  params.set("count_mode", countMode);
  return request<AnalyticsFacet>(
    `/api/entries/analytics/facet/?${params.toString()}`,
  );
}

export function fetchAnalyticsMolecularSummary(
  filters: Record<string, string>,
) {
  return request<AnalyticsMolecularSummary>(
    `/api/entries/analytics/molecular-summary/?${analyticsQuery(filters)}`,
  );
}

export function fetchAnalyticsMolecularChronology(
  filters: Record<string, string>,
  countMode = "events",
) {
  const params = new URLSearchParams(analyticsQuery(filters));
  params.set("count_mode", countMode);
  return request<AnalyticsMolecularChronology>(
    `/api/entries/analytics/molecular-chronology/?${params.toString()}`,
  );
}

export function fetchAnalyticsMolecularResultBreakdown(
  filters: Record<string, string>,
  countMode = "entries",
) {
  const params = new URLSearchParams(analyticsQuery(filters));
  params.set("count_mode", countMode);
  return request<AnalyticsMolecularResultBreakdown>(
    `/api/entries/analytics/molecular-result-breakdown/?${params.toString()}`,
  );
}

export function fetchAnalyticsSurvival(filters: Record<string, string>) {
  return request<AnalyticsSurvival>(
    `/api/entries/analytics/survival/?${analyticsQuery(filters)}`,
  );
}

export function fetchAnalyticsPatientMatches(
  subject: string,
  filters: Record<string, string>,
) {
  const params = new URLSearchParams(analyticsQuery(filters));
  if (subject) params.set("subject", subject);
  return request<AnalyticsPatientMatches>(
    `/api/entries/analytics/patients/?${params.toString()}`,
  );
}

export function buildAnalyticsExportUrl(filters: Record<string, string>) {
  return `${API_BASE_URL}/api/entries/analytics/export/?${analyticsQuery(filters)}`;
}

export function fetchLongitudinalAnalytics(
  filters: { start_date?: string; end_date?: string } = {},
) {
  const params = new URLSearchParams();
  if (filters.start_date) params.set("start_date", filters.start_date);
  if (filters.end_date) params.set("end_date", filters.end_date);
  return request<LongitudinalAnalyticsOverview>(
    `/api/longitudinal-analytics/overview/${params.size ? `?${params}` : ""}`,
  );
}

export function buildMolecularPatientTraceExportUrl(
  filters: Record<string, string>,
) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  return `${API_BASE_URL}/api/longitudinal-analytics/molecular-patients/export/${params.size ? `?${params}` : ""}`;
}
export function fetchAnalyticsReviewQueue() {
  return request<{ items: AnalyticsReviewTask[] }>(
    "/api/longitudinal-analytics/review-queue/",
  );
}
export function updateAnalyticsReviewTask(
  task_key: string,
  status: string,
  notes: string,
) {
  return request<Pick<AnalyticsReviewTask, "task_key" | "status" | "notes">>(
    "/api/longitudinal-analytics/review-queue/",
    { method: "POST", body: JSON.stringify({ task_key, status, notes }) },
  );
}

/** LEGACY_API: retired patient-workspace endpoints used only by PatientEntryPage. */
export function fetchPatientDemographics(district = "", diseaseGroup = "") {
  const params = new URLSearchParams();
  if (district) {
    params.set("district", district);
  }
  if (diseaseGroup) {
    params.set("disease_group", diseaseGroup);
  }
  const query = params.toString();
  return request<PatientDemographicsLookup>(
    `/api/patients/demographics/${query ? `?${query}` : ""}`,
  );
}

export function fetchPatients(
  query: string,
  page = 1,
  perPage = 24,
  state = "all",
  sort = "name",
  direction = "asc",
) {
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("per_page", String(perPage));
  if (query) {
    params.set("q", query);
  }
  if (state !== "all") {
    params.set("state", state);
  }
  params.set("sort", sort);
  params.set("dir", direction);

  return request<{ count: number; next: string | null; previous: string | null; results: RawRecord[] }>(
    `/api/records/patients/?page=${page}&page_size=${perPage}`,
  ).then((response) => ({
    ...response,
    results: response.results
      .filter((item) => {
        const needle = query.trim().toLowerCase();
        return !needle || [item.name, item.phone, item.registration_no, item.patient_id]
          .some((value) => String(value ?? "").toLowerCase().includes(needle));
      })
      .map((item): Patient => ({
        id: Number(item.id), legacy_id: null, registry_id: String(item.patient_id ?? item.id),
        legacy_unique_id: null, registration_no: String(item.registration_no ?? ""), name: String(item.name ?? ""),
        phone: item.phone ? String(item.phone) : null, age: typeof item.age === "number" ? item.age : null,
        gender: null, district: null, socio_economic_status: null, observation_count: 0,
        latest_observation: null, can_edit: true,
      })),
  }));
}

export function fetchRegistryPatients(
  query: string,
  page = 1,
  perPage = 24,
  state = "all",
  sort = "name",
  direction = "asc",
) {
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("per_page", String(perPage));
  if (query) {
    params.set("q", query);
  }
  if (state !== "all") {
    params.set("state", state);
  }
  params.set("sort", sort);
  params.set("dir", direction);

  return request<PatientListResponse>(`/api/patients/?${params.toString()}`);
}

export function fetchRegistryPatientDetail(registryId: string) {
  return request<PatientDetail>(`/api/patients/${registryId}/`);
}

export async function fetchPatientDetail(registryId: string) {
  const source = await fetchEntriesPatientClinicalDetail(Number(registryId));
  return adaptEntriesPatientDetail(source);
}

export function fetchLegacyUnlinkedHistories(
  query = "",
  page = 1,
  status = "open",
) {
  const params = new URLSearchParams({
    page: String(page),
    per_page: "25",
    status,
  });
  if (query) {
    params.set("q", query);
  }
  return request<LegacyUnlinkedHistoryResponse>(
    `/api/legacy-review/unlinked-histories/?${params.toString()}`,
  );
}

export function createPatientEntry(payload: PatientEntryPayload) {
  return request<{ id: number; registry_id: string; name: string }>(
    "/api/patients/create/",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function updatePatientEntry(
  registryId: string,
  payload: PatientEntryPayload,
) {
  return request<{ id: number; registry_id: string; name: string }>(
    `/api/patients/${registryId}/update/`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );
}

export interface EntryOption {
  id: number;
  name?: string;
  display: string;
  [key: string]: unknown;
}

export interface EntriesPatientMatch {
  id: number;
  patient_id: string;
  name: string;
  phone: string;
  registration_no: string;
}

export interface EntriesIntakePayload {
  existing_patient_id?: number;
  draft_observation_id?: number;
  draft_form_state?: Record<string, unknown>;
  patient: Record<string, unknown>;
  observation: Record<string, unknown>;
  history?: Record<string, unknown>;
  smoking_history_records?: Array<Record<string, unknown>>;
  tb_history_records?: Array<Record<string, unknown>>;
  covid_history_records?: Array<Record<string, unknown>>;
  comorbidities?: Array<Record<string, unknown>>;
  diagnoses?: Array<Record<string, unknown>>;
  histopathologies?: Array<Record<string, unknown>>;
  clinical_tnm_stagings?: Array<Record<string, unknown>>;
  pathological_tnm_stagings?: Array<Record<string, unknown>>;
  pathological_staging_details?: Array<Record<string, unknown>>;
  molecular_pathologies?: Array<Record<string, unknown>>;
  molecular_tests?: Array<Record<string, unknown>>;
  cancer_markers?: Array<Record<string, unknown>>;
  ihc_panels?: Array<Record<string, unknown>>;
  past_treatment_histories?: Array<Record<string, unknown>>;
  treatment_cycles?: Array<Record<string, unknown>>;
  surgeries?: Array<Record<string, unknown>>;
  radiotherapy_schedules?: Array<Record<string, unknown>>;
  progression_records?: Array<Record<string, unknown>>;
  survival_followups?: Array<Record<string, unknown>>;
}

export function fetchEntriesOptions(resources: string[]) {
  const params = new URLSearchParams({ include: resources.join(",") });
  return request<Record<string, EntryOption[]>>(
    `/api/catalog/?${params.toString()}`,
  );
}

export function fetchEntriesPatients(search: string, page = 1, pageSize = 8) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  return request<{
    count: number;
    next: string | null;
    previous: string | null;
    results: EntriesPatientMatch[];
  }>(`/api/records/patients/?${params.toString()}`).then((response) => ({
    ...response,
    results: response.results.filter((patient) => {
      const needle = search.trim().toLowerCase();
      return !needle || [patient.name, patient.phone, patient.registration_no, patient.patient_id]
        .some((value) => String(value ?? "").toLowerCase().includes(needle));
    }).map((patient) => ({
      ...patient,
      id: Number(patient.id), patient_id: String(patient.patient_id ?? ""), name: String(patient.name ?? ""),
      phone: String(patient.phone ?? ""), registration_no: String(patient.registration_no ?? ""),
    })),
  }));
}

export function fetchEntriesPatient(id: number) {
  return request<EntriesPatientMatch & Record<string, unknown>>(
    `/api/records/patients/${id}/`,
  );
}

export async function lookupEntriesPatient(registrationNo: string, phone: string) {
  const response = await request<{ results: Array<EntriesPatientMatch & Record<string, unknown>> }>(
    "/api/records/patients/?page_size=100",
  );
  const match = response.results.find((patient) =>
    (registrationNo && String(patient.registration_no) === registrationNo) ||
    (phone && String(patient.phone) === phone),
  ) ?? null;
  return { match, count: match ? 1 : 0 };
}

export function fetchEntriesObservations(patientId: number) {
  return request<{ results: Array<Record<string, unknown>> }>(
    `/api/entries/observations/?patient=${patientId}&page_size=100`,
  );
}

export interface EntriesClinicalRecord extends Record<string, unknown> {
  id: number;
  labels?: Record<string, string | string[]>;
}

export interface EntriesPatientClinicalDetail {
  patient: EntriesClinicalRecord;
  observations: Array<Record<string, unknown>>;
  molecular_tests: Array<EntriesClinicalRecord>;
}

export async function fetchEntriesPatientClinicalDetail(id: number): Promise<EntriesPatientClinicalDetail> {
  const [patient, observationResponse] = await Promise.all([
    request<EntriesClinicalRecord>(`/api/records/patients/${id}/`),
    request<{ results: EntriesClinicalRecord[] }>("/api/records/observations/?page_size=100"),
  ]);
  return {
    patient,
    observations: observationResponse.results
      .filter((observation) => Number(observation.patient) === id)
      .map((observation) => ({ observation })),
    molecular_tests: [],
  } as EntriesPatientClinicalDetail;
}

type RawEntriesRecord = EntriesClinicalRecord & Record<string, unknown>;

function entryRows(
  entry: Record<string, unknown>,
  key: string,
): RawEntriesRecord[] {
  return Array.isArray(entry[key]) ? (entry[key] as RawEntriesRecord[]) : [];
}

function entryLabel(
  record: RawEntriesRecord | undefined,
  key: string,
): string | null {
  if (!record) return null;
  const value = record.labels?.[key];
  if (typeof value === "string") return value;
  const raw = record[key];
  return raw === null || raw === undefined || raw === "" ? null : String(raw);
}

function entryLabels(
  record: RawEntriesRecord | undefined,
  key: string,
): ValueItem[] {
  if (!record) return [];
  const value = record.labels?.[key];
  const raw = Array.isArray(record[key]) ? record[key] : [];
  return Array.isArray(value)
    ? value.map((label, index) => ({
        id: Number(raw[index]) || index + 1,
        value: label,
      }))
    : [];
}

function entryDate(value: unknown) {
  return value === null || value === undefined || value === ""
    ? null
    : String(value);
}

/** Converts normalized Entries records to the established PatientDetail UI contract. */
export function adaptEntriesPatientDetail(
  source: EntriesPatientClinicalDetail,
): PatientDetail {
  const patient = source.patient as RawEntriesRecord;
  const observations = source.observations.map((entry) => {
    const observation = entry.observation as RawEntriesRecord;
    const histories = entryRows(entry, "histories");
    const history = histories[0];
    const diagnoses = entryRows(entry, "diagnoses");
    const diagnosis = diagnoses[0];
    const histopathologies = entryRows(entry, "histopathologies");
    const clinicalStage = entryRows(entry, "clinical_tnm_stagings");
    const pathologicalStage = entryRows(entry, "pathological_tnm_stagings");
    const pathologicalDetails = entryRows(
      entry,
      "pathological_staging_details",
    );
    const ihcPanels = entryRows(entry, "ihc_panels");
    const ihcResults = entryRows(entry, "ihc_results");
    const cycles = entryRows(entry, "treatment_cycles");

    return {
      id: observation.id,
      legacy_id:
        typeof observation.legacy_id === "number"
          ? observation.legacy_id
          : null,
      registration_no: entryLabel(observation, "registration_no"),
      observed_at: entryDate(observation.observed_at),
      consulting_doctor_name:
        entryLabel(observation, "doctor") ||
        entryLabel(observation, "consulting_doctor_name"),
      center_name:
        entryLabel(observation, "center") ||
        entryLabel(observation, "center_name"),
      cancer_type: entryLabel(observation, "cancer_type"),
      diagnosis_disease_group:
        entryLabel(diagnosis, "disease_group") ||
        entryLabel(observation, "source_diagnosis_disease_group"),
      diagnosis_subgroup:
        entryLabel(diagnosis, "disease_subgroup") ||
        entryLabel(observation, "source_diagnosis_subgroup"),
      diagnosis_primary_site:
        entryLabel(diagnosis, "primary_site") ||
        entryLabel(observation, "source_diagnosis_primary_site"),
      diagnosis_laterality:
        entryLabel(diagnosis, "laterality") ||
        entryLabel(observation, "source_diagnosis_laterality"),
      grade:
        entryLabel(histopathologies[0], "histopathology_grade") ||
        entryLabel(observation, "source_grade"),
      is_draft: Boolean(observation.is_draft),
      can_edit: false,
      history: history
        ? {
            id: history.id,
            marital_status: entryLabel(history, "marital_status"),
            dietary_habit: entryLabel(history, "dietary_habits"),
            height_cm:
              typeof history.height_cm === "number"
                ? history.height_cm
                : Number(history.height_cm) || null,
            weight_kg:
              typeof history.weight_kg === "number"
                ? history.weight_kg
                : Number(history.weight_kg) || null,
            bmi:
              typeof history.bmi === "number"
                ? history.bmi
                : Number(history.bmi) || null,
            alcohol_history: entryLabel(
              history,
              "history_of_alcohol_consumption",
            ),
            radiotherapy_to_chest: entryLabel(history, "radiotherapy_to_chest"),
            family_cancer_history: entryLabel(history, "family_cancer_history"),
            known_mutation: entryLabel(history, "any_known_mutations"),
            first_diagnosis_date: entryDate(history.first_diagnosis_date),
            smoking_histories: entryRows(entry, "smoking_history_records").map(
              (item) => ({
                id: item.id,
                status: entryLabel(item, "smoking_history"),
                cigarettes_per_day: Number(item.cigarettes_per_day) || null,
                duration_years: Number(item.smoking_duration_in_years) || null,
                pack_years: Number(item.pack_years) || null,
                quit_period_years: Number(item.quit_smoking_for_years) || null,
              }),
            ),
            tb_histories: entryRows(entry, "tb_history_records").map(
              (item) => ({
                id: item.id,
                status: entryLabel(item, "tb_history"),
                date: entryDate(item.tb_treatment_start_date),
                treatment: entryLabel(item, "treatment_details"),
              }),
            ),
            covid_histories: entryRows(entry, "covid_history_records").map(
              (item) => ({
                id: item.id,
                status: entryLabel(item, "covid_history"),
                date: entryDate(item.covid_infection_date),
                vaccine_name: entryLabel(item, "vaccine_name"),
                vaccination_dose: entryLabel(item, "vaccination_dose"),
              }),
            ),
          }
        : null,
      diagnoses: diagnoses.map((item) => ({
        id: item.id,
        detail: entryLabel(item, "diagnosis_in_details"),
      })),
      metastatic_sites: entryLabels(diagnosis, "metastatic_sites"),
      comorbidities: entryRows(entry, "comorbidities").map((item) => ({
        id: item.id,
        detail: entryLabel(item, "comorbidity"),
      })),
      histopathologies: histopathologies.map((item) => ({
        id: item.id,
        detail: entryLabel(item, "histopathology_details"),
        site: entryLabel(item, "histopathology_site"),
        histology_type: entryLabel(item, "histopathology_type"),
        observed_on: entryDate(item.biopsy_date),
      })),
      molecular_pathologies: entryRows(entry, "molecular_pathologies").map(
        (item) => ({
          id: item.id,
          specimen: entryLabel(item, "specimen"),
          method: entryLabel(item, "method"),
          gene: entryLabel(item, "gene"),
          exon: entryLabel(item, "exon"),
          status: entryLabel(item, "result"),
          observed_on: entryDate(item.tested_at),
        }),
      ),
      cancer_markers: entryRows(entry, "cancer_markers").map((item) => ({
        id: item.id,
        name: entryLabel(item, "marker_name"),
        value:
          entryLabel(item, "raw_value") ||
          entryLabel(item, "marker_value") ||
          entryLabel(item, "numeric_value"),
        unit: entryLabel(item, "marker_unit"),
        observed_on: entryDate(item.tested_at),
      })),
      clinical_stagings: clinicalStage.map((item) => ({
        id: item.id,
        t: entryLabel(item, "raw_t"),
        n: entryLabel(item, "raw_n"),
        m: entryLabel(item, "raw_m"),
        result: entryLabel(item, "staging") || entryLabel(item, "raw_stage"),
        staged_on: entryDate(item.staged_at),
      })),
      pathological_stagings: pathologicalStage.map((item) => ({
        id: item.id,
        t: entryLabel(item, "raw_t"),
        n: entryLabel(item, "raw_n"),
        m: entryLabel(item, "raw_m"),
        result: entryLabel(item, "staging") || entryLabel(item, "raw_stage"),
        staged_on: entryDate(item.staged_at),
      })),
      pathological_staging_details: pathologicalDetails.map((item) => ({
        id: item.id,
        lvsi: entryLabel(item, "lvsi"),
        pni: entryLabel(item, "pni"),
        margin: entryLabel(item, "margin"),
        ki67: entryLabel(item, "ki67"),
        staged_on: entryDate(item.staged_at),
      })),
      ihc_panels: ihcPanels.map((panel) => ({
        id: panel.id,
        observed_on: entryDate(panel.tested_at),
        details: ihcResults
          .filter((item) => String(item.panel) === String(panel.id))
          .map((item) => ({
            id: item.id,
            marker_type:
              entryLabel(item, "cycle") || entryLabel(item, "raw_marker_type"),
            value: entryLabel(item, "result") || entryLabel(item, "raw_result"),
          })),
      })),
      treatment_cycles: cycles.map((cycle) => {
        const outcome = cycle.outcome as RawEntriesRecord | null;
        const recist = entryRows(cycle, "recist11_assessments")[0];
        const irecist = entryRows(cycle, "irecist_assessments")[0];
        const pathological = entryRows(
          cycle,
          "pathological_response_records",
        )[0];
        return {
          id: cycle.id,
          current_chemo_protocol:
            entryLabel(cycle, "current_treatment_protocol") ||
            entryLabel(cycle, "treatment_protocol"),
          chemo_cycle_no:
            entryLabel(cycle, "raw_chemo_cycle_no") ||
            entryLabel(cycle, "chemo_cycle_no"),
          chemo_detail: entryLabel(cycle, "chemotherapy_details"),
          chemo_starting_date: entryDate(cycle.started_at),
          chemo_end_date: entryDate(cycle.ended_at),
          line_of_treatment: entryLabel(cycle, "line_of_treatment"),
          disease_progression_status: entryLabel(
            outcome ?? undefined,
            "disease_progression_status",
          ),
          disease_progression_status_date: entryDate(
            outcome?.progression_status_date,
          ),
          survival_status: entryLabel(outcome ?? undefined, "survival_status"),
          survival_status_date: entryDate(outcome?.survival_status_date),
          recist_1_target_lesion: entryLabel(recist, "target_lesion"),
          recist_1_non_target_lesion: entryLabel(recist, "non_target_lesion"),
          recist_1_new_lesion: entryLabel(recist, "new_lesion"),
          recist_1_result: entryLabel(recist, "response_result"),
          recist_1_date: entryDate(recist?.assessed_at),
          recist_1_method_of_estimation: entryLabel(
            recist,
            "estimation_method",
          ),
          irecist_target_lesion: entryLabel(irecist, "target_lesion"),
          irecist_non_target_lesion: entryLabel(irecist, "non_target_lesion"),
          irecist_new_lesion: entryLabel(irecist, "new_lesion"),
          irecist_result: entryLabel(irecist, "response_result"),
          irecist_date: entryDate(irecist?.assessed_at),
          irecist_method_of_estimation: entryLabel(
            irecist,
            "estimation_method",
          ),
          pathological_response_rate_target_lesion: entryLabel(
            pathological,
            "target_lesion",
          ),
          pathological_response_rate_non_target_lesion: entryLabel(
            pathological,
            "non_target_lesion",
          ),
          pathological_response_rate_new_lesion: entryLabel(
            pathological,
            "new_lesion",
          ),
          pathological_response_rate_result: entryLabel(
            pathological,
            "response_result",
          ),
          pathological_response_rate_date: entryDate(pathological?.assessed_at),
          pathological_method_of_estimation: entryLabel(
            pathological,
            "estimation_method",
          ),
          progression_free_survival:
            entryLabel(outcome ?? undefined, "raw_pfs") ||
            (outcome?.pfs_months ? `${outcome.pfs_months} months` : null),
          overall_survival:
            entryLabel(outcome ?? undefined, "raw_overall_survival") ||
            (outcome?.overall_survival_months
              ? `${outcome.overall_survival_months} months`
              : null),
          chemotherapy_protocols: [],
          chemotherapy_modalities: entryLabels(cycle, "modalities").map(
            (item) => ({ id: item.id, detail: item.value }),
          ),
        };
      }),
      past_treatment_histories: entryRows(
        entry,
        "past_treatment_histories",
      ).map((item) => ({
        id: item.id,
        detail: entryLabel(item, "details"),
        date: entryDate(item.recorded_at),
      })),
      radiotherapy_schedules: entryRows(entry, "radiotherapy_schedules").map(
        (item) => ({
          id: item.id,
          start_date: entryDate(item.started_at),
          end_date: entryDate(item.ended_at),
          intent: entryLabel(item, "radiotherapy_intent"),
          fraction: entryLabel(item, "fraction_dose"),
          fraction_number: entryLabel(item, "fraction_count"),
          total_dose: entryLabel(item, "total_dose"),
          sites: entryLabels(item, "sites"),
          modalities: entryLabels(item, "modalities"),
        }),
      ),
      surgeries: entryRows(entry, "surgeries").map((item) => ({
        id: item.id,
        surgery_date: entryDate(item.surgery_date),
        modality: entryLabel(item, "surgery_modality"),
        lateralities: entryLabels(item, "lateralities"),
      })),
    };
  });

  return {
    id: patient.id,
    legacy_id: typeof patient.legacy_id === "number" ? patient.legacy_id : null,
    registry_id: entryLabel(patient, "patient_id") || "",
    legacy_unique_id: entryLabel(patient, "legacy_unique_id"),
    registration_no: entryLabel(patient, "registration_no"),
    name: entryLabel(patient, "name") || "Unnamed patient",
    phone: entryLabel(patient, "phone"),
    email: entryLabel(patient, "email"),
    nid: entryLabel(patient, "nid"),
    date_of_birth: entryDate(patient.date_of_birth),
    age: Number(patient.age) || null,
    gender: entryLabel(patient, "sex"),
    blood_group: entryLabel(patient, "blood_group"),
    area: entryLabel(patient, "area"),
    police_station: entryLabel(patient, "thana"),
    district: entryLabel(patient, "district"),
    socio_economic_status: entryLabel(patient, "economic_status"),
    passport: entryLabel(patient, "passport"),
    patient_type: entryLabel(patient, "type_of_patient"),
    is_draft: Boolean(patient.is_draft),
    can_edit: false,
    observations,
  };
}

export function createEntriesIntake(payload: EntriesIntakePayload) {
  return saveNormalizedEntry(payload, false);
}

export function saveEntriesDraft(payload: EntriesIntakePayload) {
  return saveNormalizedEntry(payload, true) as Promise<{
    patient_id: number;
    patient_identifier: string;
    observation_id: number;
    status: "draft";
  }>;
}

type RawRecord = Record<string, unknown>;

function defined(value: unknown) {
  return value !== undefined && value !== null && value !== "";
}

function pick(source: RawRecord, keys: string[]) {
  return Object.fromEntries(keys.filter((key) => defined(source[key])).map((key) => [key, source[key]]));
}

/**
 * The entry screen predates the normalized REST API.  Keep its UI contract,
 * but persist each section through the current records endpoints.
 */
async function saveNormalizedEntry(payload: EntriesIntakePayload, draft: boolean) {
  const patientInput = payload.patient ?? {};
  const observationInput = payload.observation ?? {};
  let patient: RawRecord;
  if (payload.existing_patient_id) {
    patient = await request<RawRecord>(`/api/records/patients/${payload.existing_patient_id}/`, {
      method: "PATCH",
      body: JSON.stringify(pick(patientInput, [
        "name", "phone", "email", "nid", "passport", "sex", "date_of_birth", "age",
        "district", "thana", "area", "economic_status", "blood_group", "type_of_patient",
      ])),
    });
  } else {
    const suffix = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    patient = await request<RawRecord>("/api/records/patients/", {
      method: "POST",
      body: JSON.stringify({
        ...pick(patientInput, [
          "name", "phone", "email", "nid", "passport", "sex", "date_of_birth", "age",
          "district", "thana", "area", "economic_status", "blood_group", "type_of_patient",
        ]),
        registration_no: String(patientInput.registration_no || `REG-${suffix}`),
        patient_id: String(patientInput.patient_id || `LCR-${suffix}`),
        is_draft: draft,
      }),
    });
  }
  const patientId = Number(patient.id);
  const history = payload.history ?? {};
  await request<RawRecord>(`/api/records/patients/${patientId}/`, {
    method: "PATCH",
    body: JSON.stringify(pick({
      ...history,
      marital_status: history.marital_status,
      alcohol_history: history.history_of_alcohol_consumption,
      first_diagnosis_date: history.first_diagnosis_date,
      dietary_habits: history.dietary_habits,
      personal_history_of_cancer: history.personal_or_family_history_of_cancer || history.cancer_history,
      family_history_of_cancer: history.family_cancer_history,
      any_known_mutation: history.any_known_mutations,
      smoking_history: payload.smoking_history_records?.[0]?.smoking_history,
      cigarettes_per_day: payload.smoking_history_records?.[0]?.cigarettes_per_day,
      smoking_duration_in_years: payload.smoking_history_records?.[0]?.smoking_duration_in_years,
      quit_smoking_for_in_years: payload.smoking_history_records?.[0]?.quit_smoking_for_years,
      tb_history: payload.tb_history_records?.[0]?.tb_history,
      covid_history: payload.covid_history_records?.[0]?.covid_history,
      covid_infection_date: payload.covid_history_records?.[0]?.covid_infection_date,
      vaccine: payload.covid_history_records?.[0]?.vaccine_name,
      vaccination_dose: payload.covid_history_records?.[0]?.vaccination_dose,
    }, ["marital_status", "alcohol_history", "first_diagnosis_date", "dietary_habits", "personal_history_of_cancer", "family_history_of_cancer", "any_known_mutation", "smoking_history", "cigarettes_per_day", "smoking_duration_in_years", "quit_smoking_for_in_years", "tb_history", "covid_history", "covid_infection_date", "vaccine", "vaccination_dose"])),
  });
  const observation = await request<RawRecord>("/api/records/observations/", {
    method: "POST",
    body: JSON.stringify({
      patient: patientId,
      ...pick(observationInput, ["doctor", "center", "observed_at", "prescription_date", "prescription_age_years", "prescription_age_months", "prescription_age_days"]),
      status: draft ? "draft" : "published",
    }),
  });
  const observationId = Number(observation.id);
  const post = (path: string, body: RawRecord) => request<RawRecord>(path, { method: "POST", body: JSON.stringify(body) });
  if (defined(history.height_cm) || defined(history.weight_kg)) {
    await post("/api/records/anthropometries/", {
      observation: observationId,
      ...pick(history, ["height_cm", "weight_kg"]),
    });
  }
  await Promise.all((payload.comorbidities ?? []).map((row) => post("/api/records/comorbidities/", { observation: observationId, ...row })));
  for (const row of payload.diagnoses ?? []) {
    const diagnosis = await post("/api/records/diagnoses/", { observation: observationId, ...pick(row, ["disease_group", "disease_subgroup", "primary_site", "laterality", "diagnosis_in_details"]) });
    await Promise.all(((row.metastatic_sites as number[] | undefined) ?? []).map((site) => post("/api/records/metastatic-sites/", { diagnosis: diagnosis.id, site })));
  }
  await Promise.all((payload.histopathologies ?? []).map((row) => post("/api/records/histopathologies/", { observation: observationId, ...row })));
  for (const panel of payload.ihc_panels ?? []) {
    const panelRecord = panel as RawRecord;
    await Promise.all(
      ((panelRecord.results as RawRecord[] | undefined) ?? []).map((result) =>
        post("/api/records/ihc-results/", {
          observation: observationId,
          tested_at: panelRecord.tested_at,
          marker: result.cycle,
          result: result.result,
        }),
      ),
    );
    if (!draft) await request<RawRecord>(`/api/records/molecular-tests/${test.id}/finalize/`, { method: "POST" });
    await Promise.all(
      ((panelRecord.staging_results as RawRecord[] | undefined) ?? []).map((result) =>
        post("/api/records/pathological-staging-results/", {
          observation: observationId,
          assessed_at: panelRecord.tested_at,
          feature: result.cycle,
          result: result.result,
        }),
      ),
    );
  }
  await Promise.all((payload.clinical_tnm_stagings ?? []).map((row) => post("/api/records/clinical-tnm-stagings/", { observation: observationId, t: row.t, n: row.n, m: row.m, stage: row.stage, staged_on: row.staged_at })));
  await Promise.all((payload.pathological_tnm_stagings ?? []).map((row) => post("/api/records/pathological-tnm-stagings/", { observation: observationId, t: row.t, n: row.n, m: row.m, stage: row.stage, staged_on: row.staged_at })));
  await Promise.all((payload.cancer_markers ?? []).map((row) => post("/api/records/cancer-marker-results/", { observation: observationId, marker: row.marker_name, value: row.marker_value, tested_on: row.tested_at })));
  for (const row of payload.molecular_tests ?? []) {
    const test = await post("/api/records/molecular-tests/", {
      observation: observationId,
      ...pick(row, ["panel_version", "method", "specimen", "specimen_collected_on", "tested_on", "reported_on", "qc_status", "laboratory", "accession_number", "notes"]),
      status: "draft",
    });
    await Promise.all(
      ((row.results as RawRecord[] | undefined) ?? []).map((result) =>
        post("/api/records/molecular-test-results/", {
          molecular_test: test.id,
          ...pick(result, ["panel_target", "gene", "exon", "alteration_type", "result", "partner_gene", "clinical_significance", "dna_change", "protein_change", "common_name", "variant_allele_frequency", "copy_number", "notes"]),
        }),
      ),
    );
  }
  for (const row of payload.treatment_cycles ?? []) {
    const modality = Array.isArray(row.modalities) ? row.modalities[0] : undefined;
    const protocol = row.treatment_protocol;
    if (modality && protocol) {
      const course = await post("/api/records/treatment-courses/", { observation: observationId, modality, protocol, line_of_treatment: row.line_of_treatment, started_on: row.started_at, ended_on: row.ended_at, status: row.status, reason_for_stopping: row.reason_for_stopping, notes: row.course_notes || row.chemotherapy_details });
      await Promise.all(((row.administrations as RawRecord[] | undefined) ?? []).map((administration) => post("/api/records/treatment-administrations/", { treatment_course: course.id, observation: observationId, ...administration })));
      await Promise.all(((row.recist11_assessments as RawRecord[] | undefined) ?? []).map((assessment) => post("/api/records/recist11-assessments/", { observation: observationId, treatment_course: course.id, assessed_on: assessment.assessed_at, timepoint: "on_treatment", target_lesion: assessment.target_lesion, non_target_lesion: assessment.non_target_lesion, new_lesion: assessment.new_lesion, overall_response: assessment.response_result, estimation_method: assessment.estimation_method })));
      await Promise.all(((row.irecist_assessments as RawRecord[] | undefined) ?? []).map((assessment) => post("/api/records/irecist-assessments/", { observation: observationId, treatment_course: course.id, assessed_on: assessment.assessed_at, timepoint: "on_treatment", target_lesion: assessment.target_lesion, non_target_lesion: assessment.non_target_lesion, new_lesion: assessment.new_lesion, overall_response: assessment.response_result, estimation_method: assessment.estimation_method })));
      await Promise.all(((row.pathological_response_records as RawRecord[] | undefined) ?? []).filter((assessment) => Boolean(assessment.assessed_at)).map((assessment) => post("/api/records/pathological-response-assessments/", { observation: observationId, treatment_course: course.id, assessed_on: assessment.assessed_at, timepoint: "post_treatment", response_category: assessment.response_category, residual_viable_tumor_percentage: assessment.residual_viable_tumor_percentage, tumor_regression_grade: assessment.tumor_regression_grade, estimation_method: assessment.estimation_method })));
    }
  }
  await Promise.all((payload.progression_records ?? []).map((record) => post("/api/records/disease-progression-records/", { observation: observationId, ...record })));
  await Promise.all((payload.survival_followups ?? []).map((record) => post("/api/records/survival-followups/", { observation: observationId, ...record })));
  await Promise.all((payload.surgeries ?? []).map((surgery) => post("/api/records/surgeries/", {
    observation: observationId,
    modality: surgery.surgery_modality,
    laterality: Array.isArray(surgery.lateralities) ? surgery.lateralities[0] : undefined,
    surgery_date: surgery.surgery_date,
    status: surgery.status,
    procedure_details: surgery.procedure_details,
    operative_findings: surgery.operative_findings,
    complications: surgery.complications,
    notes: surgery.notes,
  })));
  await Promise.all((payload.radiotherapy_schedules ?? []).map((course) => post("/api/records/radiotherapy-courses/", {
    observation: observationId,
    site: Array.isArray(course.sites) ? course.sites[0] : undefined,
    intent: course.radiotherapy_intent,
    modality: Array.isArray(course.modalities) ? course.modalities[0] : undefined,
    started_on: course.started_at,
    ended_on: course.ended_at,
    dose_per_fraction_cgy: course.fraction_dose,
    planned_fractions: course.fraction_count,
    completed_fractions: course.completed_fractions,
    status: course.status,
    reason_for_stopping: course.reason_for_stopping,
    notes: course.notes,
  })));
  const result = { patient_id: patientId, patient_identifier: String(patient.patient_id), observation_id: observationId };
  return draft ? { ...result, status: "draft" as const } : result;
}

export function fetchEntriesDraft(patientId: number) {
  // Draft status is represented by ClinicalObservation.status in the current
  // backend.  The form state itself is browser-owned, so there is no stale
  // legacy draft payload endpoint to call.
  void patientId;
  return Promise.resolve<{
    draft: null | {
      observation_id: number
      saved_at: string
      payload: Record<string, unknown>
    }
  }>({ draft: null })
}

export function buildPatientExportUrl(
  query: string,
  state = "all",
  sort = "name",
  direction = "asc",
) {
  const params = new URLSearchParams();
  if (query) {
    params.set("q", query);
  }
  if (state !== "all") {
    params.set("state", state);
  }
  params.set("sort", sort);
  params.set("dir", direction);

  return `${API_BASE_URL}/api/entries/workspace/patients/export/?${params.toString()}`;
}

export function refreshLongitudinalAnalytics() {
  return request<{ status: 'current' | 'failed'; reason: string }>('/api/longitudinal-analytics/refresh/', { method: 'POST' })
}
