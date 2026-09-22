import type { ClinicalObservation } from '../api'

export const metricPalette = ['#0f4c81', '#f97316', '#0ea5a4', '#164e63']

export function buildObservationTrend(observations: ClinicalObservation[]) {
  const map = new Map<string, number>()

  observations.forEach((observation) => {
    const key = observation.observed_at
      ? new Date(observation.observed_at).getFullYear().toString()
      : 'Unknown'
    map.set(key, (map.get(key) ?? 0) + 1)
  })

  return [...map.entries()].map(([label, count]) => ({ label, count }))
}

export function buildTreatmentMix(observations: ClinicalObservation[]) {
  const cycles = observations.reduce(
    (sum, observation) => sum + observation.treatment_cycles.length,
    0,
  )
  const radiotherapy = observations.reduce(
    (sum, observation) => sum + observation.radiotherapy_schedules.length,
    0,
  )
  const surgeries = observations.reduce(
    (sum, observation) => sum + observation.surgeries.length,
    0,
  )

  return [
    { label: 'Treatment cycles', value: cycles },
    { label: 'Radiotherapy', value: radiotherapy },
    { label: 'Surgeries', value: surgeries },
  ]
}

export function buildMarkerSeries(observations: ClinicalObservation[]) {
  const seriesByMarker = new Map<
    string,
    { name: string; unit: string; points: Array<{ label: string; value: number; date: string }> }
  >()

  observations.forEach((observation) => {
    observation.cancer_markers.forEach((marker) => {
      const value = Number(marker.value)
      const date = marker.observed_on || observation.observed_at
      if (!marker.name || !date || !Number.isFinite(value)) {
        return
      }
      const unit = marker.unit || ''
      const key = `${marker.name}::${unit}`
      const series = seriesByMarker.get(key) ?? { name: marker.name, unit, points: [] }
      series.points.push({ label: formatDate(date), value, date })
      seriesByMarker.set(key, series)
    })
  })

  return [...seriesByMarker.values()]
    .map((series) => ({
      ...series,
      points: series.points.sort((left, right) => left.date.localeCompare(right.date)),
    }))
    .filter((series) => series.points.length >= 2)
}

export function joinValues(values: Array<string | null | undefined>) {
  const cleanValues = values.filter(Boolean)
  return cleanValues.length ? cleanValues.join(', ') : ''
}

export function compactJoin(values: Array<string | null | undefined>) {
  const cleanValues = values.filter(Boolean)
  return cleanValues.length ? cleanValues.join(' | ') : null
}

export function formatMeasure(value?: string | number | null, unit?: string) {
  if (value === null || value === undefined || value === '') {
    return ''
  }

  return unit ? `${value} ${unit}` : String(value)
}

export function formatStage(
  t?: string | null,
  n?: string | null,
  m?: string | null,
) {
  const parts = [t, n, m].filter(Boolean)
  return parts.length ? parts.join(' / ') : ''
}

export function formatDate(value?: string | null) {
  if (!value) {
    return ''
  }

  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(value))
}

export function formatDateTime(value?: string | null) {
  if (!value) {
    return ''
  }

  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(value))
}
