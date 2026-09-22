// LEGACY_UI: superseded by EntriesPatientEntryPage; it targets retired patient endpoints.
import { type Dispatch, type FormEvent, type SetStateAction, useDeferredValue, useEffect, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, CalendarDays, ChevronLeft, ChevronRight, Plus, Search, Trash2 } from 'lucide-react'
import {
  createPatientEntry,
  fetchPatientDemographics,
  fetchRegistryPatients,
  fetchRegistryPatientDetail,
  type ApiError,
  type PatientDetail,
  type PatientEntryPayload,
  updatePatientEntry,
} from '../api'

type MarkerForm = { name: string; value: string; unit: string; observed_on: string }
type HistoryForm = {
  marital_status: string
  dietary_habit: string
  height_cm: string
  weight_kg: string
  bmi: string
  alcohol_history: string
  radiotherapy_to_chest: string
  family_cancer_history: string
  known_mutation: string
  first_diagnosis_date: string
}
type SmokingForm = {
  status: string
  cigarettes_per_day: string
  duration_years: string
  pack_years: string
  quit_period_years: string
}
type TbForm = { status: string; date: string; treatment: string }
type CovidForm = { status: string; date: string; vaccine_name: string; vaccination_dose: string }
type HistopathologyForm = { detail: string; site: string; histology_type: string; observed_on: string }
type MolecularForm = {
  specimen: string
  method: string
  gene: string
  exon: string
  status: string
  observed_on: string
}
type IHCDetailForm = { marker_type: string; value: string }
type IHCPanelForm = { observed_on: string; details: IHCDetailForm[] }
type TreatmentCycleForm = {
  current_chemo_protocol: string
  chemo_cycle_no: string
  chemo_detail: string
  chemo_starting_date: string
  chemo_end_date: string
  line_of_treatment: string
  disease_progression_status: string
  disease_progression_status_date: string
  survival_status: string
  survival_status_date: string
}
type PastTreatmentForm = { detail: string; date: string }
type RadiotherapyForm = {
  start_date: string
  end_date: string
  intent: string
  fraction: string
  fraction_number: string
  total_dose: string
  sites_text: string
  modalities_text: string
}
type SurgeryForm = { surgery_date: string; modality: string; lateralities_text: string }

const steps = [
  { key: 'demography', label: 'Patient Demography' },
  { key: 'diagnosis', label: 'Diagnosis' },
  { key: 'treatment', label: 'Treatment' },
] as const

