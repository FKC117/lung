// LEGACY_UI: expects the former nested Entries detail response.
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Plus } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { type EntriesClinicalRecord, fetchEntriesPatientClinicalDetail } from '../api'

const hiddenFields = new Set([
  'id', 'display', 'labels', 'legacy_id', 'observation', 'patient', 'patient_history', 'treatment_cycle', 'panel',
  'source_created_at', 'source_updated_at', 'source_deleted_at', 'source_date', 'source_staged_on',
])

function label(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, letter => letter.toUpperCase())
}

function text(value: unknown) {
  if (value === null || value === undefined || value === '') return 'Not recorded'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (Array.isArray(value)) return value.length ? value.join(', ') : 'Not recorded'
  return String(value).replace('T00:00:00+06:00', '')
}

function RecordFields({ record }: { record: EntriesClinicalRecord }) {
  const labels = record.labels ?? {}
  const fields = Object.entries(record).filter(([key, value]) => !hiddenFields.has(key) && value !== null && value !== '' && value !== undefined)
  if (!fields.length) return <p className="entry-inline-note">No additional data recorded.</p>
  return <div className="detail-grid">{fields.map(([key, value]) => <div className="data-point" key={key}><span>{label(key)}</span><strong>{text(labels[key] ?? value)}</strong></div>)}</div>
}

function RecordGroup({ title, eyebrow, records }: { title: string; eyebrow?: string; records?: EntriesClinicalRecord[] }) {
  if (!records?.length) return null
  return <section className="clinical-card"><div className="clinical-card-title"><div><small>{eyebrow ?? 'Recorded data'}</small><strong>{title}</strong></div><span className="data-pill">{records.length} recorded</span></div><div className="timeline-list timeline-list-compact">{records.map((record, index) => <article className="timeline-card timeline-card-compact" key={record.id ?? index}><RecordFields record={record} /></article>)}</div></section>
}

function TreatmentCycleCard({ cycle }: { cycle: EntriesClinicalRecord & Record<string, unknown> }) {
  const base = Object.fromEntries(Object.entries(cycle).filter(([key]) => !['outcome', 'recist11_assessments', 'irecist_assessments', 'pathological_response_records', 'progression_sites'].includes(key))) as EntriesClinicalRecord
  return <article className="repeatable-card"><div className="clinical-card-title"><div><small>Treatment cycle</small><strong>{text(cycle.display)}</strong></div></div><RecordFields record={base} />{cycle.outcome ? <RecordGroup title="Outcome and survival" records={[cycle.outcome as EntriesClinicalRecord]} /> : null}<RecordGroup title="RECIST 1.1" records={cycle.recist11_assessments as EntriesClinicalRecord[]} /><RecordGroup title="iRECIST" records={cycle.irecist_assessments as EntriesClinicalRecord[]} /><RecordGroup title="Pathological response" records={cycle.pathological_response_records as EntriesClinicalRecord[]} /><RecordGroup title="Progression sites" records={cycle.progression_sites as EntriesClinicalRecord[]} /></article>
}

export default function EntriesPatientDetailPage() {
  const patientId = Number(useParams().patientId)
  const detailQuery = useQuery({ queryKey: ['entries-patient-clinical', patientId], queryFn: () => fetchEntriesPatientClinicalDetail(patientId), enabled: Number.isFinite(patientId) })
  if (detailQuery.isLoading) return <section className="panel state-card"><p>Loading complete clinical record…</p></section>
  if (!detailQuery.data) return <section className="panel state-card"><h3>Patient record unavailable</h3><Link className="secondary-button" to="/entries/new">Create entry</Link></section>

  const { patient, observations } = detailQuery.data
  return <section className="page-grid">
    <Link className="back-link" to="/entries/patients"><ArrowLeft size={16} />Back to Entries records</Link>
    <section className="hero-panel hero-panel-tight"><div className="hero-copy"><p className="eyebrow">Entries clinical record</p><h2>{text(patient.name)}</h2><p className="hero-text">{text(patient.patient_id)} · {text(patient.phone)} · {observations.length} observation{observations.length === 1 ? '' : 's'}</p></div><Link className="primary-button" to="/entries/new"><Plus size={16} />New observation</Link></section>
    <section className="panel"><div className="panel-heading"><div><p className="eyebrow">Demography</p><h3>Patient profile</h3></div></div><RecordFields record={patient} /></section>
    {observations.map((entry, index) => {
      const observation = entry.observation as EntriesClinicalRecord
      const cycles = entry.treatment_cycles as Array<EntriesClinicalRecord & Record<string, unknown>>
      return <section className="panel entry-block" key={observation.id}><div className="panel-heading"><div><p className="eyebrow">Observation {index + 1}</p><h3>{text(observation.observed_at)} · {observation.is_draft ? 'Draft' : 'Published'}</h3></div><span className="data-pill">{text(observation.cancer_type)}</span></div><RecordFields record={observation} />
        <div className="clinical-card-grid">
          <RecordGroup title="Clinical context" records={entry.histories as EntriesClinicalRecord[]} />
          <RecordGroup title="Smoking history" records={entry.smoking_history_records as EntriesClinicalRecord[]} />
          <RecordGroup title="Tuberculosis history" records={entry.tb_history_records as EntriesClinicalRecord[]} />
          <RecordGroup title="COVID and vaccination" records={entry.covid_history_records as EntriesClinicalRecord[]} />
          <RecordGroup title="Comorbidities" records={entry.comorbidities as EntriesClinicalRecord[]} />
          <RecordGroup title="Diagnosis" records={entry.diagnoses as EntriesClinicalRecord[]} />
          <RecordGroup title="Histopathology" records={entry.histopathologies as EntriesClinicalRecord[]} />
          <RecordGroup title="Clinical TNM staging" records={entry.clinical_tnm_stagings as EntriesClinicalRecord[]} />
          <RecordGroup title="Pathological TNM staging" records={entry.pathological_tnm_stagings as EntriesClinicalRecord[]} />
          <RecordGroup title="Pathological staging details" records={entry.pathological_staging_details as EntriesClinicalRecord[]} />
          <RecordGroup title="IHC panels" records={entry.ihc_panels as EntriesClinicalRecord[]} />
          <RecordGroup title="IHC results" records={entry.ihc_results as EntriesClinicalRecord[]} />
          <RecordGroup title="IHC staging results" records={entry.ihc_staging_results as EntriesClinicalRecord[]} />
          <RecordGroup title="Molecular pathology" records={entry.molecular_pathologies as EntriesClinicalRecord[]} />
          <RecordGroup title="Cancer markers" records={entry.cancer_markers as EntriesClinicalRecord[]} />
          <RecordGroup title="Past treatment history" records={entry.past_treatment_histories as EntriesClinicalRecord[]} />
          <RecordGroup title="Surgeries" records={entry.surgeries as EntriesClinicalRecord[]} />
          <RecordGroup title="Radiotherapy schedules" records={entry.radiotherapy_schedules as EntriesClinicalRecord[]} />
        </div>
        {cycles?.length ? <section className="clinical-card"><div className="clinical-card-title"><div><small>Treatment</small><strong>Treatment response and outcomes</strong></div><span className="data-pill">{cycles.length} recorded</span></div><div className="entry-repeatable-list">{cycles.map(cycle => <TreatmentCycleCard key={cycle.id} cycle={cycle} />)}</div></section> : null}
      </section>
    })}
  </section>
}
