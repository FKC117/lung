// LEGACY_UI: presentation mapping remains from the former nested patient response.
import { type ReactNode, useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Activity,
  ArrowLeft,
  ChevronDown,
  ClipboardList,
  Dna,
  Download,
  FileText,
  HeartPulse,
  Printer,
  UserRound,
} from 'lucide-react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { adaptEntriesPatientDetail, fetchEntriesPatientClinicalDetail, fetchPatientDetail, type TreatmentCycle } from '../api'
import {
  DataBadge,
  DataPoint,
  EmptyState,
  ListPanel,
  LoadingState,
} from '../components/registry-ui'
import { ClinicalChart } from '../components/ClinicalChart'
import {
  buildMarkerSeries,
  buildTreatmentMix,
  compactJoin,
  formatDate,
  formatDateTime,
  formatStage,
  joinValues,
  metricPalette,
} from '../lib/registry'

function hasChanged(left: string | number | null | undefined, right: string | number | null | undefined) {
  return String(left ?? '').trim() !== String(right ?? '').trim()
}

function molecularResultCategory(status: string | null | undefined) {
  const normalized = status?.toLowerCase() ?? ''
  if (normalized.includes('negative') || normalized.includes('not detected') || normalized.includes('wild type')) {
    return { label: 'Negative / not detected', color: '#64748b' }
  }
  if (normalized.includes('positive') || normalized.includes('detected') || normalized.includes('mutated')) {
    return { label: 'Detected / positive', color: '#f59e0b' }
  }
  return { label: 'Result recorded', color: '#38bdf8' }
}

function ClinicalCard({
  id,
  eyebrow,
  title,
  icon,
  count,
  hasData,
  defaultOpen,
  emptyMessage,
  children,
}: {
  id: string
  eyebrow: string
  title: string
  icon: ReactNode
  count?: number
  hasData: boolean
  defaultOpen?: boolean
  emptyMessage: string
  children: ReactNode
}) {
  return (
    <details
      className={hasData ? 'clinical-card clinical-card-populated' : 'clinical-card'}
      id={id}
      open={defaultOpen ?? hasData}
    >
      <summary>
        <span className="clinical-card-icon">{icon}</span>
        <span className="clinical-card-title">
          <small>{eyebrow}</small>
          <strong>{title}</strong>
        </span>
        <span className={hasData ? 'clinical-card-state clinical-card-state-live' : 'clinical-card-state'}>
          {hasData ? `${count ?? 1} recorded` : 'No data'}
        </span>
        <ChevronDown className="clinical-card-chevron" size={18} aria-hidden="true" />
      </summary>
      <div className="clinical-card-body">
        {hasData ? children : <p className="clinical-card-empty-copy">{emptyMessage}</p>}
      </div>
    </details>
  )
}

function TreatmentResponseCard({ cycle, index }: { cycle: TreatmentCycle; index: number }) {
  return (
    <article className="treatment-response-card">
      <div className="treatment-response-head">
        <div>
          <p className="eyebrow">Treatment cycle {index + 1}</p>
          <h4>{cycle.current_chemo_protocol || 'Treatment assessment'}</h4>
        </div>
        <span className="result-chip">{cycle.chemo_cycle_no ? `Cycle ${cycle.chemo_cycle_no}` : 'Cycle not recorded'}</span>
      </div>

      <div className="response-assessment-grid">
        <section>
          <h5>Clinical outcome</h5>
          <div className="detail-grid detail-grid-compact">
            <DataPoint label="Disease progression status" value={cycle.disease_progression_status} />
            <DataPoint label="Progression status date" value={formatDate(cycle.disease_progression_status_date)} />
            <DataPoint label="Survival status" value={cycle.survival_status} />
            <DataPoint label="Survival status date" value={formatDate(cycle.survival_status_date)} />
            <DataPoint label="Progression-free survival (PFS)" value={cycle.progression_free_survival} />
            <DataPoint label="Overall survival (OS)" value={cycle.overall_survival} />
          </div>
        </section>
        <section>
          <h5>RECIST 1.1</h5>
          <div className="detail-grid detail-grid-compact">
            <DataPoint label="Target lesion" value={cycle.recist_1_target_lesion} />
            <DataPoint label="Non-target lesion" value={cycle.recist_1_non_target_lesion} />
            <DataPoint label="New lesion" value={cycle.recist_1_new_lesion} />
            <DataPoint label="Result" value={cycle.recist_1_result} />
            <DataPoint label="Assessment date" value={formatDate(cycle.recist_1_date)} />
            <DataPoint label="Method" value={cycle.recist_1_method_of_estimation} />
          </div>
        </section>
        <section>
          <h5>iRECIST</h5>
          <div className="detail-grid detail-grid-compact">
            <DataPoint label="Target lesion" value={cycle.irecist_target_lesion} />
            <DataPoint label="Non-target lesion" value={cycle.irecist_non_target_lesion} />
            <DataPoint label="New lesion" value={cycle.irecist_new_lesion} />
            <DataPoint label="Result" value={cycle.irecist_result} />
            <DataPoint label="Assessment date" value={formatDate(cycle.irecist_date)} />
            <DataPoint label="Method" value={cycle.irecist_method_of_estimation} />
          </div>
        </section>
        <section>
          <h5>Pathological response rate</h5>
          <div className="detail-grid detail-grid-compact">
            <DataPoint label="Target lesion" value={cycle.pathological_response_rate_target_lesion} />
            <DataPoint label="Non-target lesion" value={cycle.pathological_response_rate_non_target_lesion} />
            <DataPoint label="New lesion" value={cycle.pathological_response_rate_new_lesion} />
            <DataPoint label="Result" value={cycle.pathological_response_rate_result} />
            <DataPoint label="Assessment date" value={formatDate(cycle.pathological_response_rate_date)} />
            <DataPoint label="Method" value={cycle.pathological_method_of_estimation} />
          </div>
        </section>
      </div>
    </article>
  )
}