function splitTextValues(value: string) {
  return value
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function emptyMarker(): MarkerForm {
  return { name: '', value: '', unit: '', observed_on: '' }
}

function emptyHistory(): HistoryForm {
  return {
    marital_status: '',
    dietary_habit: '',
    height_cm: '',
    weight_kg: '',
    bmi: '',
    alcohol_history: '',
    radiotherapy_to_chest: '',
    family_cancer_history: '',
    known_mutation: '',
    first_diagnosis_date: '',
  }
}

function emptySmoking(): SmokingForm {
  return {
    status: '',
    cigarettes_per_day: '',
    duration_years: '',
    pack_years: '',
    quit_period_years: '',
  }
}

function emptyTb(): TbForm {
  return { status: '', date: '', treatment: '' }
}

function emptyCovid(): CovidForm {
  return { status: '', date: '', vaccine_name: '', vaccination_dose: '' }
}

function emptyHistopathology(): HistopathologyForm {
  return { detail: '', site: '', histology_type: '', observed_on: '' }
}

function emptyMolecular(): MolecularForm {
  return {
    specimen: '',
    method: '',
    gene: '',
    exon: '',
    status: '',
    observed_on: '',
  }
}

function emptyIhcDetail(): IHCDetailForm {
  return { marker_type: '', value: '' }
}

function emptyIhcPanel(): IHCPanelForm {
  return { observed_on: '', details: [emptyIhcDetail()] }
}

function emptyTreatmentCycle(): TreatmentCycleForm {
  return {
    current_chemo_protocol: '',
    chemo_cycle_no: '',
    chemo_detail: '',
    chemo_starting_date: '',
    chemo_end_date: '',
    line_of_treatment: '',
    disease_progression_status: '',
    disease_progression_status_date: '',
    survival_status: '',
    survival_status_date: '',
  }
}

function emptyPastTreatment(): PastTreatmentForm {
  return { detail: '', date: '' }
}

function emptyRadiotherapy(): RadiotherapyForm {
  return {
    start_date: '',
    end_date: '',
    intent: '',
    fraction: '',
    fraction_number: '',
    total_dose: '',
    sites_text: '',
    modalities_text: '',
  }
}

function emptySurgery(): SurgeryForm {
  return { surgery_date: '', modality: '', lateralities_text: '' }
}

function dateOnly(value: string) {
  return value ? value.slice(0, 10) : ''
}

function parseDateInput(value: string) {
  if (!value) {
    return null
  }
  const parsed = new Date(`${value}T00:00:00`)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

function formatDateInput(value: Date) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function formatDisplayDate(value: string) {
  const [year, month, day] = value.split('-')
  return year && month && day ? `${day}/${month}/${year}` : ''
}

function parseDisplayDate(value: string) {
  const match = value.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)
  if (!match) {
    return null
  }
  const [, dayValue, monthValue, year] = match
  const day = Number(dayValue)
  const month = Number(monthValue)
  const date = new Date(Number(year), month - 1, day)
  if (
    date.getFullYear() !== Number(year) ||
    date.getMonth() !== month - 1 ||
    date.getDate() !== day
  ) {
    return null
  }
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

function DateField({
  value,
  onChange,
  readOnly = false,
}: {
  value: string
  onChange?: (value: string) => void
  readOnly?: boolean
}) {
  const [displayValue, setDisplayValue] = useState(() => formatDisplayDate(value))
  const pickerRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setDisplayValue(formatDisplayDate(value))
  }, [value])

  return (
    <div className="date-field-control">
      <input
        className="auth-input"
        inputMode="numeric"
        placeholder="DD/MM/YYYY"
        value={displayValue}
        readOnly={readOnly}
        onChange={(event) => {
          const nextValue = event.target.value
          setDisplayValue(nextValue)
          const parsed = parseDisplayDate(nextValue)
          if (parsed) {
            onChange?.(parsed)
          } else if (!nextValue) {
            onChange?.('')
          }
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
        onChange={(event) => onChange?.(event.target.value)}
      />
    </div>
  )
}

function DateTimeField({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const date = dateOnly(value)
  const time = value.slice(11, 16)

  return (
    <div className="date-time-field">
      <DateField
        value={date}
        onChange={(nextDate) => onChange(nextDate ? `${nextDate}T${time || '00:00'}` : '')}
      />
      <input
        className="auth-input date-time-input"
        type="time"
        value={time}
        onChange={(event) => onChange(`${date || formatDateInput(new Date())}T${event.target.value}`)}
        aria-label="Observation time"
      />
    </div>
  )
}

function formatDateTimeLocal(value: string | null | undefined) {
  if (!value) {
    return ''
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value.slice(0, 16)
  }
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day}T${hours}:${minutes}`
}

function calculateAgeAtDate(dateOfBirth: string, referenceDate: string) {
  const dob = parseDateInput(dateOfBirth)
  const reference = parseDateInput(referenceDate)
  if (!dob || !reference) {
    return null
  }
  let years = reference.getFullYear() - dob.getFullYear()
  if (
    reference.getMonth() < dob.getMonth() ||
    (reference.getMonth() === dob.getMonth() && reference.getDate() < dob.getDate())
  ) {
    years -= 1
  }
  return Math.max(years, 0)
}

function estimateDateOfBirthFromAge(ageValue: string, referenceDate: string) {
  const age = Number(ageValue)
  const reference = parseDateInput(referenceDate)
  if (!Number.isFinite(age) || age < 0 || !reference) {
    return ''
  }
  const estimated = new Date(reference)
  estimated.setFullYear(estimated.getFullYear() - age)
  return formatDateInput(estimated)
}

export default function PatientEntryPage() {
  const { registryId = '' } = useParams()
  const navigate = useNavigate()
  const isEditMode = Boolean(registryId)
  const [activeStep, setActiveStep] = useState(0)
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [saveMode, setSaveMode] = useState<'draft' | 'published'>('draft')
  const [ageInputMode, setAgeInputMode] = useState<'dob' | 'age'>('dob')
  const [editingObservationId, setEditingObservationId] = useState<number | null>(null)
  const [formHydrated, setFormHydrated] = useState(false)
  const [patient, setPatient] = useState({
    registry_id: '',
    legacy_unique_id: '',
    registration_no: '',
    name: '',
    phone: '',
    email: '',
    nid: '',
    date_of_birth: '',
    age: '',
    gender: '',
    blood_group: '',
    area: '',
    police_station: '',
    district: '',
    socio_economic_status: '',
    passport: '',
    patient_type: '',
  })
  const [observation, setObservation] = useState({
    observed_at: '',
    consulting_doctor_name: '',
    center_name: '',
    cancer_type: '',
    diagnosis_disease_group: '',
    diagnosis_subgroup: '',
    diagnosis_primary_site: '',
    diagnosis_laterality: '',
    grade: '',
    laterality_notes: '',
    diagnoses_text: '',
    metastatic_sites_text: '',
    comorbidities_text: '',
    clinical_t: '',
    clinical_n: '',
    clinical_m: '',
    clinical_result: '',
    clinical_staged_on: '',
    pathological_t: '',
    pathological_n: '',
    pathological_m: '',
    pathological_result: '',
    pathological_staged_on: '',
    pathological_lvsi: '',
    pathological_pni: '',
    pathological_margin: '',
    pathological_ki67: '',
    pathological_detail_staged_on: '',
  })
  const [history, setHistory] = useState(emptyHistory())
  const [smokingHistories, setSmokingHistories] = useState<SmokingForm[]>([emptySmoking()])
  const [tbHistories, setTbHistories] = useState<TbForm[]>([emptyTb()])
  const [covidHistories, setCovidHistories] = useState<CovidForm[]>([emptyCovid()])
  const [markers, setMarkers] = useState<MarkerForm[]>([emptyMarker()])
  const [histopathologies, setHistopathologies] = useState<HistopathologyForm[]>([
    emptyHistopathology(),
  ])
  const [molecularPathologies, setMolecularPathologies] = useState<MolecularForm[]>([
    emptyMolecular(),
  ])
  const [ihcPanels, setIhcPanels] = useState<IHCPanelForm[]>([emptyIhcPanel()])
  const [treatmentCycles, setTreatmentCycles] = useState<TreatmentCycleForm[]>([
    emptyTreatmentCycle(),
  ])
  const [pastTreatments, setPastTreatments] = useState<PastTreatmentForm[]>([
    emptyPastTreatment(),
  ])
  const [radiotherapySchedules, setRadiotherapySchedules] = useState<RadiotherapyForm[]>([
    emptyRadiotherapy(),
  ])
  const [surgeries, setSurgeries] = useState<SurgeryForm[]>([emptySurgery()])
  const [recordLookupTerm, setRecordLookupTerm] = useState('')
  const patientDetailQuery = useQuery({
    queryKey: ['patient-edit-detail', registryId],
    queryFn: () => fetchRegistryPatientDetail(registryId),
    enabled: isEditMode,
  })
  const demographicsQuery = useQuery({
    queryKey: ['patient-demographics', patient.district, observation.diagnosis_disease_group],
    queryFn: () => fetchPatientDemographics(patient.district, observation.diagnosis_disease_group),
  })
  const demographics = demographicsQuery.data
  const deferredDuplicateLookupTerm = useDeferredValue(recordLookupTerm.trim())
  const duplicateLookupQuery = useQuery({
    queryKey: ['entry-duplicate-check', deferredDuplicateLookupTerm],
    queryFn: () => fetchRegistryPatients(deferredDuplicateLookupTerm, 1, 6),
    enabled: !isEditMode && deferredDuplicateLookupTerm.length >= 3,
  })
  const duplicateMatches = duplicateLookupQuery.data?.results ?? []
  const ageReferenceDate = history.first_diagnosis_date || dateOnly(observation.observed_at) || formatDateInput(new Date())
  const ageAtDiagnosis =
    patient.date_of_birth && history.first_diagnosis_date
      ? calculateAgeAtDate(patient.date_of_birth, history.first_diagnosis_date)
      : null

  useEffect(() => {
    if (ageInputMode !== 'age' || !patient.age) {
      return
    }
    const estimatedDob = estimateDateOfBirthFromAge(patient.age, ageReferenceDate)
    setPatient((current) =>
      current.date_of_birth === estimatedDob ? current : { ...current, date_of_birth: estimatedDob },
    )
  }, [ageInputMode, ageReferenceDate, patient.age])

  useEffect(() => {
    if (!isEditMode || !patientDetailQuery.data || formHydrated) {
      return
    }
    const detail: PatientDetail = patientDetailQuery.data
    const sourceObservation = detail.observations[0] ?? null
    const sourceHistory = sourceObservation?.history ?? null
    const sourceClinicalStage = sourceObservation?.clinical_stagings[0] ?? null
    const sourcePathologicalStage = sourceObservation?.pathological_stagings[0] ?? null
    const sourcePathologicalDetail = sourceObservation?.pathological_staging_details[0] ?? null

    setPatient({
      registry_id: detail.registry_id || '',
      legacy_unique_id: detail.legacy_unique_id || '',
      registration_no: detail.registration_no || '',
      name: detail.name || '',
      phone: detail.phone || '',
      email: detail.email || '',
      nid: detail.nid || '',
      date_of_birth: dateOnly(detail.date_of_birth || ''),
      age: detail.age != null ? String(detail.age) : '',
      gender: detail.gender || '',
      blood_group: detail.blood_group || '',
      area: detail.area || '',
      police_station: detail.police_station || '',
      district: detail.district || '',
      socio_economic_status: detail.socio_economic_status || '',
      passport: detail.passport || '',
      patient_type: detail.patient_type || '',
    })
    setObservation({
      observed_at: formatDateTimeLocal(sourceObservation?.observed_at),
      consulting_doctor_name: sourceObservation?.consulting_doctor_name || '',
      center_name: sourceObservation?.center_name || '',
      cancer_type: sourceObservation?.cancer_type || '',
      diagnosis_disease_group: sourceObservation?.diagnosis_disease_group || '',
      diagnosis_subgroup: sourceObservation?.diagnosis_subgroup || '',
      diagnosis_primary_site: sourceObservation?.diagnosis_primary_site || '',
      diagnosis_laterality: sourceObservation?.diagnosis_laterality || '',
      grade: sourceObservation?.grade || '',
      laterality_notes: '',
      diagnoses_text: (sourceObservation?.diagnoses ?? []).map((item) => item.detail).filter(Boolean).join('\n'),
      metastatic_sites_text: (sourceObservation?.metastatic_sites ?? []).map((item) => item.value).filter(Boolean).join('\n'),
      comorbidities_text: (sourceObservation?.comorbidities ?? []).map((item) => item.detail).filter(Boolean).join('\n'),
      clinical_t: sourceClinicalStage?.t || '',
      clinical_n: sourceClinicalStage?.n || '',
      clinical_m: sourceClinicalStage?.m || '',
      clinical_result: sourceClinicalStage?.result || '',
      clinical_staged_on: dateOnly(sourceClinicalStage?.staged_on || ''),
      pathological_t: sourcePathologicalStage?.t || '',
      pathological_n: sourcePathologicalStage?.n || '',
      pathological_m: sourcePathologicalStage?.m || '',
      pathological_result: sourcePathologicalStage?.result || '',
      pathological_staged_on: dateOnly(sourcePathologicalStage?.staged_on || ''),
      pathological_lvsi: sourcePathologicalDetail?.lvsi || '',
      pathological_pni: sourcePathologicalDetail?.pni || '',
      pathological_margin: sourcePathologicalDetail?.margin || '',
      pathological_ki67: sourcePathologicalDetail?.ki67 || '',
      pathological_detail_staged_on: dateOnly(sourcePathologicalDetail?.staged_on || ''),
    })
    setHistory({
      marital_status: sourceHistory?.marital_status || '',
      dietary_habit: sourceHistory?.dietary_habit || '',
      height_cm: sourceHistory?.height_cm != null ? String(sourceHistory.height_cm) : '',
      weight_kg: sourceHistory?.weight_kg != null ? String(sourceHistory.weight_kg) : '',
      bmi: sourceHistory?.bmi != null ? String(sourceHistory.bmi) : '',
      alcohol_history: sourceHistory?.alcohol_history || '',
      radiotherapy_to_chest: sourceHistory?.radiotherapy_to_chest || '',
      family_cancer_history: sourceHistory?.family_cancer_history || '',
      known_mutation: sourceHistory?.known_mutation || '',
      first_diagnosis_date: dateOnly(sourceHistory?.first_diagnosis_date || ''),
    })
    setSmokingHistories(
      sourceHistory?.smoking_histories.length
        ? sourceHistory.smoking_histories.map((item) => ({
            status: item.status || '',
            cigarettes_per_day: item.cigarettes_per_day != null ? String(item.cigarettes_per_day) : '',
            duration_years: item.duration_years != null ? String(item.duration_years) : '',
            pack_years: item.pack_years != null ? String(item.pack_years) : '',
            quit_period_years: item.quit_period_years != null ? String(item.quit_period_years) : '',
          }))
        : [emptySmoking()],
    )
    setTbHistories(
      sourceHistory?.tb_histories.length
        ? sourceHistory.tb_histories.map((item) => ({
            status: item.status || '',
            date: dateOnly(item.date || ''),
            treatment: item.treatment || '',
          }))
        : [emptyTb()],
    )
    setCovidHistories(
      sourceHistory?.covid_histories.length
        ? sourceHistory.covid_histories.map((item) => ({
            status: item.status || '',
            date: dateOnly(item.date || ''),
            vaccine_name: item.vaccine_name || '',
            vaccination_dose: item.vaccination_dose || '',
          }))
        : [emptyCovid()],
    )
    setMarkers(
      sourceObservation?.cancer_markers.length
        ? sourceObservation.cancer_markers.map((item) => ({
            name: item.name || '',
            value: item.value || '',
            unit: item.unit || '',
            observed_on: dateOnly(item.observed_on || ''),
          }))
        : [emptyMarker()],
    )
    setHistopathologies(
      sourceObservation?.histopathologies.length
        ? sourceObservation.histopathologies.map((item) => ({
            detail: item.detail || '',
            site: item.site || '',
            histology_type: item.histology_type || '',
            observed_on: dateOnly(item.observed_on || ''),
          }))
        : [emptyHistopathology()],
    )
    setMolecularPathologies(
      sourceObservation?.molecular_pathologies.length
        ? sourceObservation.molecular_pathologies.map((item) => ({
            specimen: item.specimen || '',
            method: item.method || '',
            gene: item.gene || '',
            exon: item.exon || '',
            status: item.status || '',
            observed_on: dateOnly(item.observed_on || ''),
          }))
        : [emptyMolecular()],
    )
    setIhcPanels(
      sourceObservation?.ihc_panels.length
        ? sourceObservation.ihc_panels.map((panel) => ({
            observed_on: dateOnly(panel.observed_on || ''),
            details: panel.details.length
              ? panel.details.map((detail) => ({
                  marker_type: detail.marker_type || '',
                  value: detail.value || '',
                }))
              : [emptyIhcDetail()],
          }))
        : [emptyIhcPanel()],
    )
    setTreatmentCycles(
      sourceObservation?.treatment_cycles.length
        ? sourceObservation.treatment_cycles.map((item) => ({
            current_chemo_protocol: item.current_chemo_protocol || '',
            chemo_cycle_no: item.chemo_cycle_no || '',
            chemo_detail: item.chemo_detail || '',
            chemo_starting_date: dateOnly(item.chemo_starting_date || ''),
            chemo_end_date: dateOnly(item.chemo_end_date || ''),
            line_of_treatment: item.line_of_treatment || '',
            disease_progression_status: item.disease_progression_status || '',
            disease_progression_status_date: dateOnly(item.disease_progression_status_date || ''),
            survival_status: item.survival_status || '',
            survival_status_date: dateOnly(item.survival_status_date || ''),
          }))
        : [emptyTreatmentCycle()],
    )
    setPastTreatments(
      sourceObservation?.past_treatment_histories.length
        ? sourceObservation.past_treatment_histories.map((item) => ({
            detail: item.detail || '',
            date: dateOnly(item.date || ''),
          }))
        : [emptyPastTreatment()],
    )
    setRadiotherapySchedules(
      sourceObservation?.radiotherapy_schedules.length
        ? sourceObservation.radiotherapy_schedules.map((item) => ({
            start_date: dateOnly(item.start_date || ''),
            end_date: dateOnly(item.end_date || ''),
            intent: item.intent || '',
            fraction: item.fraction || '',
            fraction_number: item.fraction_number || '',
            total_dose: item.total_dose || '',
            sites_text: item.sites.map((site) => site.value).filter(Boolean).join('\n'),
            modalities_text: item.modalities.map((modality) => modality.value).filter(Boolean).join('\n'),
          }))
        : [emptyRadiotherapy()],
    )
    setSurgeries(
      sourceObservation?.surgeries.length
        ? sourceObservation.surgeries.map((item) => ({
            surgery_date: dateOnly(item.surgery_date || ''),
            modality: item.modality || '',
            lateralities_text: item.lateralities.map((laterality) => laterality.value).filter(Boolean).join('\n'),
          }))
        : [emptySurgery()],
    )
    setEditingObservationId(sourceObservation?.id ?? null)
    setSaveMode(sourceObservation?.is_draft || detail.is_draft ? 'draft' : 'published')
    setAgeInputMode(detail.date_of_birth ? 'dob' : detail.age != null ? 'age' : 'dob')
    setFormHydrated(true)
  }, [formHydrated, isEditMode, patientDetailQuery.data])

  const createMutation = useMutation({
    mutationFn: createPatientEntry,
    onSuccess: (response) => {
      setErrorMessage('')
      setSuccessMessage(`Saved ${response.name} (${response.registry_id}). Redirecting...`)
      window.setTimeout(() => {
        navigate(`/patients/${response.registry_id}`)
      }, 700)
    },
    onError: (error) => {
      const apiError = error as ApiError
      setSuccessMessage('')
      setErrorMessage(apiError.message || 'Unable to save patient entry.')
    },
  })
  const updateMutation = useMutation({
    mutationFn: (payload: PatientEntryPayload) => updatePatientEntry(registryId, payload),
    onSuccess: (response) => {
      setErrorMessage('')
      setSuccessMessage(`Updated ${response.name} (${response.registry_id}). Redirecting...`)
      window.setTimeout(() => {
        navigate(`/patients/${response.registry_id}`)
      }, 700)
    },
    onError: (error) => {
      const apiError = error as ApiError
      setSuccessMessage('')
      setErrorMessage(apiError.message || 'Unable to update patient entry.')
    },
  })

  function updateObjectField<T extends Record<string, string>>(
    setter: Dispatch<SetStateAction<T>>,
    name: keyof T,
    value: string,
  ) {
    setter((current) => ({ ...current, [name]: value }))
  }

  function updateArrayItem<T extends Record<string, any>>(
    setter: Dispatch<SetStateAction<T[]>>,
    index: number,
    name: keyof T,
    value: any,
  ) {
    setter((current) =>
      current.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [name]: value } : item,
      ),
    )
  }

  function removeArrayItem<T>(
    setter: Dispatch<SetStateAction<T[]>>,
    index: number,
  ) {
    setter((current) => current.filter((_, itemIndex) => itemIndex !== index))
  }

  function handleDateOfBirthChange(value: string) {
    setAgeInputMode('dob')
    setPatient((current) => ({
      ...current,
      date_of_birth: value,
      age: value ? String(calculateAgeAtDate(value, formatDateInput(new Date())) ?? '') : '',
    }))
  }

  function handleAgeChange(value: string) {
    setAgeInputMode('age')
    setPatient((current) => ({
      ...current,
      age: value,
      date_of_birth: value ? estimateDateOfBirthFromAge(value, ageReferenceDate) : '',
    }))
  }

  function buildPayload(): PatientEntryPayload {
    return {
      observation_id: editingObservationId ?? undefined,
      registry_id: patient.registry_id || undefined,
      legacy_unique_id: patient.legacy_unique_id || undefined,
      registration_no: patient.registration_no || undefined,
      name: patient.name.trim(),
      phone: patient.phone || undefined,
      email: patient.email || undefined,
      nid: patient.nid || undefined,
      date_of_birth: patient.date_of_birth || null,
      age: patient.age ? Number(patient.age) : null,
      gender: patient.gender || undefined,
      blood_group: patient.blood_group || undefined,
      area: patient.area || undefined,
      police_station: patient.police_station || undefined,
      district: patient.district || undefined,
      socio_economic_status: patient.socio_economic_status || undefined,
      passport: patient.passport || undefined,
      patient_type: patient.patient_type || undefined,
      patient_is_draft: saveMode === 'draft',
      observed_at: observation.observed_at || null,
      consulting_doctor_name: observation.consulting_doctor_name || undefined,
      center_name: observation.center_name || undefined,
      cancer_type: observation.cancer_type || undefined,
      diagnosis_disease_group: observation.diagnosis_disease_group || undefined,
      diagnosis_subgroup: observation.diagnosis_subgroup || undefined,
      diagnosis_primary_site: observation.diagnosis_primary_site || undefined,
      diagnosis_laterality: observation.diagnosis_laterality || undefined,
      grade: observation.grade || undefined,
      laterality_notes: observation.laterality_notes || undefined,
      observation_is_draft: saveMode === 'draft',
      history: {
        marital_status: history.marital_status || undefined,
        dietary_habit: history.dietary_habit || undefined,
        height_cm: history.height_cm || null,
        weight_kg: history.weight_kg || null,
        bmi: history.bmi || null,
        alcohol_history: history.alcohol_history || undefined,
        radiotherapy_to_chest: history.radiotherapy_to_chest || undefined,
        family_cancer_history: history.family_cancer_history || undefined,
        known_mutation: history.known_mutation || undefined,
        first_diagnosis_date: history.first_diagnosis_date || null,
      },
      smoking_histories: smokingHistories
        .filter((item) => Object.values(item).some((value) => String(value).trim()))
        .map((item) => ({
          status: item.status || undefined,
          cigarettes_per_day: item.cigarettes_per_day ? Number(item.cigarettes_per_day) : null,
          duration_years: item.duration_years || null,
          pack_years: item.pack_years || null,
          quit_period_years: item.quit_period_years || null,
        })),
      tb_histories: tbHistories
        .filter((item) => Object.values(item).some((value) => String(value).trim()))
        .map((item) => ({
          status: item.status || undefined,
          date: item.date || null,
          treatment: item.treatment || undefined,
        })),
      covid_histories: covidHistories
        .filter((item) => Object.values(item).some((value) => String(value).trim()))
        .map((item) => ({
          status: item.status || undefined,
          date: item.date || null,
          vaccine_name: item.vaccine_name || undefined,
          vaccination_dose: item.vaccination_dose || undefined,
        })),
      diagnoses: splitTextValues(observation.diagnoses_text),
      metastatic_sites: splitTextValues(observation.metastatic_sites_text),
      comorbidities: splitTextValues(observation.comorbidities_text),
      histopathologies: histopathologies
        .filter((item) => Object.values(item).some((value) => value.trim()))
        .map((item) => ({
          detail: item.detail || undefined,
          site: item.site || undefined,
          histology_type: item.histology_type || undefined,
          observed_on: item.observed_on || null,
        })),
      molecular_pathologies: molecularPathologies
        .filter((item) => Object.values(item).some((value) => value.trim()))
        .map((item) => ({
          specimen: item.specimen || undefined,
          method: item.method || undefined,
          gene: item.gene || undefined,
          exon: item.exon || undefined,
          status: item.status || undefined,
          observed_on: item.observed_on || null,
        })),
      cancer_markers: markers
        .filter((item) => item.name.trim() && item.value.trim() && item.observed_on)
        .map((item) => ({
          name: item.name.trim(),
          value: item.value.trim(),
          unit: item.unit.trim(),
          observed_on: item.observed_on,
        })),
      clinical_staging: {
        t: observation.clinical_t || undefined,
        n: observation.clinical_n || undefined,
        m: observation.clinical_m || undefined,
        result: observation.clinical_result || undefined,
        staged_on: observation.clinical_staged_on || null,
      },
      pathological_staging: {
        t: observation.pathological_t || undefined,
        n: observation.pathological_n || undefined,
        m: observation.pathological_m || undefined,
        result: observation.pathological_result || undefined,
        staged_on: observation.pathological_staged_on || null,
      },
      pathological_staging_detail: {
        lvsi: observation.pathological_lvsi || undefined,
        pni: observation.pathological_pni || undefined,
        margin: observation.pathological_margin || undefined,
        ki67: observation.pathological_ki67 || undefined,
        staged_on: observation.pathological_detail_staged_on || null,
      },
      ihc_panels: ihcPanels
        .filter(
          (panel) =>
            panel.observed_on ||
            panel.details.some((detail) => detail.marker_type.trim() || detail.value.trim()),
        )
        .map((panel) => ({
          observed_on: panel.observed_on || null,
          details: panel.details
            .filter((detail) => detail.marker_type.trim() || detail.value.trim())
            .map((detail) => ({
              marker_type: detail.marker_type || undefined,
              value: detail.value || undefined,
            })),
        })),
      treatment_cycles: treatmentCycles
        .filter((item) => Object.values(item).some((value) => value.trim()))
        .map((item) => ({ ...item })),
      past_treatment_histories: pastTreatments
        .filter((item) => item.detail.trim() || item.date)
        .map((item) => ({
          detail: item.detail || undefined,
          date: item.date || null,
        })),
      radiotherapy_schedules: radiotherapySchedules
        .filter((item) => Object.values(item).some((value) => value.trim()))
        .map((item) => ({
          start_date: item.start_date || null,
          end_date: item.end_date || null,
          intent: item.intent || undefined,
          fraction: item.fraction || undefined,
          fraction_number: item.fraction_number || undefined,
          total_dose: item.total_dose || undefined,
          sites: splitTextValues(item.sites_text),
          modalities: splitTextValues(item.modalities_text),
        })),
      surgeries: surgeries
        .filter((item) => item.surgery_date || item.modality.trim() || item.lateralities_text.trim())
        .map((item) => ({
          surgery_date: item.surgery_date,
          modality: item.modality || undefined,
          lateralities: splitTextValues(item.lateralities_text),
        })),
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!patient.name.trim()) {
      setErrorMessage('Patient name is required.')
      setActiveStep(0)
      return
    }
    setErrorMessage('')
    setSuccessMessage('')
    if (isEditMode) {
      updateMutation.mutate(buildPayload())
      return
    }
    createMutation.mutate(buildPayload())
  }

  const isFirstStep = activeStep === 0
  const isLastStep = activeStep === steps.length - 1
  const isSubmitting = createMutation.isPending || updateMutation.isPending

  if (isEditMode && patientDetailQuery.isLoading) {
    return (
      <section className="panel">
        <p className="eyebrow">Edit Patient Entry</p>
        <h3>Loading record</h3>
      </section>
    )
  }

  if (isEditMode && !patientDetailQuery.data) {
    return (
      <section className="panel">
        <p className="eyebrow">Edit Patient Entry</p>
        <h3>Record unavailable</h3>
        <p className="entry-inline-note">
          The selected patient record could not be loaded for editing.
        </p>
      </section>
    )
  }

  if (isEditMode && patientDetailQuery.data && !patientDetailQuery.data.can_edit) {
    return (
      <section className="panel">
        <p className="eyebrow">Edit Patient Entry</p>
        <h3>Editing not allowed</h3>
        <p className="entry-inline-note">
          This account cannot edit the selected patient record.
        </p>
      </section>
    )
  }

  return (
    <section className="page-grid">
      <Link className="back-link" to="/patients">
        <ArrowLeft size={16} />
        Back to registry
      </Link>

      <section className="hero-panel hero-panel-tight entry-hero-compact">
        <div className="hero-copy">
          <p className="eyebrow">{isEditMode ? 'Edit Patient Entry' : 'New Patient Entry'}</p>
          <h2>{isEditMode ? 'Update patient entry' : 'Create patient entry'}</h2>
          <p className="hero-text">
            Demography, diagnosis, treatment, and follow-up in one clinical workflow.
          </p>
        </div>
        <div className="header-badges">
          <span className="data-pill">Draft / Publish</span>
          <span className="data-pill">Admin / Doctor / User</span>
        </div>
      </section>

      <section className="panel panel-compact">
        <div className="entry-stepper">
          {steps.map((step, index) => (
            <button
              key={step.key}
              type="button"
              className={
                index === activeStep
                  ? 'entry-step entry-step-active'
                  : index < activeStep
                  ? 'entry-step entry-step-complete'
                  : 'entry-step'
              }
              onClick={() => setActiveStep(index)}
            >
              <span>{index + 1}</span>
              <strong>{step.label}</strong>
            </button>
          ))}
        </div>
      </section>

      <form className="entry-layout" onSubmit={handleSubmit}>
        {activeStep === 0 ? (
          <>
            {!isEditMode ? (
              <section className="entry-record-check" aria-live="polite">
                <div className="entry-record-check-copy">
                  <span className="entry-record-check-icon"><Search size={18} /></span>
                  <div>
                    <p className="eyebrow">Existing record check</p>
                    <h3>Find an existing patient</h3>
                  </div>
                </div>
                <div className="entry-record-lookup">
                  <label className="search-label" htmlFor="existing-record-lookup">Patient lookup</label>
                  <div className="search-row">
                    <Search className="search-icon" size={18} />
                    <input
                      id="existing-record-lookup"
                      className="search-input"
                      value={recordLookupTerm}
                      onChange={(event) => setRecordLookupTerm(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter') event.preventDefault()
                      }}
                      placeholder="Paste registration no., mobile no., or patient name"
                    />
                  </div>
                </div>
                {deferredDuplicateLookupTerm.length >= 3 ? (
                  <div className="entry-match-area">
                    {duplicateLookupQuery.isLoading ? <span className="entry-lookup-status">Searching registry...</span> : null}
                    {!duplicateLookupQuery.isLoading && duplicateMatches.length === 0 ? (
                      <span className="entry-lookup-status entry-lookup-clear">No matching record found. You can continue.</span>
                    ) : null}
                    {duplicateMatches.length ? (
                      <div className="entry-match-list">
                        {duplicateMatches.map((match) => (
                          <button
                            key={match.registry_id}
                            type="button"
                            className="entry-match"
                            onClick={() => navigate(`/patients/${match.registry_id}/edit`)}
                          >
                            <span>
                              <strong>{match.name || 'Unnamed patient'}</strong>
                              <small>{match.registration_no || match.legacy_unique_id || match.registry_id}</small>
                            </span>
                            <span className="entry-match-meta">
                              {match.phone || ''}
                              <span>Load entry</span>
                            </span>
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </section>
            ) : null}

            <section className="panel entry-block entry-block-demography">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Patient Demography</p>
                  <h3>Core patient profile</h3>
                </div>
              </div>
              <div className="entry-grid">
                {[
                  ['registry_id', 'Registry ID'],
                  ['legacy_unique_id', 'Legacy Unique ID'],
                  ['registration_no', 'Registration No'],
                  ['name', 'Patient Name *'],
                  ['phone', 'Patient Contact / Mobile No'],
                  ['email', 'Email'],
                  ['nid', 'NID'],
                ].map(([name, label]) => (
                  <label key={name} className="filter-field">
                    <span>{label}</span>
                    <input
                      className="auth-input"
                      value={patient[name as keyof typeof patient]}
                      onChange={(event) =>
                        updateObjectField(setPatient, name as keyof typeof patient, event.target.value)
                      }
                    />
                  </label>
                ))}

                <div className="filter-field entry-span-full">
                  <span>Age / Date of Birth Mode</span>
                  <div className="auth-role-selector">
                    <button
                      type="button"
                      className={ageInputMode === 'dob' ? 'auth-role-option auth-role-option-active' : 'auth-role-option'}
                      onClick={() => setAgeInputMode('dob')}
                    >
                      Known DOB
                    </button>
                    <button
                      type="button"
                      className={ageInputMode === 'age' ? 'auth-role-option auth-role-option-active' : 'auth-role-option'}
                      onClick={() => setAgeInputMode('age')}
                    >
                      Known Age
                    </button>
                  </div>
                </div>

                {ageInputMode === 'dob' ? (
                  <>
                    <label className="filter-field">
                      <span>Date of Birth</span>
                      <DateField
                        value={patient.date_of_birth}
                        onChange={handleDateOfBirthChange}
                      />
                    </label>
                    <label className="filter-field">
                      <span>Age</span>
                      <input
                        className="auth-input"
                        value={patient.age}
                        readOnly
                        placeholder="Auto-calculated from DOB"
                      />
                    </label>
                  </>
                ) : (
                  <>
                    <label className="filter-field">
                      <span>Age</span>
                      <input
                        className="auth-input"
                        type="number"
                        min="0"
                        value={patient.age}
                        onChange={(event) => handleAgeChange(event.target.value)}
                      />
                    </label>
                    <label className="filter-field">
                      <span>Estimated Date of Birth</span>
                      <DateField
                        value={patient.date_of_birth}
                        readOnly
                      />
                    </label>
                  </>
                )}

                <label className="filter-field">
                  <span>Sex</span>
                  <select
                    className="inline-filter-select"
                    value={patient.gender}
                    onChange={(event) => updateObjectField(setPatient, 'gender', event.target.value)}
                  >
                    <option value="">Select sex</option>
                    {(demographics?.genders ?? []).map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="filter-field">
                  <span>Blood Group</span>
                  <select
                    className="inline-filter-select"
                    value={patient.blood_group}
                    onChange={(event) => updateObjectField(setPatient, 'blood_group', event.target.value)}
                  >
                    <option value="">Select blood group</option>
                    {(demographics?.blood_groups ?? []).map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="filter-field">
                  <span>Area</span>
                  <input
                    className="auth-input"
                    value={patient.area}
                    onChange={(event) => updateObjectField(setPatient, 'area', event.target.value)}
                  />
                </label>
                <label className="filter-field">
                  <span>District</span>
                  <select
                    className="inline-filter-select"
                    value={patient.district}
                    onChange={(event) =>
                      setPatient((current) => ({
                        ...current,
                        district: event.target.value,
                        police_station: '',
                      }))
                    }
                  >
                    <option value="">Select district</option>
                    {(demographics?.districts ?? []).map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="filter-field">
                  <span>Thana / Police Station</span>
                  <select
                    className="inline-filter-select"
                    value={patient.police_station}
                    onChange={(event) => updateObjectField(setPatient, 'police_station', event.target.value)}
                    disabled={!patient.district}
                  >
                    <option value="">{patient.district ? 'Select thana' : 'Select district first'}</option>
                    {(demographics?.police_stations ?? []).map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="filter-field">
                  <span>Socio-Economic Status</span>
                  <select
                    className="inline-filter-select"
                    value={patient.socio_economic_status}
                    onChange={(event) =>
                      updateObjectField(setPatient, 'socio_economic_status', event.target.value)
                    }
                  >
                    <option value="">Select socio-economic status</option>
                    {(demographics?.socio_economic_statuses ?? []).map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="filter-field">
                  <span>Passport</span>
                  <input
                    className="auth-input"
                    value={patient.passport}
                    onChange={(event) => updateObjectField(setPatient, 'passport', event.target.value)}
                  />
                </label>
                <label className="filter-field">
                  <span>Type</span>
                  <select
                    className="inline-filter-select"
                    value={patient.patient_type}
                    onChange={(event) => updateObjectField(setPatient, 'patient_type', event.target.value)}
                  >
                    <option value="">Select type</option>
                    {(demographics?.patient_types ?? []).map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </section>

            <section className="panel panel-compact entry-block entry-block-history">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">History</p>
                  <h3>Personal and family background</h3>
                </div>
              </div>
              <div className="entry-grid">
                <label className="filter-field">
                  <span>Marital Status</span>
                  <select
                    className="inline-filter-select"
                    value={history.marital_status}
                    onChange={(event) => updateObjectField(setHistory, 'marital_status', event.target.value)}
                  >
                    <option value="">Select marital status</option>
                    {(demographics?.marital_statuses ?? []).map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="filter-field">
                  <span>Dietary Habit</span>
                  <input
                    className="auth-input"
                    value={history.dietary_habit}
                    onChange={(event) => updateObjectField(setHistory, 'dietary_habit', event.target.value)}
                  />
                </label>
                <label className="filter-field">
                  <span>Height (cm)</span>
                  <input
                    className="auth-input"
                    type="number"
                    value={history.height_cm}
                    onChange={(event) => updateObjectField(setHistory, 'height_cm', event.target.value)}
                  />
                </label>
                <label className="filter-field">
                  <span>Weight (kg)</span>
                  <input
                    className="auth-input"
                    type="number"
                    value={history.weight_kg}
                    onChange={(event) => updateObjectField(setHistory, 'weight_kg', event.target.value)}
                  />
                </label>
                <label className="filter-field">
                  <span>BMI</span>
                  <input
                    className="auth-input"
                    type="number"
                    value={history.bmi}
                    onChange={(event) => updateObjectField(setHistory, 'bmi', event.target.value)}
                  />
                </label>
                <label className="filter-field">
                  <span>H/O Alcoholism</span>
                  <select
                    className="inline-filter-select"
                    value={history.alcohol_history}
                    onChange={(event) => updateObjectField(setHistory, 'alcohol_history', event.target.value)}
                  >
                    <option value="">Select alcoholism history</option>
                    {(demographics?.alcohol_history_options ?? []).map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="filter-field">
                  <span>Any H/O RT to Chest</span>
                  <input
                    className="auth-input"
                    value={history.radiotherapy_to_chest}
                    onChange={(event) =>
                      updateObjectField(setHistory, 'radiotherapy_to_chest', event.target.value)
                    }
                  />
                </label>
                <label className="filter-field">
                  <span>Personal/Family H/O Cancer</span>
                  <input
                    className="auth-input"
                    value={history.family_cancer_history}
                    onChange={(event) =>
                      updateObjectField(setHistory, 'family_cancer_history', event.target.value)
                    }
                  />
                </label>
                <label className="filter-field">
                  <span>Any Known Mutation</span>
                  <input
                    className="auth-input"
                    value={history.known_mutation}
                    onChange={(event) => updateObjectField(setHistory, 'known_mutation', event.target.value)}
                  />
                </label>
                <label className="filter-field">
                  <span>Date of 1st Diagnosis</span>
                  <DateField
                    value={history.first_diagnosis_date}
                    onChange={(value) => updateObjectField(setHistory, 'first_diagnosis_date', value)}
                  />
                </label>
                <label className="filter-field">
                  <span>Age at Diagnosis</span>
                  <input
                    className="auth-input"
                    value={ageAtDiagnosis ?? ''}
                    readOnly
                    placeholder="Calculated from Date of 1st Diagnosis"
                  />
                </label>
                <p className="entry-inline-note entry-span-full">
                  Age at diagnosis now uses only `Date of 1st Diagnosis`. If only age is known, the estimated DOB
                  is still anchored to that same diagnosis date.
                </p>
              </div>
            </section>

            <section className="panel panel-compact entry-block entry-block-exposure">
              <div className="panel-heading">
                <h3>Smoking History</h3>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setSmokingHistories((current) => [...current, emptySmoking()])}
                >
                  <Plus size={16} />
                  Add smoking cycle
                </button>
              </div>
              <div className="repeatable-grid">
                {smokingHistories.map((item, index) => (
                  <div key={`smoking-${index}`} className="repeatable-card">
                    <div className="repeatable-head">
                      <strong>Smoking Record {index + 1}</strong>
                      {smokingHistories.length > 1 ? (
                        <button
                          type="button"
                          className="icon-button"
                          onClick={() => removeArrayItem(setSmokingHistories, index)}
                        >
                          <Trash2 size={16} />
                        </button>
                      ) : null}
                    </div>
                      <div className="entry-grid">
                      <label className="filter-field">
                        <span>Status</span>
                        <select
                          className="inline-filter-select"
                          value={item.status}
                          onChange={(event) =>
                            updateArrayItem(setSmokingHistories, index, 'status', event.target.value)
                          }
                        >
                          <option value="">Select smoking status</option>
                          {(demographics?.smoking_statuses ?? []).map((value) => (
                            <option key={value} value={value}>
                              {value}
                            </option>
                          ))}
                        </select>
                      </label>
                      {[
                        ['cigarettes_per_day', 'No. of Cigarettes / Day', 'number'],
                        ['duration_years', 'Smoking For (Years)', 'number'],
                        ['pack_years', 'Pack-Year', 'number'],
                        ['quit_period_years', 'Quit Smoking For (Years)', 'number'],
                      ].map(([name, label, type]) => (
                        <label key={name} className="filter-field">
                          <span>{label}</span>
                          <input
                            className="auth-input"
                            type={type || 'text'}
                            value={item[name as keyof SmokingForm]}
                            onChange={(event) =>
                              updateArrayItem(
                                setSmokingHistories,
                                index,
                                name as keyof SmokingForm,
                                event.target.value,
                              )
                            }
                          />
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="insight-grid insight-grid-dense">
              <article className="panel panel-compact">
                <div className="panel-heading">
                  <h3>TB History</h3>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => setTbHistories((current) => [...current, emptyTb()])}
                  >
                    <Plus size={16} />
                    Add TB
                  </button>
                </div>
                <div className="repeatable-grid">
                  {tbHistories.map((item, index) => (
                    <div key={`tb-${index}`} className="repeatable-card">
                      <div className="repeatable-head">
                        <strong>TB Record {index + 1}</strong>
                        {tbHistories.length > 1 ? (
                          <button
                            type="button"
                            className="icon-button"
                            onClick={() => removeArrayItem(setTbHistories, index)}
                          >
                            <Trash2 size={16} />
                          </button>
                        ) : null}
                      </div>
                      <div className="entry-grid">
                        <label className="filter-field">
                          <span>Status</span>
                          <select
                            className="inline-filter-select"
                            value={item.status}
                            onChange={(event) =>
                              updateArrayItem(setTbHistories, index, 'status', event.target.value)
                            }
                          >
                            <option value="">Select TB status</option>
                            {(demographics?.tb_statuses ?? []).map((value) => (
                              <option key={value} value={value}>
                                {value}
                              </option>
                            ))}
                          </select>
                        </label>
                        {[
                          ['date', 'TB Treatment Start Date', 'date'],
                          ['treatment', 'Treatment'],
                        ].map(([name, label, type]) => (
                          <label key={name} className="filter-field">
                            <span>{label}</span>
                            {type === 'date' ? (
                              <DateField
                                value={item[name as keyof TbForm]}
                                onChange={(value) => updateArrayItem(setTbHistories, index, name as keyof TbForm, value)}
                              />
                            ) : (
                              <input
                                className="auth-input"
                                value={item[name as keyof TbForm]}
                                onChange={(event) =>
                                  updateArrayItem(setTbHistories, index, name as keyof TbForm, event.target.value)
                                }
                              />
                            )}
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </article>

              <article className="panel panel-compact">
                <div className="panel-heading">
                  <h3>Covid History</h3>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => setCovidHistories((current) => [...current, emptyCovid()])}
                  >
                    <Plus size={16} />
                    Add Covid
                  </button>
                </div>
                <div className="repeatable-grid">
                  {covidHistories.map((item, index) => (
                    <div key={`covid-${index}`} className="repeatable-card">
                      <div className="repeatable-head">
                        <strong>Covid Record {index + 1}</strong>
                        {covidHistories.length > 1 ? (
                          <button
                            type="button"
                            className="icon-button"
                            onClick={() => removeArrayItem(setCovidHistories, index)}
                          >
                            <Trash2 size={16} />
                          </button>
                        ) : null}
                      </div>
                      <div className="entry-grid">
                        <label className="filter-field">
                          <span>Status</span>
                          <select
                            className="inline-filter-select"
                            value={item.status}
                            onChange={(event) =>
                              updateArrayItem(setCovidHistories, index, 'status', event.target.value)
                            }
                          >
                            <option value="">Select Covid status</option>
                            {(demographics?.covid_statuses ?? []).map((value) => (
                              <option key={value} value={value}>
                                {value}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="filter-field">
                          <span>Date</span>
                          <DateField
                            value={item.date}
                            onChange={(value) => updateArrayItem(setCovidHistories, index, 'date', value)}
                          />
                        </label>
                        <label className="filter-field">
                          <span>Vaccine Name</span>
                          <select
                            className="inline-filter-select"
                            value={item.vaccine_name}
                            onChange={(event) =>
                              updateArrayItem(setCovidHistories, index, 'vaccine_name', event.target.value)
                            }
                          >
                            <option value="">Select vaccine</option>
                            {(demographics?.covid_vaccine_names ?? []).map((value) => (
                              <option key={value} value={value}>
                                {value}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="filter-field">
                          <span>Vaccination Dose</span>
                          <select
                            className="inline-filter-select"
                            value={item.vaccination_dose}
                            onChange={(event) =>
                              updateArrayItem(setCovidHistories, index, 'vaccination_dose', event.target.value)
                            }
                          >
                            <option value="">Select dose</option>
                            {(demographics?.covid_vaccination_doses ?? []).map((value) => (
                              <option key={value} value={value}>
                                {value}
                              </option>
                            ))}
                          </select>
                        </label>
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            </section>
          </>
        ) : null}

        {activeStep === 1 ? (
          <>
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Diagnosis</p>
                  <h3>Observation and diagnosis framing</h3>
                </div>
              </div>
              <div className="entry-grid">
                <label className="filter-field">
                  <span>Observation Date / Time</span>
                  <DateTimeField
                    value={observation.observed_at}
                    onChange={(value) => updateObjectField(setObservation, 'observed_at', value)}
                  />
                </label>
                <label className="filter-field">
                  <span>Consultant / Primary Physician</span>
                  <input
                    className="auth-input"
                    value={observation.consulting_doctor_name}
                    onChange={(event) =>
                      updateObjectField(setObservation, 'consulting_doctor_name', event.target.value)
                    }
                  />
                </label>
                <label className="filter-field">
                  <span>Center</span>
                  <input
                    className="auth-input"
                    value={observation.center_name}
                    onChange={(event) => updateObjectField(setObservation, 'center_name', event.target.value)}
                  />
                </label>
                <label className="filter-field">
                  <span>Cancer Type</span>
                  <input
                    className="auth-input"
                    value={observation.cancer_type}
                    onChange={(event) => updateObjectField(setObservation, 'cancer_type', event.target.value)}
                  />
                </label>
                <label className="filter-field">
                  <span>Diagnosis Disease Group</span>
                  <select
                    className="inline-filter-select"
                    value={observation.diagnosis_disease_group}
                    onChange={(event) =>
                      setObservation((current) => ({
                        ...current,
                        diagnosis_disease_group: event.target.value,
                        diagnosis_subgroup: '',
                      }))
                    }
                  >
                    <option value="">Select disease group</option>
                    {(demographics?.diagnosis_disease_groups ?? []).map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="filter-field">
                  <span>Diagnosis Subgroup</span>
                  <select
                    className="inline-filter-select"
                    value={observation.diagnosis_subgroup}
                    onChange={(event) => updateObjectField(setObservation, 'diagnosis_subgroup', event.target.value)}
                    disabled={!observation.diagnosis_disease_group}
                  >
                    <option value="">
                      {observation.diagnosis_disease_group ? 'Select subgroup' : 'Select disease group first'}
                    </option>
                    {(demographics?.diagnosis_disease_subgroups ?? []).map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="filter-field">
                  <span>Diagnosis Primary Site</span>
                  <select
                    className="inline-filter-select"
                    value={observation.diagnosis_primary_site}
                    onChange={(event) =>
                      updateObjectField(setObservation, 'diagnosis_primary_site', event.target.value)
                    }
                  >
                    <option value="">Select primary site</option>
                    {(demographics?.diagnosis_primary_sites ?? []).map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="filter-field">
                  <span>Diagnosis Laterality</span>
                  <select
                    className="inline-filter-select"
                    value={observation.diagnosis_laterality}
                    onChange={(event) =>
                      updateObjectField(setObservation, 'diagnosis_laterality', event.target.value)
                    }
                  >
                    <option value="">Select laterality</option>
                    {(demographics?.diagnosis_lateralities ?? []).map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="filter-field">
                  <span>Grade</span>
                  <input
                    className="auth-input"
                    value={observation.grade}
                    onChange={(event) => updateObjectField(setObservation, 'grade', event.target.value)}
                  />
                </label>
                <label className="filter-field entry-span-full">
                  <span>Diagnosis in Details</span>
                  <textarea
                    className="entry-textarea"
                    value={observation.diagnoses_text}
                    onChange={(event) =>
                      updateObjectField(setObservation, 'diagnoses_text', event.target.value)
                    }
                    placeholder="Use new lines or commas for multiple diagnosis details"
                  />
                </label>
                <label className="filter-field">
                  <span>Metastatic Sites</span>
                  <textarea
                    className="entry-textarea"
                    value={observation.metastatic_sites_text}
                    onChange={(event) =>
                      updateObjectField(setObservation, 'metastatic_sites_text', event.target.value)
                    }
                    placeholder={(demographics?.diagnosis_metastatic_sites ?? []).join(', ')}
                  />
                </label>
                <label className="filter-field">
                  <span>Comorbidities</span>
                  <textarea
                    className="entry-textarea"
                    value={observation.comorbidities_text}
                    onChange={(event) =>
                      updateObjectField(setObservation, 'comorbidities_text', event.target.value)
                    }
                  />
                </label>
                <label className="filter-field entry-span-full">
                  <span>Laterality Notes</span>
                  <textarea
                    className="entry-textarea"
                    value={observation.laterality_notes}
                    onChange={(event) =>
                      updateObjectField(setObservation, 'laterality_notes', event.target.value)
                    }
                  />
                </label>
              </div>
            </section>

            <section className="insight-grid insight-grid-dense">
              <article className="panel panel-compact">
                <div className="panel-heading">
                  <h3>Histopathology</h3>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() =>
                      setHistopathologies((current) => [...current, emptyHistopathology()])
                    }
                  >
                    <Plus size={16} />
                    Add histopathology
                  </button>
                </div>
                <div className="repeatable-grid">
                  {histopathologies.map((item, index) => (
                    <div key={`histo-${index}`} className="repeatable-card">
                      <div className="repeatable-head">
                        <strong>Histopathology {index + 1}</strong>
                        {histopathologies.length > 1 ? (
                          <button
                            type="button"
                            className="icon-button"
                            onClick={() => removeArrayItem(setHistopathologies, index)}
                          >
                            <Trash2 size={16} />
                          </button>
                        ) : null}
                      </div>
                      <div className="entry-grid">
                        {[
                          ['detail', 'Detail'],
                          ['site', 'Site'],
                          ['histology_type', 'Type'],
                          ['observed_on', 'Date', 'date'],
                        ].map(([name, label, type]) => (
                          <label key={name} className="filter-field">
                            <span>{label}</span>
                            {type === 'date' ? (
                              <DateField
                                value={item[name as keyof HistopathologyForm]}
                                onChange={(value) => updateArrayItem(setHistopathologies, index, name as keyof HistopathologyForm, value)}
                              />
                            ) : (
                              <input
                                className="auth-input"
                                value={item[name as keyof HistopathologyForm]}
                                onChange={(event) =>
                                  updateArrayItem(setHistopathologies, index, name as keyof HistopathologyForm, event.target.value)
                                }
                              />
                            )}
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </article>

              <article className="panel panel-compact">
                <div className="panel-heading">
                  <h3>Molecular Pathology</h3>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() =>
                      setMolecularPathologies((current) => [...current, emptyMolecular()])
                    }
                  >
                    <Plus size={16} />
                    Add molecular
                  </button>
                </div>
                <div className="repeatable-grid">
                  {molecularPathologies.map((item, index) => (
                    <div key={`molecular-${index}`} className="repeatable-card">
                      <div className="repeatable-head">
                        <strong>Molecular Record {index + 1}</strong>
                        {molecularPathologies.length > 1 ? (
                          <button
                            type="button"
                            className="icon-button"
                            onClick={() => removeArrayItem(setMolecularPathologies, index)}
                          >
                            <Trash2 size={16} />
                          </button>
                        ) : null}
                      </div>
                      <div className="entry-grid">
                        {[
                          ['specimen', 'Specimen'],
                          ['method', 'Method'],
                          ['gene', 'Gene'],
                          ['exon', 'Exon'],
                          ['status', 'Status'],
                          ['observed_on', 'Date', 'date'],
                        ].map(([name, label, type]) => (
                          <label key={name} className="filter-field">
                            <span>{label}</span>
                            {type === 'date' ? (
                              <DateField
                                value={item[name as keyof MolecularForm]}
                                onChange={(value) => updateArrayItem(setMolecularPathologies, index, name as keyof MolecularForm, value)}
                              />
                            ) : (
                              <input
                                className="auth-input"
                                value={item[name as keyof MolecularForm]}
                                onChange={(event) =>
                                  updateArrayItem(setMolecularPathologies, index, name as keyof MolecularForm, event.target.value)
                                }
                              />
                            )}
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            </section>

            <section className="insight-grid insight-grid-dense">
              <article className="panel panel-compact">
                <div className="panel-heading">
                  <h3>Staging</h3>
                </div>
                <div className="entry-grid">
                  {[
                    ['clinical_t', 'Clinical T'],
                    ['clinical_n', 'Clinical N'],
                    ['clinical_m', 'Clinical M'],
                    ['clinical_result', 'Staging-Clinical'],
                    ['clinical_staged_on', 'Clinical Date', 'date'],
                    ['pathological_t', 'Pathological T'],
                    ['pathological_n', 'Pathological N'],
                    ['pathological_m', 'Pathological M'],
                    ['pathological_result', 'Staging-Pathological'],
                    ['pathological_staged_on', 'Pathological Date', 'date'],
                  ].map(([name, label, type]) => (
                    <label key={name} className="filter-field">
                      <span>{label}</span>
                      {type === 'date' ? (
                        <DateField
                          value={observation[name as keyof typeof observation]}
                          onChange={(value) => updateObjectField(setObservation, name as keyof typeof observation, value)}
                        />
                      ) : (
                        <input
                          className="auth-input"
                          value={observation[name as keyof typeof observation]}
                          onChange={(event) => updateObjectField(setObservation, name as keyof typeof observation, event.target.value)}
                        />
                      )}
                    </label>
                  ))}
                </div>
                <div className="entry-grid">
                  {[
                    ['pathological_lvsi', 'LVSI'],
                    ['pathological_pni', 'PNI'],
                    ['pathological_margin', 'Margin'],
                    ['pathological_ki67', 'Ki67'],
                    ['pathological_detail_staged_on', 'Pathological Detail Date', 'date'],
                  ].map(([name, label, type]) => (
                    <label key={name} className="filter-field">
                      <span>{label}</span>
                      {type === 'date' ? (
                        <DateField
                          value={observation[name as keyof typeof observation]}
                          onChange={(value) => updateObjectField(setObservation, name as keyof typeof observation, value)}
                        />
                      ) : (
                        <input
                          className="auth-input"
                          value={observation[name as keyof typeof observation]}
                          onChange={(event) => updateObjectField(setObservation, name as keyof typeof observation, event.target.value)}
                        />
                      )}
                    </label>
                  ))}
                </div>
              </article>

              <article className="panel panel-compact">
                <div className="panel-heading">
                  <h3>IHC Panels</h3>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => setIhcPanels((current) => [...current, emptyIhcPanel()])}
                  >
                    <Plus size={16} />
                    Add IHC cycle
                  </button>
                </div>
                <div className="repeatable-grid">
                  {ihcPanels.map((panel, panelIndex) => (
                    <div key={`ihc-${panelIndex}`} className="repeatable-card">
                      <div className="repeatable-head">
                        <strong>IHC Panel {panelIndex + 1}</strong>
                        {ihcPanels.length > 1 ? (
                          <button
                            type="button"
                            className="icon-button"
                            onClick={() => removeArrayItem(setIhcPanels, panelIndex)}
                          >
                            <Trash2 size={16} />
                          </button>
                        ) : null}
                      </div>
                      <div className="entry-grid">
                        <label className="filter-field">
                          <span>Observed On</span>
                          <DateField
                            value={panel.observed_on}
                            onChange={(value) =>
                              updateArrayItem(setIhcPanels, panelIndex, 'observed_on', value)
                            }
                          />
                        </label>
                      </div>
                      <div className="repeatable-grid">
                        {panel.details.map((detail, detailIndex) => (
                          <div key={`ihc-detail-${panelIndex}-${detailIndex}`} className="repeatable-card repeatable-card-soft">
                            <div className="repeatable-head">
                              <strong>IHC Detail {detailIndex + 1}</strong>
                              {panel.details.length > 1 ? (
                                <button
                                  type="button"
                                  className="icon-button"
                                  onClick={() =>
                                    setIhcPanels((current) =>
                                      current.map((item, itemIndex) =>
                                        itemIndex === panelIndex
                                          ? {
                                              ...item,
                                              details: item.details.filter(
                                                (_, currentIndex) => currentIndex !== detailIndex,
                                              ),
                                            }
                                          : item,
                                      ),
                                    )
                                  }
                                >
                                  <Trash2 size={16} />
                                </button>
                              ) : null}
                            </div>
                            <div className="entry-grid">
                              <label className="filter-field">
                                <span>Marker Type</span>
                                <input
                                  className="auth-input"
                                  value={detail.marker_type}
                                  onChange={(event) =>
                                    setIhcPanels((current) =>
                                      current.map((item, itemIndex) =>
                                        itemIndex === panelIndex
                                          ? {
                                              ...item,
                                              details: item.details.map((detailItem, currentIndex) =>
                                                currentIndex === detailIndex
                                                  ? { ...detailItem, marker_type: event.target.value }
                                                  : detailItem,
                                              ),
                                            }
                                          : item,
                                      ),
                                    )
                                  }
                                />
                              </label>
                              <label className="filter-field">
                                <span>Value</span>
                                <input
                                  className="auth-input"
                                  value={detail.value}
                                  onChange={(event) =>
                                    setIhcPanels((current) =>
                                      current.map((item, itemIndex) =>
                                        itemIndex === panelIndex
                                          ? {
                                              ...item,
                                              details: item.details.map((detailItem, currentIndex) =>
                                                currentIndex === detailIndex
                                                  ? { ...detailItem, value: event.target.value }
                                                  : detailItem,
                                              ),
                                            }
                                          : item,
                                      ),
                                    )
                                  }
                                />
                              </label>
                            </div>
                          </div>
                        ))}
                        <button
                          type="button"
                          className="secondary-button"
                          onClick={() =>
                            setIhcPanels((current) =>
                              current.map((item, itemIndex) =>
                                itemIndex === panelIndex
                                  ? { ...item, details: [...item.details, emptyIhcDetail()] }
                                  : item,
                              ),
                            )
                          }
                        >
                          <Plus size={16} />
                          Add IHC Detail
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            </section>

            <section className="panel panel-compact">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Cancer Marker</p>
                  <h3>Marker values</h3>
                </div>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setMarkers((current) => [...current, emptyMarker()])}
                >
                  <Plus size={16} />
                  Add marker
                </button>
              </div>
              <div className="repeatable-grid">
                {markers.map((marker, index) => (
                  <div key={`marker-${index}`} className="repeatable-card">
                    <div className="repeatable-head">
                      <strong>Marker {index + 1}</strong>
                      {markers.length > 1 ? (
                        <button
                          type="button"
                          className="icon-button"
                          onClick={() => removeArrayItem(setMarkers, index)}
                        >
                          <Trash2 size={16} />
                        </button>
                      ) : null}
                    </div>
                    <div className="entry-grid">
                      {[
                        ['name', 'Name'],
                        ['unit', 'Unit'],
                        ['value', 'Value'],
                        ['observed_on', 'Date', 'date'],
                      ].map(([name, label, type]) => (
                        <label key={name} className="filter-field">
                          <span>{label}</span>
                          {type === 'date' ? (
                            <DateField
                              value={marker[name as keyof MarkerForm]}
                              onChange={(value) => updateArrayItem(setMarkers, index, name as keyof MarkerForm, value)}
                            />
                          ) : (
                            <input
                              className="auth-input"
                              value={marker[name as keyof MarkerForm]}
                              onChange={(event) => updateArrayItem(setMarkers, index, name as keyof MarkerForm, event.target.value)}
                            />
                          )}
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </>
        ) : null}

        {activeStep === 2 ? (
          <>
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Treatment</p>
                  <h3>Past treatment, cycles, radiotherapy, surgery</h3>
                </div>
              </div>

              <div className="repeatable-stack">
                <div className="panel-heading">
                  <h3>Past Treatment History</h3>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => setPastTreatments((current) => [...current, emptyPastTreatment()])}
                  >
                    <Plus size={16} />
                    Add past treatment
                  </button>
                </div>
                {pastTreatments.map((item, index) => (
                  <div key={`past-treatment-${index}`} className="repeatable-card">
                    <div className="repeatable-head">
                      <strong>Past Treatment {index + 1}</strong>
                      {pastTreatments.length > 1 ? (
                        <button
                          type="button"
                          className="icon-button"
                          onClick={() => removeArrayItem(setPastTreatments, index)}
                        >
                          <Trash2 size={16} />
                        </button>
                      ) : null}
                    </div>
                    <div className="entry-grid">
                      <label className="filter-field entry-span-full">
                        <span>Detail</span>
                        <textarea
                          className="entry-textarea"
                          value={item.detail}
                          onChange={(event) =>
                            updateArrayItem(setPastTreatments, index, 'detail', event.target.value)
                          }
                        />
                      </label>
                      <label className="filter-field">
                        <span>Date</span>
                        <DateField
                          value={item.date}
                          onChange={(value) => updateArrayItem(setPastTreatments, index, 'date', value)}
                        />
                      </label>
                    </div>
                  </div>
                ))}
              </div>

              <div className="repeatable-stack">
                <div className="panel-heading">
                  <h3>Treatment Cycles</h3>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => setTreatmentCycles((current) => [...current, emptyTreatmentCycle()])}
                  >
                    <Plus size={16} />
                    Add cycle
                  </button>
                </div>
                {treatmentCycles.map((cycle, index) => (
                  <div key={`cycle-${index}`} className="repeatable-card">
                    <div className="repeatable-head">
                      <strong>Cycle {index + 1}</strong>
                      {treatmentCycles.length > 1 ? (
                        <button
                          type="button"
                          className="icon-button"
                          onClick={() => removeArrayItem(setTreatmentCycles, index)}
                        >
                          <Trash2 size={16} />
                        </button>
                      ) : null}
                    </div>
                    <div className="entry-grid">
                      {[
                        ['current_chemo_protocol', 'Current Chemo Protocol'],
                        ['chemo_cycle_no', 'Chemo Cycle No'],
                        ['chemo_detail', 'Chemo Detail'],
                        ['chemo_starting_date', 'Chemo Start', 'date'],
                        ['chemo_end_date', 'Chemo End', 'date'],
                        ['line_of_treatment', 'Line of Treatment'],
                        ['disease_progression_status', 'Disease Progression Status'],
                        ['disease_progression_status_date', 'Progression Status Date', 'date'],
                        ['survival_status', 'Survival Status'],
                        ['survival_status_date', 'Survival Status Date', 'date'],
                      ].map(([name, label, type]) => (
                        <label key={name} className="filter-field">
                          <span>{label}</span>
                          {type === 'date' ? (
                            <DateField
                              value={cycle[name as keyof TreatmentCycleForm]}
                              onChange={(value) => updateArrayItem(setTreatmentCycles, index, name as keyof TreatmentCycleForm, value)}
                            />
                          ) : (
                            <input
                              className="auth-input"
                              value={cycle[name as keyof TreatmentCycleForm]}
                              onChange={(event) =>
                                updateArrayItem(setTreatmentCycles, index, name as keyof TreatmentCycleForm, event.target.value)
                              }
                            />
                          )}
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="insight-grid insight-grid-dense">
              <article className="panel panel-compact">
                <div className="panel-heading">
                  <h3>Radiotherapy Schedules</h3>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() =>
                      setRadiotherapySchedules((current) => [...current, emptyRadiotherapy()])
                    }
                  >
                    <Plus size={16} />
                    Add radiotherapy
                  </button>
                </div>
                <div className="repeatable-grid">
                  {radiotherapySchedules.map((schedule, index) => (
                    <div key={`radiotherapy-${index}`} className="repeatable-card">
                      <div className="repeatable-head">
                        <strong>Radiotherapy {index + 1}</strong>
                        {radiotherapySchedules.length > 1 ? (
                          <button
                            type="button"
                            className="icon-button"
                            onClick={() => removeArrayItem(setRadiotherapySchedules, index)}
                          >
                            <Trash2 size={16} />
                          </button>
                        ) : null}
                      </div>
                      <div className="entry-grid">
                        {[
                          ['start_date', 'Start Date', 'date'],
                          ['end_date', 'End Date', 'date'],
                          ['intent', 'Intent'],
                          ['fraction', 'Fraction Dose'],
                          ['fraction_number', 'Fraction Number / Dose'],
                          ['total_dose', 'Total Dose in cGy'],
                        ].map(([name, label, type]) => (
                          <label key={name} className="filter-field">
                            <span>{label}</span>
                            {type === 'date' ? (
                              <DateField
                                value={schedule[name as keyof RadiotherapyForm]}
                                onChange={(value) => updateArrayItem(setRadiotherapySchedules, index, name as keyof RadiotherapyForm, value)}
                              />
                            ) : (
                              <input
                                className="auth-input"
                                value={schedule[name as keyof RadiotherapyForm]}
                                onChange={(event) =>
                                  updateArrayItem(setRadiotherapySchedules, index, name as keyof RadiotherapyForm, event.target.value)
                                }
                              />
                            )}
                          </label>
                        ))}
                        <label className="filter-field">
                          <span>Radiotherapy Sites</span>
                          <textarea
                            className="entry-textarea"
                            value={schedule.sites_text}
                            onChange={(event) =>
                              updateArrayItem(setRadiotherapySchedules, index, 'sites_text', event.target.value)
                            }
                          />
                        </label>
                        <label className="filter-field">
                          <span>Radiotherapy Modalities</span>
                          <textarea
                            className="entry-textarea"
                            value={schedule.modalities_text}
                            onChange={(event) =>
                              updateArrayItem(
                                setRadiotherapySchedules,
                                index,
                                'modalities_text',
                                event.target.value,
                              )
                            }
                          />
                        </label>
                      </div>
                    </div>
                  ))}
                </div>
              </article>

              <article className="panel panel-compact">
                <div className="panel-heading">
                  <h3>Surgeries</h3>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => setSurgeries((current) => [...current, emptySurgery()])}
                  >
                    <Plus size={16} />
                    Add surgery
                  </button>
                </div>
                <div className="repeatable-grid">
                  {surgeries.map((item, index) => (
                    <div key={`surgery-${index}`} className="repeatable-card">
                      <div className="repeatable-head">
                        <strong>Surgery {index + 1}</strong>
                        {surgeries.length > 1 ? (
                          <button
                            type="button"
                            className="icon-button"
                            onClick={() => removeArrayItem(setSurgeries, index)}
                          >
                            <Trash2 size={16} />
                          </button>
                        ) : null}
                      </div>
                      <div className="entry-grid">
                        <label className="filter-field">
                          <span>Surgery Date</span>
                          <DateField
                            value={item.surgery_date}
                            onChange={(value) =>
                              updateArrayItem(setSurgeries, index, 'surgery_date', value)
                            }
                          />
                        </label>
                        <label className="filter-field">
                          <span>Modality</span>
                          <input
                            className="auth-input"
                            value={item.modality}
                            onChange={(event) =>
                              updateArrayItem(setSurgeries, index, 'modality', event.target.value)
                            }
                          />
                        </label>
                        <label className="filter-field">
                          <span>Surgical Lateralities</span>
                          <textarea
                            className="entry-textarea"
                            value={item.lateralities_text}
                            onChange={(event) =>
                              updateArrayItem(setSurgeries, index, 'lateralities_text', event.target.value)
                            }
                          />
                        </label>
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            </section>

            <section className="panel panel-compact">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Save Mode</p>
                  <h3>Draft or publish</h3>
                </div>
              </div>
              <div className="auth-role-selector">
                <button
                  type="button"
                  className={
                    saveMode === 'draft'
                      ? 'auth-role-option auth-role-option-active'
                      : 'auth-role-option'
                  }
                  onClick={() => setSaveMode('draft')}
                >
                  Save as draft
                </button>
                <button
                  type="button"
                  className={
                    saveMode === 'published'
                      ? 'auth-role-option auth-role-option-active'
                      : 'auth-role-option'
                  }
                  onClick={() => setSaveMode('published')}
                >
                  Publish
                </button>
              </div>
              {errorMessage ? <p className="auth-error">{errorMessage}</p> : null}
              {successMessage ? <p className="entry-success">{successMessage}</p> : null}
            </section>
          </>
        ) : null}

        <section className="panel panel-compact">
          <div className="entry-nav">
            <button
              type="button"
              className="secondary-button"
              disabled={isFirstStep}
              onClick={() => setActiveStep((current) => Math.max(0, current - 1))}
            >
              <ChevronLeft size={16} />
              Back
            </button>
            <div className="entry-nav-actions">
              {!isLastStep ? (
                <button
                  type="button"
                  className="primary-button"
                  onClick={() => setActiveStep((current) => Math.min(steps.length - 1, current + 1))}
                >
                  Next
                  <ChevronRight size={16} />
                </button>
              ) : (
                <button type="submit" className="primary-button" disabled={isSubmitting}>
                  {isSubmitting
                    ? isEditMode
                      ? 'Updating entry...'
                      : 'Saving entry...'
                    : isEditMode
                    ? 'Update patient entry'
                    : 'Create patient entry'}
                </button>
              )}
            </div>
          </div>
        </section>
      </form>
    </section>
  )
}