export default function PatientDetailPage() {
  const { registryId = '', patientId = '' } = useParams()
  const isEntriesRecord = Boolean(patientId)
  const detailIdentifier = isEntriesRecord ? patientId : registryId
  const [searchParams, setSearchParams] = useSearchParams()
  const patientQuery = useQuery({
    queryKey: ['patient-detail', isEntriesRecord ? 'entries' : 'registry', detailIdentifier],
    queryFn: async () => isEntriesRecord
      ? adaptEntriesPatientDetail(await fetchEntriesPatientClinicalDetail(Number(patientId)))
      : fetchPatientDetail(registryId),
    enabled: Boolean(detailIdentifier),
  })
  const patient = patientQuery.data ?? null
  const siteFilter = searchParams.get('site') ?? 'all'
  const draftFilter = searchParams.get('draft') ?? 'all'

  const filteredObservations = useMemo(
    () =>
      [...(patient?.observations ?? [])]
        .filter((observation) => {
          const siteMatches =
            siteFilter === 'all' ||
            (observation.diagnosis_primary_site ?? '').toLowerCase() === siteFilter
          const draftMatches =
            draftFilter === 'all' ||
            (draftFilter === 'draft' ? observation.is_draft : !observation.is_draft)

          return siteMatches && draftMatches
        })
        .sort((left, right) =>
          (left.observed_at ?? '').localeCompare(right.observed_at ?? '') || left.id - right.id,
        ),
    [draftFilter, patient?.observations, siteFilter],
  )

  const availableSites = useMemo(
    () =>
      [
        ...new Set(
          (patient?.observations ?? [])
            .map((observation) => observation.diagnosis_primary_site?.trim())
            .filter((site): site is string => Boolean(site)),
        ),
      ].sort((left, right) => left.localeCompare(right)),
    [patient?.observations],
  )

  // IDs, rather than positions, keep a shared link pointed at the same visit after sorting or filtering.
  const selectedObservationId = Number(searchParams.get('observation_id'))
  const selectedCompareObservationId = Number(searchParams.get('compare_id'))
  const legacyObservationIndex = Number(searchParams.get('observation'))
  const legacyCompareObservationIndex = Number(searchParams.get('compare'))
  const defaultObservationIndex = Math.max(filteredObservations.length - 1, 0)
  const defaultCompareObservationIndex = Math.max(filteredObservations.length - 2, 0)
  const selectedObservationIndex = filteredObservations.findIndex(
    (observation) => observation.id === selectedObservationId,
  )
  const selectedCompareObservationIndex = filteredObservations.findIndex(
    (observation) => observation.id === selectedCompareObservationId,
  )
  const activeObservationIndex = selectedObservationIndex >= 0
    ? selectedObservationIndex
    : Number.isInteger(legacyObservationIndex) && legacyObservationIndex >= 0
      ? Math.min(legacyObservationIndex, defaultObservationIndex)
      : defaultObservationIndex
  const compareObservationIndex = selectedCompareObservationIndex >= 0
    ? selectedCompareObservationIndex
    : Number.isInteger(legacyCompareObservationIndex) && legacyCompareObservationIndex >= 0
      ? Math.min(legacyCompareObservationIndex, defaultObservationIndex)
      : defaultCompareObservationIndex
  const activeObservation = filteredObservations[activeObservationIndex]
  const compareObservation = filteredObservations[compareObservationIndex]
  const reviewSection = searchParams.get('review_section')

  useEffect(() => {
    if (!reviewSection || patientQuery.isLoading || !activeObservation) return
    const timeout = window.setTimeout(() => {
      const card = document.getElementById(reviewSection)
      if (!card) return
      if (card instanceof HTMLDetailsElement) card.open = true
      card.scrollIntoView({ behavior: 'smooth', block: 'start' })
      card.setAttribute('tabindex', '-1')
      card.focus({ preventScroll: true })
    }, 100)
    return () => window.clearTimeout(timeout)
  }, [activeObservation?.id, patientQuery.isLoading, reviewSection])

  const treatmentMix = buildTreatmentMix(patient?.observations ?? [])
  const markerSeries = buildMarkerSeries(patient?.observations ?? [])
  const markerBaselineGroups = useMemo(() => {
    const groups = new Map<string, Array<{ label: string; value: number; date: string }>>()
    activeObservation?.cancer_markers.forEach((marker) => {
      const value = Number(marker.value)
      if (!marker.name || !Number.isFinite(value)) {
        return
      }
      const unit = marker.unit || 'Unit not recorded'
      const values = groups.get(unit) ?? []
      values.push({
        label: marker.name,
        value,
        date: marker.observed_on ? formatDate(marker.observed_on) : formatDate(activeObservation.observed_at),
      })
      groups.set(unit, values)
    })
    return [...groups.entries()].map(([unit, readings]) => ({ unit, readings }))
  }, [activeObservation])
  const activeMolecularResults = useMemo(
    () =>
      (activeObservation?.molecular_pathologies ?? []).map((item, index) => {
        const category = molecularResultCategory(item.status)
        return {
          label: item.gene || item.method || `Assay ${index + 1}`,
          category,
          detail: compactJoin([item.method, item.exon, item.status, item.specimen]),
          observedOn: item.observed_on ? formatDate(item.observed_on) : '',
        }
      }),
    [activeObservation],
  )
  const molecularHistoryGroups = useMemo(() => {
    const groups = new Map<string, {
      summary: string
      testDate: string | null
      observations: Array<{ id: number; label: string }>
      recordCount: number
    }>()

    ;(patient?.observations ?? []).forEach((observation, index) => {
      observation.molecular_pathologies.forEach((item) => {
        const testDate = item.observed_on ?? null
        const summary = compactJoin([
          item.method,
          item.gene,
          item.exon,
          item.specimen,
          item.status,
        ]) ?? 'Molecular result recorded'
        const key = [testDate, item.method, item.gene, item.exon, item.specimen, item.status]
          .map((value) => String(value ?? '').trim().toLowerCase())
          .join('|')
        const existing = groups.get(key)
        const observationLabel = `Obs ${observation.legacy_id ?? index + 1} / ${formatDate(observation.observed_at)}`

        if (existing) {
          existing.recordCount += 1
          if (!existing.observations.some((source) => source.id === observation.id)) {
            existing.observations.push({ id: observation.id, label: observationLabel })
          }
          return
        }

        groups.set(key, {
          summary,
          testDate,
          observations: [{ id: observation.id, label: observationLabel }],
          recordCount: 1,
        })
      })
    })

    return [...groups.values()].sort((left, right) =>
      (right.testDate ?? '').localeCompare(left.testDate ?? '') || left.summary.localeCompare(right.summary),
    )
  }, [patient?.observations])
  const clinicalCourse = useMemo(() => {
    const events: Array<{ date: string; category: string; label: string; detail: string; observationIndex: number; targetId: string }> = []
    const add = (date: string | null | undefined, category: string, label: string, detail: string, observationIndex: number, targetId: string) => {
      if (date) events.push({ date, category, label, detail, observationIndex, targetId })
    }

    ;(patient?.observations ?? [])
      .map((observation, sourceIndex) => ({ observation, sourceIndex }))
      .sort((left, right) => (left.observation.observed_at ?? '').localeCompare(right.observation.observed_at ?? ''))
      .forEach(({ observation, sourceIndex }, chronologicalIndex) => {
      const diagnosisDetail = compactJoin([observation.diagnosis_disease_group, observation.diagnosis_primary_site]) ?? ''
      add(observation.history?.first_diagnosis_date, 'Diagnosis', 'First diagnosis', diagnosisDetail, sourceIndex, 'diagnosis')
      add(observation.observed_at, 'Follow-up', `Observation ${chronologicalIndex + 1}`, compactJoin([observation.center_name, observation.consulting_doctor_name]) ?? '', sourceIndex, 'clinical-snapshot')
      observation.histopathologies.forEach((item) => add(item.observed_on, 'Pathology', 'Histopathology', compactJoin([item.histology_type, item.site]) ?? '', sourceIndex, 'pathology'))
      observation.molecular_pathologies.forEach((item) => add(item.observed_on, 'Molecular', 'Molecular test', compactJoin([item.gene, item.exon, item.status]) ?? '', sourceIndex, 'molecular-pathology'))
      observation.treatment_cycles.forEach((item) => {
        add(item.chemo_starting_date, 'Treatment', 'Systemic therapy', compactJoin([item.current_chemo_protocol, item.chemo_cycle_no ? `Cycle ${item.chemo_cycle_no}` : null]) ?? '', sourceIndex, 'treatment')
        add(item.recist_1_date, 'Response', 'RECIST assessment', item.recist_1_result ?? '', sourceIndex, 'response-outcomes')
        add(item.irecist_date, 'Response', 'iRECIST assessment', item.irecist_result ?? '', sourceIndex, 'response-outcomes')
        add(item.disease_progression_status_date, 'Response', 'Progression status', item.disease_progression_status ?? '', sourceIndex, 'response-outcomes')
      })
      observation.radiotherapy_schedules.forEach((item) => add(item.start_date, 'Treatment', 'Radiotherapy', item.intent ?? '', sourceIndex, 'treatment'))
      observation.surgeries.forEach((item) => add(item.surgery_date, 'Treatment', 'Surgery', item.modality ?? '', sourceIndex, 'treatment'))
    })

    const seen = new Set<string>()
    return events
      .sort((left, right) => left.date.localeCompare(right.date))
      .filter((event) => {
        const key = `${event.date}|${event.category}|${event.label}|${event.detail}`
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })
  }, [patient?.observations])
  const patientJourney = useMemo(() => {
    const groups = new Map<string, typeof clinicalCourse>()
    clinicalCourse.forEach((event) => {
      const key = event.date.slice(0, 10)
      const events = groups.get(key) ?? []
      events.push(event)
      groups.set(key, events)
    })
    return [...groups.entries()].map(([date, events]) => ({ date, events }))
  }, [clinicalCourse])
  const journeyDisplay = useMemo(
    () =>
      patientJourney.map((group) => {
        const branches = new Map<string, typeof group.events>()
        group.events.forEach((event) => {
          const events = branches.get(event.category) ?? []
          events.push(event)
          branches.set(event.category, events)
        })
        return {
          date: group.date,
          branches: [...branches.entries()].map(([category, events]) => {
            const latestEvent = events[events.length - 1]
            const descriptions = [...new Set(events.map((event) => event.detail).filter(Boolean))]
            return {
              category,
              label: events.length === 1 ? latestEvent.label : `${events.length} ${category.toLowerCase()} records`,
              detail: descriptions.slice(0, 2).join(' | '),
              event: latestEvent,
            }
          }),
        }
      }),
    [patientJourney],
  )
  const clinicalBriefSections = useMemo(() => {
    const observations = patient?.observations ?? []
    const uniqueJoined = (values: Array<string | null | undefined>) =>
      [...new Set(values.filter((value): value is string => Boolean(value?.trim())))].join(', ')
    const cycles = observations.flatMap((observation) => observation.treatment_cycles)
    const histories = observations.map((observation) => observation.history).filter(Boolean)
    const firstDiagnosisDate = histories
      .map((history) => history?.first_diagnosis_date)
      .filter((date): date is string => Boolean(date))
      .sort()[0]

    return [
      {
        title: 'Patient profile',
        items: [
          { label: 'Age', value: patient?.age ? `${patient.age} years` : '' },
          { label: 'Sex', value: patient?.gender ?? '' },
          { label: 'BMI', value: uniqueJoined(histories.map((history) => history?.bmi ? String(history.bmi) : '')) },
        ],
      },
      {
        title: 'Clinical context',
        items: [
          { label: 'Covid and vaccination', value: uniqueJoined(histories.flatMap((history) => history?.covid_histories.map((item) => compactJoin([item.status, item.vaccine_name, item.vaccination_dose, item.date ? formatDate(item.date) : null])) ?? [])) },
          { label: 'TB history', value: uniqueJoined(histories.flatMap((history) => history?.tb_histories.map((item) => compactJoin([item.status, item.treatment, item.date ? formatDate(item.date) : null])) ?? [])) },
          { label: 'Smoking history', value: uniqueJoined(histories.flatMap((history) => history?.smoking_histories.map((item) => compactJoin([item.status, item.pack_years ? `${item.pack_years} pack-years` : null])) ?? [])) },
          { label: 'Comorbidities', value: uniqueJoined(observations.flatMap((observation) => observation.comorbidities.map((item) => item.detail))) },
        ],
      },
      {
        title: 'Diagnosis',
        items: [
          { label: 'First diagnosis', value: formatDate(firstDiagnosisDate) },
          { label: 'Disease group', value: uniqueJoined(observations.map((observation) => observation.diagnosis_disease_group)) },
          { label: 'Disease subgroup', value: uniqueJoined(observations.map((observation) => observation.diagnosis_subgroup)) },
          { label: 'Primary site', value: uniqueJoined(observations.map((observation) => observation.diagnosis_primary_site)) },
          { label: 'Laterality', value: uniqueJoined(observations.map((observation) => observation.diagnosis_laterality)) },
          { label: 'Grade', value: uniqueJoined(observations.map((observation) => observation.grade)) },
          { label: 'Metastatic sites', value: uniqueJoined(observations.flatMap((observation) => observation.metastatic_sites.map((item) => item.value))) },
          { label: 'Histopathology', value: uniqueJoined(observations.flatMap((observation) => observation.histopathologies.map((item) => item.detail || item.histology_type))) },
          { label: 'Molecular profile', value: uniqueJoined(observations.flatMap((observation) => observation.molecular_pathologies.map((item) => compactJoin([item.gene, item.exon, item.status])))) },
          { label: 'Cancer markers', value: uniqueJoined(observations.flatMap((observation) => observation.cancer_markers.map((item) => compactJoin([item.name, item.value, item.unit])))) },
          { label: 'Clinical TNM', value: uniqueJoined(observations.flatMap((observation) => observation.clinical_stagings.map((item) => formatStage(item.t, item.n, item.m))) ) },
          { label: 'Pathological TNM', value: uniqueJoined(observations.flatMap((observation) => observation.pathological_stagings.map((item) => formatStage(item.t, item.n, item.m))) ) },
          { label: 'IHC panels', value: uniqueJoined(observations.flatMap((observation) => observation.ihc_panels.flatMap((panel) => panel.details.map((item) => compactJoin([item.marker_type, item.value]))))) },
        ],
      },
      {
        title: 'Treatment',
        items: [
          { label: 'Treatment cycles', value: cycles.length ? String(cycles.length) : '' },
          { label: 'Chemotherapy protocol', value: uniqueJoined(cycles.map((cycle) => cycle.current_chemo_protocol)) },
          { label: 'Chemotherapy details', value: uniqueJoined(cycles.map((cycle) => cycle.chemo_detail)) },
          { label: 'Chemo cycle number', value: uniqueJoined(cycles.map((cycle) => cycle.chemo_cycle_no)) },
          { label: 'Line of treatment', value: uniqueJoined(cycles.map((cycle) => cycle.line_of_treatment)) },
          { label: 'Radiotherapy details', value: uniqueJoined(observations.flatMap((observation) => observation.radiotherapy_schedules.map((item) => compactJoin([joinValues(item.sites.map((site) => site.value)), item.intent, item.total_dose ? `${item.total_dose} cGy` : null])))) },
          { label: 'Surgeries', value: uniqueJoined(observations.flatMap((observation) => observation.surgeries.map((item) => compactJoin([item.modality, joinValues(item.lateralities.map((laterality) => laterality.value))])))) },
        ],
      },
      {
        title: 'Outcomes',
        items: [
          { label: 'Disease progression', value: uniqueJoined(cycles.map((cycle) => cycle.disease_progression_status)) },
          { label: 'RECIST result', value: uniqueJoined(cycles.map((cycle) => cycle.recist_1_result)) },
          { label: 'iRECIST result', value: uniqueJoined(cycles.map((cycle) => cycle.irecist_result)) },
          { label: 'Pathological response', value: uniqueJoined(cycles.map((cycle) => cycle.pathological_response_rate_result)) },
          { label: 'Survival status', value: uniqueJoined(cycles.map((cycle) => cycle.survival_status)) },
          { label: 'PFS', value: uniqueJoined(cycles.map((cycle) => cycle.progression_free_survival)) },
          { label: 'OS', value: uniqueJoined(cycles.map((cycle) => cycle.overall_survival)) },
        ],
      },
    ]
      .map((section) => ({ ...section, items: section.items.filter((item) => item.value) }))
      .filter((section) => section.items.length)
  }, [patient])
  const stagingRecords = useMemo(
    () =>
      filteredObservations.map((observation, index) => ({
        id: observation.id,
        label: `Observation ${index + 1}`,
        date: formatDate(observation.observed_at),
        clinical: formatStage(
          observation.clinical_stagings[0]?.t,
          observation.clinical_stagings[0]?.n,
          observation.clinical_stagings[0]?.m,
        ),
        pathological: formatStage(
          observation.pathological_stagings[0]?.t,
          observation.pathological_stagings[0]?.n,
          observation.pathological_stagings[0]?.m,
        ),
      })).filter((record) => record.clinical || record.pathological),
    [filteredObservations],
  )
  const treatmentTrend = useMemo(
    () =>
      filteredObservations.map((observation, index) => ({
        label: `Obs ${index + 1}`,
        cycles: observation.treatment_cycles.length,
        radiotherapy: observation.radiotherapy_schedules.length,
        surgeries: observation.surgeries.length,
      })),
    [filteredObservations],
  )
  const activeClinicalStage = activeObservation?.clinical_stagings[0]
  const activePathologicalStage = activeObservation?.pathological_stagings[0]
  const activePathologicalDetail =
    activeObservation?.pathological_staging_details[0]
  const activeIhcPanel = activeObservation?.ihc_panels[0]
  const patientTreatmentCycles =
    patient?.observations.flatMap((observation) => observation.treatment_cycles) ?? []
  const patientRadiotherapySchedules =
    patient?.observations.flatMap((observation) => observation.radiotherapy_schedules) ?? []
  const patientSurgeries =
    patient?.observations.flatMap((observation) => observation.surgeries) ?? []
  const responseCycles = patientTreatmentCycles.filter((cycle) =>
      [
        cycle.disease_progression_status,
        cycle.survival_status,
        cycle.recist_1_result,
        cycle.irecist_result,
        cycle.pathological_response_rate_result,
      ].some(Boolean),
    )
  const comparisonHighlights = [
    {
      label: 'Observation date',
      changed: hasChanged(activeObservation?.observed_at, compareObservation?.observed_at),
      summary: `${formatDate(activeObservation?.observed_at)} -> ${formatDate(compareObservation?.observed_at)}`,
    },
    {
      label: 'Disease group',
      changed: hasChanged(
        activeObservation?.diagnosis_disease_group,
        compareObservation?.diagnosis_disease_group,
      ),
      summary: `${activeObservation?.diagnosis_disease_group || ''} -> ${compareObservation?.diagnosis_disease_group || ''}`,
    },
    {
      label: 'Primary site',
      changed: hasChanged(
        activeObservation?.diagnosis_primary_site,
        compareObservation?.diagnosis_primary_site,
      ),
      summary: `${activeObservation?.diagnosis_primary_site || ''} -> ${compareObservation?.diagnosis_primary_site || ''}`,
    },
    {
      label: 'Clinical TNM',
      changed: hasChanged(
        formatStage(
          activeObservation?.clinical_stagings[0]?.t,
          activeObservation?.clinical_stagings[0]?.n,
          activeObservation?.clinical_stagings[0]?.m,
        ),
        formatStage(
          compareObservation?.clinical_stagings[0]?.t,
          compareObservation?.clinical_stagings[0]?.n,
          compareObservation?.clinical_stagings[0]?.m,
        ),
      ),
      summary: `${formatStage(
        activeObservation?.clinical_stagings[0]?.t,
        activeObservation?.clinical_stagings[0]?.n,
        activeObservation?.clinical_stagings[0]?.m,
      ) || ''} -> ${formatStage(
        compareObservation?.clinical_stagings[0]?.t,
        compareObservation?.clinical_stagings[0]?.n,
        compareObservation?.clinical_stagings[0]?.m,
      ) || ''}`,
    },
    {
      label: 'Pathological TNM',
      changed: hasChanged(
        formatStage(
          activeObservation?.pathological_stagings[0]?.t,
          activeObservation?.pathological_stagings[0]?.n,
          activeObservation?.pathological_stagings[0]?.m,
        ),
        formatStage(
          compareObservation?.pathological_stagings[0]?.t,
          compareObservation?.pathological_stagings[0]?.n,
          compareObservation?.pathological_stagings[0]?.m,
        ),
      ),
      summary: `${formatStage(
        activeObservation?.pathological_stagings[0]?.t,
        activeObservation?.pathological_stagings[0]?.n,
        activeObservation?.pathological_stagings[0]?.m,
      ) || ''} -> ${formatStage(
        compareObservation?.pathological_stagings[0]?.t,
        compareObservation?.pathological_stagings[0]?.n,
        compareObservation?.pathological_stagings[0]?.m,
      ) || ''}`,
    },
    {
      label: 'Treatment load',
      changed:
        hasChanged(
          activeObservation?.treatment_cycles.length,
          compareObservation?.treatment_cycles.length,
        ) ||
        hasChanged(
          activeObservation?.radiotherapy_schedules.length,
          compareObservation?.radiotherapy_schedules.length,
        ) ||
        hasChanged(activeObservation?.surgeries.length, compareObservation?.surgeries.length),
      summary: `Cycles ${activeObservation?.treatment_cycles.length ?? 0} -> ${compareObservation?.treatment_cycles.length ?? 0}, RT ${activeObservation?.radiotherapy_schedules.length ?? 0} -> ${compareObservation?.radiotherapy_schedules.length ?? 0}, Surgery ${activeObservation?.surgeries.length ?? 0} -> ${compareObservation?.surgeries.length ?? 0}`,
    },
    {
      label: 'Marker profile',
      changed: hasChanged(
        joinValues(activeObservation?.cancer_markers.map((item) => compactJoin([item.name, item.value])) ?? []),
        joinValues(compareObservation?.cancer_markers.map((item) => compactJoin([item.name, item.value])) ?? []),
      ),
      summary: `${joinValues(
        activeObservation?.cancer_markers.map((item) => compactJoin([item.name, item.value])) ?? [],
      ) || ''} -> ${joinValues(
        compareObservation?.cancer_markers.map((item) => compactJoin([item.name, item.value])) ?? [],
      ) || ''}`,
    },
  ].filter((item) => item.changed)
  const compareReportLines = [
    `Primary observation: ${formatDateTime(activeObservation?.observed_at) || ''}${
      activeObservation?.center_name ? ` at ${activeObservation.center_name}` : ''
    }`,
    `Comparison observation: ${formatDateTime(compareObservation?.observed_at) || ''}${
      compareObservation?.center_name ? ` at ${compareObservation.center_name}` : ''
    }`,
    hasChanged(
      activeObservation?.diagnosis_primary_site,
      compareObservation?.diagnosis_primary_site,
    )
      ? `Primary site changed from ${activeObservation?.diagnosis_primary_site || ''} to ${compareObservation?.diagnosis_primary_site || ''}.`
      : `Primary site remained ${activeObservation?.diagnosis_primary_site || ''}.`,
    hasChanged(
      activeObservation?.diagnosis_disease_group,
      compareObservation?.diagnosis_disease_group,
    )
      ? `Disease group changed from ${activeObservation?.diagnosis_disease_group || ''} to ${compareObservation?.diagnosis_disease_group || ''}.`
      : `Disease group remained ${activeObservation?.diagnosis_disease_group || ''}.`,
    hasChanged(
      formatStage(
        activeObservation?.clinical_stagings[0]?.t,
        activeObservation?.clinical_stagings[0]?.n,
        activeObservation?.clinical_stagings[0]?.m,
      ),
      formatStage(
        compareObservation?.clinical_stagings[0]?.t,
        compareObservation?.clinical_stagings[0]?.n,
        compareObservation?.clinical_stagings[0]?.m,
      ),
    )
      ? `Clinical TNM changed from ${
          formatStage(
            activeObservation?.clinical_stagings[0]?.t,
            activeObservation?.clinical_stagings[0]?.n,
            activeObservation?.clinical_stagings[0]?.m,
          ) || ''
        } to ${
          formatStage(
            compareObservation?.clinical_stagings[0]?.t,
            compareObservation?.clinical_stagings[0]?.n,
            compareObservation?.clinical_stagings[0]?.m,
          ) || ''
        }.`
      : `Clinical TNM remained ${
          formatStage(
            activeObservation?.clinical_stagings[0]?.t,
            activeObservation?.clinical_stagings[0]?.n,
            activeObservation?.clinical_stagings[0]?.m,
          ) || ''
        }.`,
    hasChanged(
      joinValues(activeObservation?.cancer_markers.map((item) => compactJoin([item.name, item.value, item.unit])) ?? []),
      joinValues(compareObservation?.cancer_markers.map((item) => compactJoin([item.name, item.value, item.unit])) ?? []),
    )
      ? `Marker profile changed from ${
          joinValues(
            activeObservation?.cancer_markers.map((item) => compactJoin([item.name, item.value, item.unit])) ?? [],
          ) || ''
        } to ${
          joinValues(
            compareObservation?.cancer_markers.map((item) => compactJoin([item.name, item.value, item.unit])) ?? [],
          ) || ''
        }.`
      : `Marker profile remained ${
          joinValues(
            activeObservation?.cancer_markers.map((item) => compactJoin([item.name, item.value, item.unit])) ?? [],
          ) || ''
        }.`,
    `Treatment burden: cycles ${activeObservation?.treatment_cycles.length ?? 0} -> ${compareObservation?.treatment_cycles.length ?? 0}, radiotherapy ${activeObservation?.radiotherapy_schedules.length ?? 0} -> ${compareObservation?.radiotherapy_schedules.length ?? 0}, surgeries ${activeObservation?.surgeries.length ?? 0} -> ${compareObservation?.surgeries.length ?? 0}.`,
  ]
  const sectionLinks = [
    { id: 'clinical-snapshot', label: 'Snapshot' },
    { id: 'demography', label: 'Demography' },
    { id: 'diagnosis', label: 'Diagnosis' },
    { id: 'staging', label: 'Staging' },
    { id: 'pathology', label: 'Pathology' },
    { id: 'treatment', label: 'Treatment' },
    { id: 'marker-trend', label: 'Markers' },
    { id: 'observation-timeline', label: 'Timeline' },
  ]

  if (patientQuery.isLoading) {
    return (
      <section className="panel">
        <LoadingState label="Loading patient detail" />
      </section>
    )
  }

  if (!patient) {
    return (
      <section className="panel">
        <EmptyState
          title="Patient not found"
          detail="The selected registry record could not be loaded."
        />
      </section>
    )
  }
  const currentPatient = patient

  function updateFilters(nextSite: string, nextDraft: string) {
    const next = new URLSearchParams(searchParams)
    if (nextSite === 'all') {
      next.delete('site')
    } else {
      next.set('site', nextSite)
    }
    if (nextDraft === 'all') {
      next.delete('draft')
    } else {
      next.set('draft', nextDraft)
    }
    next.delete('observation')
    next.delete('compare')
    next.delete('observation_id')
    next.delete('compare_id')
    setSearchParams(next, { replace: true })
  }

  function selectObservation(index: number) {
    const observation = filteredObservations[index]
    if (!observation) return
    const next = new URLSearchParams(searchParams)
    next.set('observation_id', String(observation.id))
    next.delete('observation')
    if (filteredObservations.length > 1 && index === compareObservationIndex) {
      const replacementIndex = index === 0 ? 1 : index - 1
      next.set('compare_id', String(filteredObservations[replacementIndex].id))
      next.delete('compare')
    }
    setSearchParams(next, { replace: true })
  }

  function selectCompareObservation(index: number) {
    if (index === activeObservationIndex) {
      return
    }
    const observation = filteredObservations[index]
    if (!observation) return
    const next = new URLSearchParams(searchParams)
    next.set('compare_id', String(observation.id))
    next.delete('compare')
    setSearchParams(next, { replace: true })
  }

  function focusObservation(index: number) {
    selectObservation(index)
    const section = document.getElementById('clinical-snapshot')
    section?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  function focusJourneyEvent(event: { observationIndex: number; targetId: string }) {
    // Journey always spans the whole record, so clear filters before selecting its observation.
    const next = new URLSearchParams(searchParams)
    next.delete('site')
    next.delete('draft')
    const observation = patient?.observations[event.observationIndex]
    if (observation) next.set('observation_id', String(observation.id))
    next.delete('observation')
    next.delete('compare')
    next.delete('compare_id')
    setSearchParams(next, { replace: true })
    window.setTimeout(() => {
      document.getElementById(event.targetId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 0)
  }

  function printRecord() {
    window.print()
  }

  function exportSummary() {
    const lines = [
      `Patient Name,${currentPatient.name || ''}`,
      `Registry ID,${currentPatient.registry_id || ''}`,
      `Legacy Unique ID,${currentPatient.legacy_unique_id || ''}`,
      `Registration No,${currentPatient.registration_no || ''}`,
      `Phone,${currentPatient.phone || ''}`,
      `Gender,${currentPatient.gender || ''}`,
      `Age,${currentPatient.age ?? ''}`,
      `District,${currentPatient.district || ''}`,
      `Publication Filter,${draftFilter}`,
      `Site Filter,${siteFilter}`,
      '',
      'Selected Observation',
      `Observed At,${activeObservation?.observed_at || ''}`,
      `Doctor,${activeObservation?.consulting_doctor_name || ''}`,
      `Center,${activeObservation?.center_name || ''}`,
      `Cancer Type,${activeObservation?.cancer_type || ''}`,
      `Disease Group,${activeObservation?.diagnosis_disease_group || ''}`,
      `Primary Site,${activeObservation?.diagnosis_primary_site || ''}`,
      `Laterality,${activeObservation?.diagnosis_laterality || ''}`,
      `Grade,${activeObservation?.grade || ''}`,
      '',
      'Observation Timeline',
      ...filteredObservations.map(
        (observation, index) =>
          [
            index + 1,
            observation.observed_at || '',
            observation.is_draft ? 'Draft' : 'Published',
            observation.diagnosis_disease_group || '',
            observation.diagnosis_primary_site || '',
            observation.center_name || '',
          ].join(','),
      ),
    ]
    const blob = new Blob([lines.join('\n')], {
      type: 'text/csv;charset=utf-8;',
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${currentPatient.registry_id || 'patient-record'}-summary.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  function exportCompareCsv() {
    const rows = [
      ['Field', 'Primary Observation', 'Comparison Observation'],
      ['Observed At', formatDateTime(activeObservation?.observed_at), formatDateTime(compareObservation?.observed_at)],
      ['Doctor', activeObservation?.consulting_doctor_name || '', compareObservation?.consulting_doctor_name || ''],
      ['Center', activeObservation?.center_name || '', compareObservation?.center_name || ''],
      ['Disease Group', activeObservation?.diagnosis_disease_group || '', compareObservation?.diagnosis_disease_group || ''],
      ['Primary Site', activeObservation?.diagnosis_primary_site || '', compareObservation?.diagnosis_primary_site || ''],
      ['Laterality', activeObservation?.diagnosis_laterality || '', compareObservation?.diagnosis_laterality || ''],
      ['Clinical TNM',
        formatStage(
          activeObservation?.clinical_stagings[0]?.t,
          activeObservation?.clinical_stagings[0]?.n,
          activeObservation?.clinical_stagings[0]?.m,
        ) || '',
        formatStage(
          compareObservation?.clinical_stagings[0]?.t,
          compareObservation?.clinical_stagings[0]?.n,
          compareObservation?.clinical_stagings[0]?.m,
        ) || '',
      ],
      ['Pathological TNM',
        formatStage(
          activeObservation?.pathological_stagings[0]?.t,
          activeObservation?.pathological_stagings[0]?.n,
          activeObservation?.pathological_stagings[0]?.m,
        ) || '',
        formatStage(
          compareObservation?.pathological_stagings[0]?.t,
          compareObservation?.pathological_stagings[0]?.n,
          compareObservation?.pathological_stagings[0]?.m,
        ) || '',
      ],
      ['Treatment Cycles', String(activeObservation?.treatment_cycles.length ?? 0), String(compareObservation?.treatment_cycles.length ?? 0)],
      ['Radiotherapy Schedules', String(activeObservation?.radiotherapy_schedules.length ?? 0), String(compareObservation?.radiotherapy_schedules.length ?? 0)],
      ['Surgeries', String(activeObservation?.surgeries.length ?? 0), String(compareObservation?.surgeries.length ?? 0)],
      [
        'Cancer Markers',
        joinValues(
          activeObservation?.cancer_markers.map((item) => compactJoin([item.name, item.value, item.unit])) ?? [],
        ),
        joinValues(
          compareObservation?.cancer_markers.map((item) => compactJoin([item.name, item.value, item.unit])) ?? [],
        ),
      ],
    ]
    const content = rows
      .map((row) => row.map((value) => `"${String(value ?? '').replaceAll('"', '""')}"`).join(','))
      .join('\n')
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${currentPatient.registry_id || 'patient-record'}-comparison.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  async function copyCompareReport() {
    try {
      await navigator.clipboard.writeText(compareReportLines.join('\n'))
    } catch (_error) {
      window.alert('Copy failed. You can still print or export the summary.')
    }
  }

  return (
    <section className="page-grid">
      <Link className="back-link" to={isEntriesRecord ? '/entries/patients' : '/patients'}>
        <ArrowLeft size={16} />
        Back to search
      </Link>

      <section className="hero-panel hero-panel-tight">
        <div className="hero-copy">
          <p className="eyebrow">Patient Record</p>
          <h2>{patient.name || patient.registry_id}</h2>
          <p className="hero-text">
            {patient.registry_id}
            {patient.legacy_unique_id ? ` | ${patient.legacy_unique_id}` : ''}
            {patient.registration_no ? ` | Reg ${patient.registration_no}` : ''}
          </p>
        </div>
        <div className="header-badges">
          {patient.gender ? <span className="data-pill">{patient.gender}</span> : null}
          {patient.age ? <span className="data-pill">{patient.age} years</span> : null}
          {patient.phone ? <span className="data-pill">{patient.phone}</span> : null}
        </div>
      </section>

      <section className="panel patient-journey-panel" id="patient-journey">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Patient Journey</p>
            <h3>Clinical record from diagnosis to latest follow-up</h3>
          </div>
          <span className="result-chip">{clinicalCourse.length} dated milestones</span>
        </div>
        {clinicalCourse.length ? (
          <>
            <p className="clinical-card-empty-copy">Select a milestone to open its observation and linked clinical section.</p>
            <div className="journey-scroll" aria-label="Patient journey timeline">
              <div className="journey-fishbone">
                {journeyDisplay.map((group, groupIndex) => (
                  <div className="journey-date-group" key={group.date}>
                    <div className="journey-branch journey-branch-top">
                      {group.branches.filter((_, index) => (index + groupIndex) % 2 === 0).map((branch, index) => (
                        <button key={`${branch.category}-${branch.label}-${index}`} type="button" className={`journey-event journey-event-${branch.category.toLowerCase().replace(/[^a-z]/g, '-')}`} onClick={() => focusJourneyEvent(branch.event)}>
                          <span>{branch.category}</span>
                          <strong>{branch.label}</strong>
                          {branch.detail ? <small>{branch.detail}</small> : null}
                        </button>
                      ))}
                    </div>
                    <div className="journey-spine-node">
                      <span className="journey-node" />
                      <time>{formatDate(group.date)}</time>
                    </div>
                    <div className="journey-branch journey-branch-bottom">
                      {group.branches.filter((_, index) => (index + groupIndex) % 2 !== 0).map((branch, index) => (
                        <button key={`${branch.category}-${branch.label}-${index}`} type="button" className={`journey-event journey-event-${branch.category.toLowerCase().replace(/[^a-z]/g, '-')}`} onClick={() => focusJourneyEvent(branch.event)}>
                          <span>{branch.category}</span>
                          <strong>{branch.label}</strong>
                          {branch.detail ? <small>{branch.detail}</small> : null}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="section-nav patient-journey-events" aria-label="Patient journey milestones" hidden>
              {clinicalCourse.map((event, index) => (
                <button
                  key={`${event.date}-${event.category}-${event.label}-${index}`}
                  type="button"
                  className="section-chip"
                  onClick={() => focusJourneyEvent(event)}
                >
                  {formatDate(event.date)} · {event.category}: {event.label}
                </button>
              ))}
            </div>
          </>
        ) : (
          <EmptyState title="No dated journey milestones available" detail="Dated diagnosis, pathology, treatment, response, and follow-up records will appear here as they are documented." />
        )}
      </section>

      {clinicalBriefSections.length ? (
        <section className="panel clinical-brief-panel" id="clinical-brief">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Clinical Brief</p>
              <h3>Patient-wide clinical summary</h3>
            </div>
            <span className="result-chip">All recorded observations</span>
          </div>
          <div className="clinical-brief-grid">
            {clinicalBriefSections.map((section) => (
              <article className={`clinical-brief-column clinical-brief-${section.title.toLowerCase().replace(/[^a-z]+/g, '-')}`} key={section.title}>
                <h4>{section.title}</h4>
                <div className="detail-grid detail-grid-compact">
                  {section.items.map((item) => (
                    <DataPoint key={item.label} label={item.label} value={item.value} />
                  ))}
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <section className="panel detail-toolbar-panel">
        <div className="detail-toolbar">
          <div className="section-nav" aria-label="Patient detail sections">
            {sectionLinks.map((section) => (
              <a key={section.id} className="section-chip" href={`#${section.id}`}>
                {section.label}
              </a>
            ))}
          </div>
          <div className="panel-actions">
            {patient.can_edit ? (
              <Link className="secondary-button" to={`/patients/${patient.registry_id}/edit`}>
                Edit record
              </Link>
            ) : null}
            <button type="button" className="secondary-button" onClick={printRecord}>
              <Printer size={16} />
              Print record
            </button>
            <button type="button" className="secondary-button" onClick={exportSummary}>
              <Download size={16} />
              Export summary
            </button>
          </div>
        </div>
      </section>

      <section className="panel panel-compact">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Observation Filter</p>
            <h3>Narrow visits fast</h3>
          </div>
          <span className="result-chip">
            {filteredObservations.length} of {currentPatient.observations.length} shown
          </span>
        </div>
        <div className="filter-bar">
          <label className="filter-field">
            <span>Primary site</span>
            <select
              className="filter-select"
              value={siteFilter}
              onChange={(event) => updateFilters(event.target.value, draftFilter)}
            >
              <option value="all">All sites</option>
              {availableSites.map((site) => (
                <option key={site} value={site.toLowerCase()}>
                  {site}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Publication state</span>
            <select
              className="filter-select"
              value={draftFilter}
              onChange={(event) => updateFilters(siteFilter, event.target.value)}
            >
              <option value="all">All observations</option>
              <option value="published">Published only</option>
              <option value="draft">Draft only</option>
            </select>
          </label>
        </div>
      </section>

      <section className="panel panel-compact">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Observation Switcher</p>
            <h3>Visit selector</h3>
          </div>
          <span className="result-chip">
            {filteredObservations.length
              ? `Obs ${activeObservation?.legacy_id ?? activeObservationIndex + 1} / ${filteredObservations.length}`
              : 'No observations'}
          </span>
        </div>
        {filteredObservations.length ? (
          <div className="observation-strip observation-strip-compact">
            {filteredObservations.map((observation, index) => (
              <button
                key={observation.id}
                type="button"
                className={
                  index === activeObservationIndex
                    ? 'observation-tab observation-tab-active'
                    : 'observation-tab'
                }
                onClick={() => selectObservation(index)}
              >
                <span>Obs {observation.legacy_id ?? index + 1}</span>
                <strong>{formatDate(observation.observed_at)}</strong>
                <small>{observation.diagnosis_primary_site || `Record ${observation.id}`}</small>
              </button>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No observations match the current filter"
            detail="Try switching the site or publication-state filters to bring observations back into view."
          />
        )}
      </section>

      <section className="panel" hidden={filteredObservations.length < 2}>
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Observation Compare</p>
            <h3>Place two visits side by side</h3>
          </div>
          <span className="result-chip">
            {filteredObservations.length ? `Comparing ${activeObservationIndex + 1} and ${compareObservationIndex + 1}` : 'No observations'}
          </span>
        </div>
        {filteredObservations.length ? (
          <>
            <div className="compare-report">
              <div className="compare-report-head">
                <div>
                  <p className="eyebrow">Visit Comparison</p>
                  <h3>Shareable comparison summary</h3>
                </div>
                <div className="panel-actions">
                  <button type="button" className="secondary-button" onClick={exportCompareCsv}>
                    <Download size={16} />
                    Export compare CSV
                  </button>
                  <button type="button" className="secondary-button" onClick={copyCompareReport}>
                    <FileText size={16} />
                    Copy summary
                  </button>
                </div>
              </div>
              <div className="compare-report-body">
                {compareReportLines.map((line) => (
                  <p key={line}>{line}</p>
                ))}
              </div>
            </div>
            <div className="compare-summary">
              {comparisonHighlights.length ? (
                comparisonHighlights.map((item) => (
                  <article key={item.label} className="compare-summary-card">
                    <span className="compare-summary-label">{item.label}</span>
                    <strong>{item.summary}</strong>
                  </article>
                ))
              ) : (
                <article className="compare-summary-card compare-summary-card-neutral">
                  <span className="compare-summary-label">Comparison summary</span>
                  <strong>No meaningful changes across the tracked clinical fields.</strong>
                </article>
              )}
            </div>
            <div className="filter-bar">
              <label className="filter-field">
                <span>Primary observation</span>
                <select
                  className="filter-select"
                  value={String(activeObservationIndex)}
                  onChange={(event) => selectObservation(Number(event.target.value))}
                >
                  {filteredObservations.map((observation, index) => (
                    <option key={`primary-${observation.id}`} value={index} disabled={index === compareObservationIndex}>
                      {`Obs ${index + 1} · ${formatDate(observation.observed_at)} · ${observation.diagnosis_primary_site || 'No site'}`}
                    </option>
                  ))}
                </select>
              </label>
              <label className="filter-field">
                <span>Comparison observation</span>
                <select
                  className="filter-select"
                  value={String(compareObservationIndex)}
                  onChange={(event) => selectCompareObservation(Number(event.target.value))}
                >
                  {filteredObservations.map((observation, index) => (
                    <option key={`compare-${observation.id}`} value={index} disabled={index === activeObservationIndex}>
                      {`Obs ${index + 1} · ${formatDate(observation.observed_at)} · ${observation.diagnosis_primary_site || 'No site'}`}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="compare-grid">
              <article className="compare-card">
                <div className="compare-card-head">
                  <p className="timeline-title">Primary observation</p>
                  <span className={activeObservation?.is_draft ? 'status-pill status-draft' : 'status-pill status-live'}>
                    {activeObservation?.is_draft ? 'Draft' : 'Published'}
                  </span>
                </div>
                <div className="detail-grid">
                  <div className={hasChanged(activeObservation?.observed_at, compareObservation?.observed_at) ? 'compare-point compare-point-changed' : 'compare-point'}>
                    <DataPoint label="Observed at" value={formatDateTime(activeObservation?.observed_at)} />
                  </div>
                  <div className={hasChanged(activeObservation?.consulting_doctor_name, compareObservation?.consulting_doctor_name) ? 'compare-point compare-point-changed' : 'compare-point'}>
                    <DataPoint label="Doctor" value={activeObservation?.consulting_doctor_name} />
                  </div>
                  <div className={hasChanged(activeObservation?.center_name, compareObservation?.center_name) ? 'compare-point compare-point-changed' : 'compare-point'}>
                    <DataPoint label="Center" value={activeObservation?.center_name} />
                  </div>
                  <div className={hasChanged(activeObservation?.diagnosis_disease_group, compareObservation?.diagnosis_disease_group) ? 'compare-point compare-point-changed' : 'compare-point'}>
                    <DataPoint label="Disease group" value={activeObservation?.diagnosis_disease_group} />
                  </div>
                  <div className={hasChanged(activeObservation?.diagnosis_primary_site, compareObservation?.diagnosis_primary_site) ? 'compare-point compare-point-changed' : 'compare-point'}>
                    <DataPoint label="Primary site" value={activeObservation?.diagnosis_primary_site} />
                  </div>
                  <div className={hasChanged(activeObservation?.diagnosis_laterality, compareObservation?.diagnosis_laterality) ? 'compare-point compare-point-changed' : 'compare-point'}>
                    <DataPoint label="Laterality" value={activeObservation?.diagnosis_laterality} />
                  </div>
                  <div className={hasChanged(activeObservation?.grade, compareObservation?.grade) ? 'compare-point compare-point-changed' : 'compare-point'}>
                    <DataPoint label="Grade" value={activeObservation?.grade} />
                  </div>
                  <div
                    className={
                      hasChanged(
                        joinValues(activeObservation?.metastatic_sites.map((item) => item.value) ?? []),
                        joinValues(compareObservation?.metastatic_sites.map((item) => item.value) ?? []),
                      )
                        ? 'compare-point compare-point-changed'
                        : 'compare-point'
                    }
                    >
                      <DataPoint
                        label="Metastatic sites"
                        value={joinValues(activeObservation?.metastatic_sites.map((item) => item.value) ?? [])}
                      />
                    </div>
                  <div
                    className={
                      hasChanged(
                        formatStage(
                          activeObservation?.clinical_stagings[0]?.t,
                          activeObservation?.clinical_stagings[0]?.n,
                          activeObservation?.clinical_stagings[0]?.m,
                        ),
                        formatStage(
                          compareObservation?.clinical_stagings[0]?.t,
                          compareObservation?.clinical_stagings[0]?.n,
                          compareObservation?.clinical_stagings[0]?.m,
                        ),
                      )
                        ? 'compare-point compare-point-changed'
                        : 'compare-point'
                    }
                  >
                    <DataPoint
                      label="Clinical TNM"
                      value={formatStage(
                        activeObservation?.clinical_stagings[0]?.t,
                        activeObservation?.clinical_stagings[0]?.n,
                        activeObservation?.clinical_stagings[0]?.m,
                      )}
                    />
                  </div>
                  <div
                    className={
                      hasChanged(
                        formatStage(
                          activeObservation?.pathological_stagings[0]?.t,
                          activeObservation?.pathological_stagings[0]?.n,
                          activeObservation?.pathological_stagings[0]?.m,
                        ),
                        formatStage(
                          compareObservation?.pathological_stagings[0]?.t,
                          compareObservation?.pathological_stagings[0]?.n,
                          compareObservation?.pathological_stagings[0]?.m,
                        ),
                      )
                        ? 'compare-point compare-point-changed'
                        : 'compare-point'
                    }
                  >
                    <DataPoint
                      label="Pathological TNM"
                      value={formatStage(
                        activeObservation?.pathological_stagings[0]?.t,
                        activeObservation?.pathological_stagings[0]?.n,
                        activeObservation?.pathological_stagings[0]?.m,
                      )}
                    />
                  </div>
                  <div
                    className={
                      hasChanged(
                        activeObservation?.treatment_cycles.length,
                        compareObservation?.treatment_cycles.length,
                      )
                        ? 'compare-point compare-point-changed'
                        : 'compare-point'
                    }
                  >
                    <DataPoint
                      label="Treatment cycles"
                      value={activeObservation?.treatment_cycles.length ?? 0}
                    />
                  </div>
                  <div
                    className={
                      hasChanged(
                        activeObservation?.radiotherapy_schedules.length,
                        compareObservation?.radiotherapy_schedules.length,
                      )
                        ? 'compare-point compare-point-changed'
                        : 'compare-point'
                    }
                  >
                    <DataPoint
                      label="Radiotherapy schedules"
                      value={activeObservation?.radiotherapy_schedules.length ?? 0}
                    />
                  </div>
                  <div
                    className={
                      hasChanged(
                        activeObservation?.surgeries.length,
                        compareObservation?.surgeries.length,
                      )
                        ? 'compare-point compare-point-changed'
                        : 'compare-point'
                    }
                  >
                    <DataPoint
                      label="Surgeries"
                      value={activeObservation?.surgeries.length ?? 0}
                    />
                  </div>
                  <div
                    className={
                      hasChanged(
                        joinValues(activeObservation?.cancer_markers.map((item) => compactJoin([item.name, item.value])) ?? []),
                        joinValues(compareObservation?.cancer_markers.map((item) => compactJoin([item.name, item.value])) ?? []),
                      )
                        ? 'compare-point compare-point-changed'
                        : 'compare-point'
                    }
                  >
                    <DataPoint
                      label="Cancer markers"
                      value={joinValues(
                        activeObservation?.cancer_markers.map((item) =>
                          compactJoin([item.name, item.value, item.unit]),
                        ) ?? [],
                      )}
                    />
                  </div>
                  <div
                    className={
                      hasChanged(
                        joinValues(activeObservation?.histopathologies.map((item) => item.detail) ?? []),
                        joinValues(compareObservation?.histopathologies.map((item) => item.detail) ?? []),
                      )
                        ? 'compare-point compare-point-changed'
                        : 'compare-point'
                    }
                  >
                    <DataPoint
                      label="Histopathology"
                      value={joinValues(
                        activeObservation?.histopathologies.map((item) => item.detail) ?? [],
                      )}
                    />
                  </div>
                </div>
              </article>
              <article className="compare-card">
                <div className="compare-card-head">
                  <p className="timeline-title">Comparison observation</p>
                  <span className={compareObservation?.is_draft ? 'status-pill status-draft' : 'status-pill status-live'}>
                    {compareObservation?.is_draft ? 'Draft' : 'Published'}
                  </span>
                </div>
                <div className="detail-grid">
                  <div className={hasChanged(compareObservation?.observed_at, activeObservation?.observed_at) ? 'compare-point compare-point-changed' : 'compare-point'}>
                    <DataPoint label="Observed at" value={formatDateTime(compareObservation?.observed_at)} />
                  </div>
                  <div className={hasChanged(compareObservation?.consulting_doctor_name, activeObservation?.consulting_doctor_name) ? 'compare-point compare-point-changed' : 'compare-point'}>
                    <DataPoint label="Doctor" value={compareObservation?.consulting_doctor_name} />
                  </div>
                  <div className={hasChanged(compareObservation?.center_name, activeObservation?.center_name) ? 'compare-point compare-point-changed' : 'compare-point'}>
                    <DataPoint label="Center" value={compareObservation?.center_name} />
                  </div>
                  <div className={hasChanged(compareObservation?.diagnosis_disease_group, activeObservation?.diagnosis_disease_group) ? 'compare-point compare-point-changed' : 'compare-point'}>
                    <DataPoint label="Disease group" value={compareObservation?.diagnosis_disease_group} />
                  </div>
                  <div className={hasChanged(compareObservation?.diagnosis_primary_site, activeObservation?.diagnosis_primary_site) ? 'compare-point compare-point-changed' : 'compare-point'}>
                    <DataPoint label="Primary site" value={compareObservation?.diagnosis_primary_site} />
                  </div>
                  <div className={hasChanged(compareObservation?.diagnosis_laterality, activeObservation?.diagnosis_laterality) ? 'compare-point compare-point-changed' : 'compare-point'}>
                    <DataPoint label="Laterality" value={compareObservation?.diagnosis_laterality} />
                  </div>
                  <div className={hasChanged(compareObservation?.grade, activeObservation?.grade) ? 'compare-point compare-point-changed' : 'compare-point'}>
                    <DataPoint label="Grade" value={compareObservation?.grade} />
                  </div>
                  <div
                    className={
                      hasChanged(
                        joinValues(compareObservation?.metastatic_sites.map((item) => item.value) ?? []),
                        joinValues(activeObservation?.metastatic_sites.map((item) => item.value) ?? []),
                      )
                        ? 'compare-point compare-point-changed'
                        : 'compare-point'
                    }
                    >
                      <DataPoint
                        label="Metastatic sites"
                        value={joinValues(compareObservation?.metastatic_sites.map((item) => item.value) ?? [])}
                      />
                    </div>
                  <div
                    className={
                      hasChanged(
                        formatStage(
                          compareObservation?.clinical_stagings[0]?.t,
                          compareObservation?.clinical_stagings[0]?.n,
                          compareObservation?.clinical_stagings[0]?.m,
                        ),
                        formatStage(
                          activeObservation?.clinical_stagings[0]?.t,
                          activeObservation?.clinical_stagings[0]?.n,
                          activeObservation?.clinical_stagings[0]?.m,
                        ),
                      )
                        ? 'compare-point compare-point-changed'
                        : 'compare-point'
                    }
                  >
                    <DataPoint
                      label="Clinical TNM"
                      value={formatStage(
                        compareObservation?.clinical_stagings[0]?.t,
                        compareObservation?.clinical_stagings[0]?.n,
                        compareObservation?.clinical_stagings[0]?.m,
                      )}
                    />
                  </div>
                  <div
                    className={
                      hasChanged(
                        formatStage(
                          compareObservation?.pathological_stagings[0]?.t,
                          compareObservation?.pathological_stagings[0]?.n,
                          compareObservation?.pathological_stagings[0]?.m,
                        ),
                        formatStage(
                          activeObservation?.pathological_stagings[0]?.t,
                          activeObservation?.pathological_stagings[0]?.n,
                          activeObservation?.pathological_stagings[0]?.m,
                        ),
                      )
                        ? 'compare-point compare-point-changed'
                        : 'compare-point'
                    }
                  >
                    <DataPoint
                      label="Pathological TNM"
                      value={formatStage(
                        compareObservation?.pathological_stagings[0]?.t,
                        compareObservation?.pathological_stagings[0]?.n,
                        compareObservation?.pathological_stagings[0]?.m,
                      )}
                    />
                  </div>
                  <div
                    className={
                      hasChanged(
                        compareObservation?.treatment_cycles.length,
                        activeObservation?.treatment_cycles.length,
                      )
                        ? 'compare-point compare-point-changed'
                        : 'compare-point'
                    }
                  >
                    <DataPoint
                      label="Treatment cycles"
                      value={compareObservation?.treatment_cycles.length ?? 0}
                    />
                  </div>
                  <div
                    className={
                      hasChanged(
                        compareObservation?.radiotherapy_schedules.length,
                        activeObservation?.radiotherapy_schedules.length,
                      )
                        ? 'compare-point compare-point-changed'
                        : 'compare-point'
                    }
                  >
                    <DataPoint
                      label="Radiotherapy schedules"
                      value={compareObservation?.radiotherapy_schedules.length ?? 0}
                    />
                  </div>
                  <div
                    className={
                      hasChanged(
                        compareObservation?.surgeries.length,
                        activeObservation?.surgeries.length,
                      )
                        ? 'compare-point compare-point-changed'
                        : 'compare-point'
                    }
                  >
                    <DataPoint
                      label="Surgeries"
                      value={compareObservation?.surgeries.length ?? 0}
                    />
                  </div>
                  <div
                    className={
                      hasChanged(
                        joinValues(compareObservation?.cancer_markers.map((item) => compactJoin([item.name, item.value])) ?? []),
                        joinValues(activeObservation?.cancer_markers.map((item) => compactJoin([item.name, item.value])) ?? []),
                      )
                        ? 'compare-point compare-point-changed'
                        : 'compare-point'
                    }
                  >
                    <DataPoint
                      label="Cancer markers"
                      value={joinValues(
                        compareObservation?.cancer_markers.map((item) =>
                          compactJoin([item.name, item.value, item.unit]),
                        ) ?? [],
                      )}
                    />
                  </div>
                  <div
                    className={
                      hasChanged(
                        joinValues(compareObservation?.histopathologies.map((item) => item.detail) ?? []),
                        joinValues(activeObservation?.histopathologies.map((item) => item.detail) ?? []),
                      )
                        ? 'compare-point compare-point-changed'
                        : 'compare-point'
                    }
                  >
                    <DataPoint
                      label="Histopathology"
                      value={joinValues(
                        compareObservation?.histopathologies.map((item) => item.detail) ?? [],
                      )}
                    />
                  </div>
                </div>
              </article>
            </div>
          </>
        ) : (
          <EmptyState
            title="No observations available to compare"
            detail="Once observations are available under the current filters, you can compare any two visits here."
          />
        )}
      </section>

      <section className="insight-grid">
        <article className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Staging Record</p>
              <h3>Clinical and pathological TNM by visit</h3>
            </div>
          </div>
          <div className="stage-record-list">
            {stagingRecords.length ? (
              <div className="stage-record-table-wrap">
                <table className="stage-record-table">
                  <thead>
                    <tr>
                      <th scope="col">Date</th>
                      <th scope="col">Visit</th>
                      <th scope="col">Clinical TNM</th>
                      <th scope="col">Pathological TNM</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stagingRecords.map((record) => (
                      <tr
                        key={record.id}
                        tabIndex={0}
                        role="button"
                        onClick={() => selectObservation(filteredObservations.findIndex((observation) => observation.id === record.id))}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault()
                            selectObservation(filteredObservations.findIndex((observation) => observation.id === record.id))
                          }
                        }}
                      >
                        <td>{record.date}</td>
                        <td>{record.label}</td>
                        <td>{record.clinical || 'Not recorded'}</td>
                        <td>{record.pathological || 'Not recorded'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                title="No staging records available"
                detail="Clinical and pathological TNM values will appear here when they are recorded."
              />
            )}
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Treatment Progression</p>
              <h3>How intervention burden changes by visit</h3>
            </div>
          </div>
          <div className="chart-box">
            {treatmentTrend.length ? (
              <ClinicalChart option={{
                tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } }, legend: { bottom: 0 },
                grid: { left: 42, right: 18, top: 22, bottom: 46 },
                xAxis: { type: 'category', data: treatmentTrend.map((entry) => entry.label) }, yAxis: { type: 'value', minInterval: 1 },
                series: [
                  { name: 'Cycles', type: 'bar', data: treatmentTrend.map((entry) => entry.cycles), itemStyle: { color: '#0f9e8f', borderRadius: [7, 7, 0, 0] } },
                  { name: 'Radiotherapy', type: 'bar', data: treatmentTrend.map((entry) => entry.radiotherapy), itemStyle: { color: '#1677c8', borderRadius: [7, 7, 0, 0] } },
                  { name: 'Surgeries', type: 'bar', data: treatmentTrend.map((entry) => entry.surgeries), itemStyle: { color: '#f97316', borderRadius: [7, 7, 0, 0] } },
                ],
              }} />
            ) : (
              <EmptyState
                title="No treatment trend available"
                detail="Treatment progression will appear here when filtered observations include cycles, radiotherapy, or surgery."
              />
            )}
          </div>
        </article>
      </section>

      <section className="insight-grid">
        <article className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Clinical Course</p>
              <h3>Recorded care milestones</h3>
            </div>
          </div>
          <div className="chart-box">
            {clinicalCourse.length ? (
              <ClinicalChart option={{
                tooltip: {
                  trigger: 'item',
                  formatter: (params) => {
                    const point = Array.isArray(params) ? params[0] : params
                    const event = clinicalCourse[point.dataIndex]
                    return [`<strong>${event.label}</strong>`, event.category, formatDate(event.date), event.detail].filter(Boolean).join('<br/>')
                  },
                },
                grid: { left: 94, right: 20, top: 26, bottom: 46 },
                xAxis: {
                  type: 'category',
                  data: clinicalCourse.map((event) => formatDate(event.date)),
                  axisLabel: { fontSize: 10, rotate: 28, interval: 0 },
                  axisTick: { alignWithLabel: true },
                },
                yAxis: { type: 'category', data: ['Follow-up', 'Response', 'Treatment', 'Molecular', 'Pathology', 'Diagnosis'], axisLabel: { fontSize: 11 } },
                series: [{
                  type: 'scatter',
                  symbolSize: 16,
                  data: clinicalCourse.map((event, index) => ({
                    value: [index, ['Follow-up', 'Response', 'Treatment', 'Molecular', 'Pathology', 'Diagnosis'].indexOf(event.category)],
                    itemStyle: { color: { Diagnosis: '#8b5cf6', Pathology: '#f97316', Molecular: '#0ea5a4', Treatment: '#1677c8', Response: '#eab308', 'Follow-up': '#64748b' }[event.category] },
                  })),
                }],
              }} />
            ) : (
              <EmptyState title="No dated milestones available" detail="The clinical course will appear as soon as dated diagnosis, pathology, treatment, response, or observation records are entered." />
            )}
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Treatment Footprint</p>
              <h3>Cycle, radiotherapy, and surgery volume</h3>
            </div>
          </div>
          <div className="chart-box">
            <ClinicalChart option={{
              tooltip: { trigger: 'axis' }, grid: { left: 42, right: 18, top: 22, bottom: 34 },
              xAxis: { type: 'category', data: treatmentMix.map((entry) => entry.label) }, yAxis: { type: 'value', minInterval: 1 },
              series: [{ type: 'bar', data: treatmentMix.map((entry, index) => ({ value: entry.value, itemStyle: { color: metricPalette[index % metricPalette.length], borderRadius: [10, 10, 0, 0] } })) }],
            }} />
          </div>
        </article>
      </section>

      <section className="clinical-card-grid" aria-label="Clinical record">
        <ClinicalCard
          id="clinical-snapshot"
          eyebrow="Clinical snapshot"
          title="Selected observation"
          icon={<HeartPulse size={19} />}
          count={patient.observations.length}
          hasData={Boolean(activeObservation)}
          defaultOpen
          emptyMessage="This patient has no imported clinical observations yet."
        >
          {activeObservation ? (
          <div className="detail-grid">
            <DataPoint
              label="Observed at"
              value={formatDateTime(activeObservation.observed_at)}
            />
            <DataPoint
              label="Doctor"
              value={activeObservation.consulting_doctor_name}
            />
            <DataPoint label="Center" value={activeObservation.center_name} />
            <DataPoint label="Cancer type" value={activeObservation.cancer_type} />
            <DataPoint
              label="Disease group"
              value={activeObservation.diagnosis_disease_group}
            />
            <DataPoint
              label="Primary site"
              value={activeObservation.diagnosis_primary_site}
            />
            <DataPoint
              label="Laterality"
              value={activeObservation.diagnosis_laterality}
            />
            <DataPoint label="Grade" value={activeObservation.grade} />
          </div>
          ) : null}
        </ClinicalCard>

        <ClinicalCard
          id="demography"
          eyebrow="Demography"
          title="Core patient profile"
          icon={<UserRound size={19} />}
          count={[patient.phone, patient.date_of_birth, patient.district].filter(Boolean).length}
          hasData={Boolean(patient.phone || patient.email || patient.nid || patient.date_of_birth || patient.district)}
          emptyMessage="No demographic detail has been recorded for this patient."
        >
          <div className="detail-grid">
            <DataPoint label="Phone" value={patient.phone} />
            <DataPoint label="Email" value={patient.email} />
            <DataPoint label="NID" value={patient.nid} />
            <DataPoint label="Date of birth" value={formatDate(patient.date_of_birth)} />
            <DataPoint label="Blood group" value={patient.blood_group} />
            <DataPoint label="District" value={patient.district} />
            <DataPoint label="Area" value={patient.area} />
            <DataPoint label="Police station" value={patient.police_station} />
            <DataPoint
              label="Socio-economic status"
              value={patient.socio_economic_status}
            />
            <DataPoint label="Patient type" value={patient.patient_type} />
          </div>
        </ClinicalCard>

        <ClinicalCard
          id="response-outcomes"
          eyebrow="Response and outcomes"
          title="Treatment response assessment"
          icon={<Activity size={19} />}
          count={responseCycles.length}
          hasData={responseCycles.length > 0}
          emptyMessage="No disease progression, survival, RECIST, iRECIST, or pathological response assessment is recorded for this patient."
        >
          <div className="response-card-stack">
            {responseCycles.map((cycle, index) => (
              <TreatmentResponseCard key={cycle.id} cycle={cycle} index={index} />
            ))}
          </div>
        </ClinicalCard>

        <ClinicalCard
          id="diagnosis"
          eyebrow="Diagnosis"
          title="Disease framing"
          icon={<Activity size={19} />}
          count={(activeObservation?.diagnoses.length ?? 0) + (activeObservation?.metastatic_sites.length ?? 0)}
          hasData={Boolean(activeObservation?.diagnosis_disease_group || activeObservation?.diagnoses.length)}
          defaultOpen
          emptyMessage="No diagnosis is available for the selected observation."
        >
          {activeObservation ? (
            <div className="stack-grid stack-grid-compact">
              <div className="badge-row badge-row-compact">
                <DataBadge label="Group" value={activeObservation.diagnosis_disease_group} />
                <DataBadge label="Subgroup" value={activeObservation.diagnosis_subgroup} />
                <DataBadge label="Site" value={activeObservation.diagnosis_primary_site} />
                <DataBadge label="Diagnosis laterality" value={activeObservation.diagnosis_laterality} />
              </div>
              <ListPanel
                title="Diagnosis details"
                items={activeObservation.diagnoses.map((item) => item.detail)}
              />
              <ListPanel
                title="Metastatic sites"
                items={activeObservation.metastatic_sites.map((item) => item.value)}
              />
              <ListPanel
                title="Comorbidities"
                items={activeObservation.comorbidities.map((item) => item.detail)}
              />
            </div>
          ) : null}
        </ClinicalCard>

        <ClinicalCard
          id="staging"
          eyebrow="Staging"
          title="Clinical and pathological status"
          icon={<ClipboardList size={19} />}
          count={(activeClinicalStage ? 1 : 0) + (activePathologicalStage ? 1 : 0)}
          hasData={Boolean(activeClinicalStage || activePathologicalStage || activePathologicalDetail)}
          emptyMessage="No staging record is attached to this observation."
        >
          {activeObservation ? (
            <div className="detail-grid detail-grid-compact">
              <DataPoint
                label="Clinical TNM"
                value={formatStage(
                  activeClinicalStage?.t,
                  activeClinicalStage?.n,
                  activeClinicalStage?.m,
                )}
              />
              <DataPoint label="Clinical result" value={activeClinicalStage?.result} />
              <DataPoint
                label="Pathological TNM"
                value={formatStage(
                  activePathologicalStage?.t,
                  activePathologicalStage?.n,
                  activePathologicalStage?.m,
                )}
              />
              <DataPoint
                label="Pathological result"
                value={activePathologicalStage?.result}
              />
              <DataPoint label="LVSI" value={activePathologicalDetail?.lvsi} />
              <DataPoint label="PNI" value={activePathologicalDetail?.pni} />
              <DataPoint label="Margin" value={activePathologicalDetail?.margin} />
              <DataPoint label="Ki67" value={activePathologicalDetail?.ki67} />
            </div>
          ) : null}
        </ClinicalCard>

        <ClinicalCard
          id="pathology"
          eyebrow="Pathology"
          title="Histopathology and molecular workup"
          icon={<Dna size={19} />}
          count={(activeObservation?.histopathologies.length ?? 0) + (activeIhcPanel?.details.length ?? 0)}
          hasData={Boolean(activeObservation?.histopathologies.length || activeIhcPanel?.details.length)}
          emptyMessage="No pathology workup is available for this observation."
        >
          {activeObservation ? (
            <div className="stack-grid stack-grid-compact">
              <ListPanel
                title="Histopathology"
                items={activeObservation.histopathologies.map((item) =>
                  compactJoin([
                    item.detail,
                    item.site,
                    item.histology_type,
                    item.observed_on ? `Date: ${formatDate(item.observed_on)}` : null,
                  ]),
                )}
              />
              <ListPanel
                title="IHC panel"
                items={
                  activeIhcPanel?.details.map((item) =>
                    compactJoin([item.marker_type, item.value]),
                  ) ?? []
                }
              />
            </div>
          ) : null}
        </ClinicalCard>

        <ClinicalCard
          id="molecular-pathology"
          eyebrow="Molecular pathology"
          title="Gene and biomarker profile"
          icon={<Dna size={19} />}
          count={activeObservation?.molecular_pathologies.length ?? 0}
          hasData={Boolean(activeMolecularResults.length || molecularHistoryGroups.length)}
          emptyMessage="No molecular pathology result is available for this patient."
        >
          <div className="stack-grid stack-grid-compact">
            <div className="molecular-observation-context">
              {activeObservation?.molecular_pathologies.length ? (
                <ListPanel
                  title="Results recorded with this observation"
                  items={
                    activeObservation.molecular_pathologies.map((item) =>
                      compactJoin([
                        item.method,
                        item.gene,
                        item.exon,
                        item.specimen,
                        item.status,
                        item.observed_on ? `Test date: ${formatDate(item.observed_on)}` : null,
                      ]),
                    )
                  }
                />
              ) : (
                <div className="list-panel">
                  <p className="list-panel-title">Results recorded with this observation</p>
                  <p className="molecular-empty-note">No molecular result was entered with this observation.</p>
                </div>
              )}
              <p className="molecular-context-note">
                Recorded with Obs {activeObservation?.legacy_id ?? activeObservation?.id ?? 'not selected'} on {formatDate(activeObservation?.observed_at)}. Test dates describe when the molecular assay was performed.
              </p>
            </div>
            {activeMolecularResults.length ? (
              <div className="molecular-chart">
                <p className="list-panel-title">Molecular test result matrix</p>
                <ClinicalChart height={210} option={{
                  tooltip: {
                    trigger: 'item',
                    formatter: (params) => {
                      const point = Array.isArray(params) ? params[0] : params
                      const result = activeMolecularResults[point.dataIndex]
                      return [
                        `<strong>${result.label}</strong>`,
                        result.category.label,
                        result.detail,
                        result.observedOn ? `Date: ${result.observedOn}` : '',
                      ].filter(Boolean).join('<br/>')
                    },
                  },
                  grid: { left: 18, right: 18, top: 34, bottom: 48 },
                  xAxis: {
                    type: 'category',
                    data: activeMolecularResults.map((entry) => entry.label),
                    axisLabel: { fontSize: 11, interval: 0 },
                    axisTick: { show: false },
                    axisLine: { show: false },
                  },
                  yAxis: { type: 'category', data: ['Result'], show: false },
                  visualMap: {
                    type: 'piecewise',
                    orient: 'horizontal',
                    left: 'center',
                    bottom: 0,
                    itemWidth: 12,
                    itemHeight: 12,
                    textStyle: { fontSize: 11 },
                    pieces: [
                      { value: 0, label: 'Detected / positive', color: '#f59e0b' },
                      { value: 1, label: 'Negative / not detected', color: '#64748b' },
                      { value: 2, label: 'Result recorded', color: '#38bdf8' },
                    ],
                  },
                  series: [{
                    type: 'heatmap',
                    data: activeMolecularResults.map((entry, index) => [
                      index,
                      0,
                      entry.category.label === 'Detected / positive' ? 0 : entry.category.label === 'Negative / not detected' ? 1 : 2,
                    ]),
                    label: { show: true, formatter: (params: { dataIndex: number }) => activeMolecularResults[params.dataIndex].category.label.replace(' / ', '\n/ '), fontSize: 11 },
                    itemStyle: { borderColor: 'transparent', borderRadius: 10 },
                  }],
                }} />
              </div>
            ) : null}
          </div>
          {molecularHistoryGroups.length ? (
            <section className="molecular-history" aria-label="Patient-wide molecular test history">
              <div className="molecular-history-heading">
                <div>
                  <p className="list-panel-title">Patient-wide molecular test history</p>
                  <p>Matching results are grouped without deleting their original observation records.</p>
                </div>
                <span className="result-chip">{molecularHistoryGroups.length} unique result groups</span>
              </div>
              <div className="molecular-history-list">
                {molecularHistoryGroups.map((group) => (
                  <article className="molecular-history-item" key={`${group.testDate}-${group.summary}`}>
                    <strong>{group.summary}</strong>
                    <span>Test date: {formatDate(group.testDate)}</span>
                    <small>
                      {group.recordCount === 1
                        ? `Recorded with ${group.observations[0].label}`
                        : `Recorded ${group.recordCount} times across ${group.observations.map((observation) => observation.label).join(', ')}`}
                    </small>
                  </article>
                ))}
              </div>
            </section>
          ) : null}
        </ClinicalCard>

        <ClinicalCard
          id="treatment"
          eyebrow="Treatment"
          title="Treatment footprint"
          icon={<HeartPulse size={19} />}
          count={patientTreatmentCycles.length + patientRadiotherapySchedules.length + patientSurgeries.length}
          hasData={Boolean(patientTreatmentCycles.length || patientRadiotherapySchedules.length || patientSurgeries.length)}
          emptyMessage="No treatment records are available for this patient."
        >
          {patientTreatmentCycles.length || patientRadiotherapySchedules.length || patientSurgeries.length ? (
            <div className="stack-grid stack-grid-compact">
              <ListPanel
                title="Treatment cycles"
                items={patientTreatmentCycles.map((cycle) => {
                  const protocolCycle = cycle.chemotherapy_protocols
                    .map((protocol) => protocol.cycle_no)
                    .find((value) => value !== null && value !== undefined)
                  const cycleNumber = protocolCycle ?? cycle.chemo_cycle_no
                  return compactJoin([
                    joinValues(cycle.chemotherapy_modalities.map((modality) => modality.detail)),
                    cycle.current_chemo_protocol,
                    cycleNumber !== null && cycleNumber !== undefined && cycleNumber !== ''
                      ? `Cycle ${String(cycleNumber).replace(/\.00$/, '')}`
                      : null,
                    cycle.line_of_treatment,
                    cycle.chemo_starting_date ? `Started ${formatDate(cycle.chemo_starting_date)}` : null,
                  ])
                })}
              />
              <ListPanel
                title="Radiotherapy schedules"
                items={patientRadiotherapySchedules.map((schedule) =>
                  compactJoin([
                    joinValues(schedule.sites.map((item) => item.value)),
                    joinValues(schedule.modalities.map((item) => item.value)),
                    schedule.intent,
                    schedule.total_dose ? `${schedule.total_dose} cGy` : null,
                  ]),
                )}
              />
              <ListPanel
                title="Surgeries"
                items={patientSurgeries.map((surgery) =>
                  compactJoin([
                    surgery.modality,
                    formatDate(surgery.surgery_date),
                    joinValues(surgery.lateralities.map((item) => item.value)),
                  ]),
                )}
              />
            </div>
          ) : null}
        </ClinicalCard>
      </section>

      <section className="panel" id="marker-trend">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Cancer markers</p>
            <h3>
              {markerSeries.length
                ? 'Marker-specific longitudinal trends'
                : 'Baseline marker profile'}
            </h3>
          </div>
        </div>
        <p className="entry-inline-note">
          {markerSeries.length
            ? 'Each chart represents one marker and one unit.'
            : 'These bars show the selected observation only and are separated by unit. They are not a treatment-response trend.'}
        </p>
        {markerSeries.length ? (
          <div className="marker-chart-grid">
            {markerSeries.map((series) => (
              <div key={`${series.name}-${series.unit}`} className="chart-box marker-chart-box">
                <p className="list-panel-title">{series.name}{series.unit ? ` (${series.unit})` : ''}</p>
                <ClinicalChart height={250} option={{
                  tooltip: { trigger: 'axis', valueFormatter: (value) => `${value} ${series.unit}` },
                  grid: { left: 46, right: 16, top: 16, bottom: 34 },
                  xAxis: { type: 'category', data: series.points.map((point) => point.label) }, yAxis: { type: 'value' },
                  series: [{ name: series.name, type: 'line', smooth: true, data: series.points.map((point) => point.value), symbolSize: 8, lineStyle: { color: '#16c7b0', width: 3 }, itemStyle: { color: '#16c7b0' } }],
                }} />
              </div>
            ))}
          </div>
        ) : markerBaselineGroups.length ? (
          <div className="marker-chart-grid">
            {markerBaselineGroups.map((group) => (
              <div key={group.unit} className="chart-box marker-chart-box">
                <p className="list-panel-title">Baseline values ({group.unit})</p>
                <ClinicalChart height={250} option={{
                  tooltip: { trigger: 'axis', valueFormatter: (value) => `${value} ${group.unit}` },
                  grid: { left: 46, right: 16, top: 16, bottom: 34 },
                  xAxis: { type: 'category', data: group.readings.map((reading) => reading.label) }, yAxis: { type: 'value' },
                  series: [{ name: 'Baseline value', type: 'bar', data: group.readings.map((reading) => reading.value), itemStyle: { color: '#20b8ff', borderRadius: [7, 7, 0, 0] } }],
                }} />
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No marker data recorded"
            detail="Marker values will appear here when they are added to an observation."
          />
        )}
      </section>

      <section className="panel panel-compact" id="observation-timeline">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Observation Timeline</p>
            <h3>Filtered observations</h3>
          </div>
        </div>
        <div className="timeline-list timeline-list-compact">
          {filteredObservations.map((observation) => (
            <article key={observation.id} className="timeline-card timeline-card-compact">
              <div className="timeline-head">
                <div>
                  <p className="timeline-title">
                    {observation.diagnosis_disease_group ||
                      observation.cancer_type ||
                      'Clinical observation'}
                  </p>
                  <p className="timeline-subtitle">
                    {formatDateTime(observation.observed_at)}
                    {observation.center_name ? ` | ${observation.center_name}` : ''}
                  </p>
                </div>
                <span
                  className={
                    observation.is_draft
                      ? 'status-pill status-draft'
                      : 'status-pill status-live'
                  }
                >
                  {observation.is_draft ? 'Draft' : 'Published'}
                </span>
              </div>
              <div className="timeline-grid timeline-grid-compact">
                <DataPoint
                  label="Primary site"
                  value={observation.diagnosis_primary_site}
                />
                <DataPoint
                  label="Diagnosis laterality"
                  value={observation.diagnosis_laterality}
                />
                <DataPoint
                  label="Subgroup"
                  value={observation.diagnosis_subgroup}
                />
                <DataPoint
                  label="Metastatic sites"
                  value={joinValues(
                    observation.metastatic_sites.map((item) => item.value),
                  )}
                />
                <DataPoint
                  label="Comorbidities"
                  value={joinValues(
                    observation.comorbidities.map((item) => item.detail),
                  )}
                />
                <DataPoint
                  label="Histopathology"
                  value={joinValues(
                    observation.histopathologies.map((item) => item.detail),
                  )}
                />
                <DataPoint
                  label="Histopathology date"
                  value={joinValues(
                    observation.histopathologies.map((item) =>
                      item.observed_on ? formatDate(item.observed_on) : null,
                    ),
                  )}
                />
                <DataPoint
                  label="Molecular pathology"
                  value={joinValues(
                    observation.molecular_pathologies.map(
                      (item) => item.status || item.gene,
                    ),
                  )}
                />
                <DataPoint
                  label="Molecular pathology date"
                  value={joinValues(
                    observation.molecular_pathologies.map((item) =>
                      item.observed_on ? formatDate(item.observed_on) : null,
                    ),
                  )}
                />
              </div>
              <div className="timeline-actions">
                {patient.can_edit && observation.can_edit ? (
                  <Link
                    className="secondary-button"
                    to={`/patients/${patient.registry_id}/edit`}
                  >
                    Edit
                  </Link>
                ) : null}
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() =>
                    focusObservation(
                      filteredObservations.findIndex((item) => item.id === observation.id),
                    )
                  }
                >
                  Focus
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </section>
  )
}
