// LEGACY_UI: this screen targets the retired entries analytics API.
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState, type ReactNode } from 'react'
import { BarChart3, Download, FileDown, Filter, ShieldCheck } from 'lucide-react'
import type { EChartsOption } from 'echarts'
import {
  buildAnalyticsExportUrl,
  fetchAnalyticsDistributions,
  fetchAnalyticsFacet,
  fetchAnalyticsFilters,
  fetchAnalyticsMolecularChronology,
  fetchAnalyticsMolecularResultBreakdown,
  fetchAnalyticsMolecularSummary,
  fetchAnalyticsPatientMatches,
  fetchAnalyticsSummary,
  fetchAnalyticsSurvival,
  type AnalyticsPatientMatches,
} from '../api'
import { ClinicalChart } from '../components/ClinicalChart'
import { LoadingState } from '../components/registry-ui'

type Filters = Record<string, string>
type ChartType = 'bar' | 'donut' | 'table'
type PaletteMode = 'standard' | 'colorful' | 'tropical' | 'aurora'
type DistributionItem = { label: string; count: number }
const clinicalPalette = ['#0f766e', '#168aa2', '#3f74ad', '#5e6f91', '#7c6a9f', '#4f8b72', '#a77a45', '#b25b70', '#8b9650', '#4b8891', '#7288a9', '#8b7697']
const DAYS_PER_AVERAGE_MONTH = 30.4375
const chartPalettes: Record<PaletteMode, string[]> = {
  standard: clinicalPalette,
  colorful: ['#2563eb', '#db2777', '#f97316', '#16a34a', '#7c3aed', '#0891b2', '#eab308', '#dc2626', '#14b8a6', '#9333ea', '#f43f5e', '#65a30d'],
  tropical: ['#00b8a9', '#24a8f2', '#8b5cf6', '#f54291', '#ff7a45', '#fbc531', '#a3d65c', '#24d4a8', '#2f80ed', '#ff5e7d', '#ef4444', '#c084fc'],
  aurora: ['#00e5ff', '#00b0ff', '#2979ff', '#651fff', '#aa00ff', '#d500f9', '#ff0080', '#ff1744', '#ff6d00', '#ffd600', '#aeea00', '#00e676'],
}
const paletteLabels: Record<PaletteMode, string> = { standard: 'Standard', colorful: 'Colorful', tropical: 'Tropical', aurora: 'Aurora' }
const initialFilters: Filters = { start_date: '', end_date: '', center: '', doctor: '', diagnosis: '', stage: '', biomarker: '', treatment: '', regimen: '', outcome: '' }
const labels: Record<string, string> = { total_patients: 'Total patients', observation_count: 'Included observations', new_diagnoses: 'Recorded diagnoses', active_treatment: 'Active treatment', recorded_response: 'Recorded response', response_rate: 'Response rate', pfs_available: 'PFS available', os_available: 'OS available' }
const formatMedianDays = (value: number | null) => value === null ? '—' : Number.isInteger(value) ? String(value) : value.toFixed(1)
const analyticsQueryDefaults = { staleTime: 60_000, gcTime: 5 * 60_000, refetchOnWindowFocus: false }

function RegimenFilter({ value, options, onChange }: { value: string; options: string[]; onChange: (value: string) => void }) {
  const [open, setOpen] = useState(false)
  const matches = useMemo(() => {
    const query = value.trim().toLocaleLowerCase()
    return query ? options.filter((option) => option.toLocaleLowerCase().includes(query)) : options
  }, [options, value])

  return <div className="analytics-filter analytics-regimen-filter">
    <span>Regimen / protocol</span>
    <div className="analytics-combobox">
      <input
        type="search"
        value={value}
        placeholder="Choose or search regimen"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={open}
        aria-controls="regimen-options"
        onFocus={() => setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 120)}
        onKeyDown={(event) => {
          if (event.key === 'Escape') setOpen(false)
        }}
        onChange={(event) => {
          onChange(event.target.value)
          setOpen(true)
        }}
      />
      {open ? <div id="regimen-options" className="analytics-combobox-options" role="listbox">
        <button type="button" role="option" aria-selected={!value} onMouseDown={(event) => event.preventDefault()} onClick={() => { onChange(''); setOpen(false) }}>All regimens</button>
        {matches.length ? matches.map((option) => <button key={option} type="button" role="option" aria-selected={value === option} title={option} onMouseDown={(event) => event.preventDefault()} onClick={() => { onChange(option); setOpen(false) }}>{option}</button>) : <p>No matching regimen</p>}
      </div> : null}
    </div>
  </div>
}

function downloadDistributionCsv(title: string, items: DistributionItem[], total: number) {
  const rows = [['Category', 'Patients', 'Share'], ...items.map((item) => [item.label, String(item.count), total ? `${(item.count / total * 100).toFixed(1)}%` : ''])]
  const csv = rows.map((row) => row.map((value) => `"${value.replace(/"/g, '""')}"`).join(',')).join('\n')
  const link = document.createElement('a')
  link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  link.download = `${title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.csv`
  link.click()
  URL.revokeObjectURL(link.href)
}

function downloadPatientMatchesCsv(title: string, items: AnalyticsPatientMatches['items']) {
  const columns: Array<[string, string]> = [
    ['Registry ID', 'registry_id'], ['Patient', 'name'], ['Registration no.', 'registration_no'], ['Phone', 'phone'], ['Email', 'email'], ['Age', 'age'], ['Gender', 'gender'], ['District', 'district'],
    ['Matching records', 'matching_records'], ['Latest matching observation', 'latest_observation'], ['Diagnosis', 'diagnosis'], ['Primary site', 'primary_site'], ['Diagnosis subgroup', 'diagnosis_subgroup'], ['Diagnosis laterality', 'diagnosis_laterality'], ['Clinical stage', 'stage'], ['Pathological stage', 'pathological_stage'], ['Histopathology', 'pathology'], ['Tumor grade', 'grade'], ['Metastatic site', 'metastatic_site'],
    ['Biomarker / gene', 'biomarker'], ['Molecular result', 'molecular_status'], ['Molecular exon', 'molecular_exon'], ['Molecular method (latest)', 'molecular_method'], ['Molecular methods (all)', 'molecular_methods'], ['Molecular specimen', 'molecular_specimen'], ['Cancer marker', 'cancer_marker'],
    ['Treatment protocol', 'treatment'], ['Treatment line', 'treatment_line'], ['Treatment modality', 'treatment_modality'], ['Response', 'response'], ['Progression status', 'progression_status'], ['Survival status', 'survival_status'],
    ['Radiotherapy intent', 'radiotherapy_intent'], ['Radiotherapy site', 'radiotherapy_site'], ['Radiotherapy modality', 'radiotherapy_modality'], ['Surgery modality', 'surgery_modality'], ['Surgery laterality', 'surgery_laterality'], ['Smoking status', 'smoking_status'], ['Comorbidity', 'comorbidity'],
    ['Diagnosis date', 'diagnosis_date'], ['Treatment start', 'treatment_start'], ['Progression date', 'progression_date'], ['Death date', 'death_date'], ['Last follow-up', 'last_follow_up'],
  ]
  const rows = [columns.map(([label]) => label), ...items.map((item) => columns.map(([, key]) => String(item[key as keyof typeof item] ?? '')))]
  const csv = rows.map((row) => row.map((value) => `"${value.replace(/"/g, '""')}"`).join(',')).join('\n')
  const link = document.createElement('a')
  link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  link.download = `${title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-patients.csv`
  link.click()
  URL.revokeObjectURL(link.href)
}

type PatientMatch = AnalyticsPatientMatches['items'][number]
type PatientMatchSortKey = 'registry_id' | 'name' | 'registration_no' | 'matching_records' | 'latest_observation'

function PatientTraceabilityTable({ items }: { items: PatientMatch[] }) {
  const [sortKey, setSortKey] = useState<PatientMatchSortKey>('registry_id')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
  const [page, setPage] = useState(1)
  const pageSize = 10
  const sortedItems = useMemo(() => [...items].sort((left, right) => {
    const leftValue = left[sortKey] ?? ''
    const rightValue = right[sortKey] ?? ''
    const comparison = typeof leftValue === 'number' && typeof rightValue === 'number'
      ? leftValue - rightValue
      : String(leftValue).localeCompare(String(rightValue), undefined, { numeric: true, sensitivity: 'base' })
    return sortDirection === 'asc' ? comparison : -comparison
  }), [items, sortDirection, sortKey])
  const totalPages = Math.max(1, Math.ceil(sortedItems.length / pageSize))
  const currentPage = Math.min(page, totalPages)
  const pageItems = sortedItems.slice((currentPage - 1) * pageSize, currentPage * pageSize)
  const changeSort = (key: PatientMatchSortKey) => {
    setPage(1)
    if (key === sortKey) setSortDirection(current => current === 'asc' ? 'desc' : 'asc')
    else {
      setSortKey(key)
      setSortDirection('asc')
    }
  }
  const heading = (label: string, key: PatientMatchSortKey) => <button type="button" className="analytics-sort-header" onClick={() => changeSort(key)} aria-sort={sortKey === key ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}>{label}{sortKey === key ? (sortDirection === 'asc' ? ' ▲' : ' ▼') : ''}</button>

  return <>
    <div className="analytics-table-wrap"><table className="registry-table"><thead><tr><th>{heading('Registry ID', 'registry_id')}</th><th>{heading('Patient', 'name')}</th><th>{heading('Registration no.', 'registration_no')}</th><th>{heading('Matching records', 'matching_records')}</th><th>{heading('Latest matching observation', 'latest_observation')}</th><th /></tr></thead><tbody>{pageItems.map(item => <tr key={item.registry_id}><td>{item.registry_id || '—'}</td><td>{item.name}</td><td>{item.registration_no || '—'}</td><td>{item.matching_records}</td><td>{item.latest_observation ? new Date(item.latest_observation).toLocaleDateString() : '—'}</td><td>{item.registry_id ? <a href={`/patients/${item.registry_id}`}>Open patient</a> : '—'}</td></tr>)}</tbody></table></div>
    <div className="pagination-row analytics-drilldown-pagination"><button type="button" className="pager-button" disabled={currentPage === 1} onClick={() => setPage(current => Math.max(1, current - 1))}>Previous</button><span className="pagination-label">{sortedItems.length ? `${(currentPage - 1) * pageSize + 1}-${Math.min(currentPage * pageSize, sortedItems.length)} of ${sortedItems.length}` : '0 records'}</span><button type="button" className="pager-button" disabled={currentPage === totalPages} onClick={() => setPage(current => Math.min(totalPages, current + 1))}>Next</button></div>
  </>
}

function DistributionChart({
  title,
  items,
  defaultChartType = 'bar',
  horizontal = false,
  defaultTopN = 0,
  supportsMissing = true,
  facetFilters,
  paletteMode,
}: {
  title: string
  items: DistributionItem[]
  defaultChartType?: ChartType
  horizontal?: boolean
  defaultTopN?: number
  supportsMissing?: boolean
  facetFilters?: ReactNode
  paletteMode: PaletteMode
}) {
  const [chartType, setChartType] = useState<ChartType>(defaultChartType)
  const [includeMissing, setIncludeMissing] = useState(false)
  const [topN, setTopN] = useState(defaultTopN)
  const usableItems = useMemo(
    () => items.filter((item) => includeMissing || item.label !== 'Not recorded'),
    [includeMissing, items],
  )
  const displayItems = useMemo(() => {
    if (!topN || usableItems.length <= topN) return usableItems
    const topItems = usableItems.slice(0, topN)
    const otherCount = usableItems.slice(topN).reduce((total, item) => total + item.count, 0)
    return otherCount ? [...topItems, { label: 'Other', count: otherCount }] : topItems
  }, [topN, usableItems])
  const total = displayItems.reduce((sum, item) => sum + item.count, 0)
  const labels = displayItems.map((item) => item.label)
  const values = displayItems.map((item) => item.count)
  const palette = chartPalettes[paletteMode]
  const usesMulticolorBars = paletteMode !== 'standard'
  const barData = usesMulticolorBars
    ? displayItems.map((item, index) => ({ value: item.count, itemStyle: { color: palette[index % palette.length] } }))
    : values
  const barItemStyle = usesMulticolorBars
    ? { borderRadius: [0, 6, 6, 0] }
    : { color: '#0f766e', borderRadius: [0, 6, 6, 0] }
  const verticalBarItemStyle = usesMulticolorBars
    ? { borderRadius: [6, 6, 0, 0] }
    : { color: '#0f766e', borderRadius: [6, 6, 0, 0] }
  const option: EChartsOption = chartType === 'donut'
    ? {
      color: palette,
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { type: 'scroll', bottom: 0, textStyle: { fontSize: 10 } },
      series: [{
        type: 'pie',
        radius: ['42%', '70%'],
        center: ['50%', '42%'],
        label: { show: true, formatter: '{b}: {c}', fontSize: 10, overflow: 'truncate', width: 86 },
        labelLine: { length: 9, length2: 8 },
        labelLayout: { hideOverlap: true },
        data: displayItems.map((item) => ({ name: item.label, value: item.count })),
        itemStyle: { borderRadius: 4, borderColor: 'transparent', borderWidth: 2 },
      }],
    }
    : horizontal
      ? {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        grid: { left: 118, right: 22, top: 16, bottom: 18 },
        xAxis: { type: 'value', minInterval: 1 },
        yAxis: { type: 'category', data: labels, inverse: true, axisLabel: { fontSize: 10, width: 102, overflow: 'truncate' } },
        series: [{ type: 'bar', data: barData, label: { show: true, position: 'right', fontSize: 10 }, itemStyle: barItemStyle }],
      }
      : {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        grid: { left: 42, right: 20, top: 18, bottom: 70 },
        xAxis: { type: 'category', data: labels, axisLabel: { rotate: 35, fontSize: 10, interval: 0 } },
        yAxis: { type: 'value', minInterval: 1 },
        series: [{ type: 'bar', data: barData, label: { show: true, position: 'top', fontSize: 10 }, itemStyle: verticalBarItemStyle }],
      }

  return (
    <article className="panel analytics-chart">
      <div className="panel-heading analytics-chart-heading">
        <h3>{title}</h3>
        <div className="analytics-chart-controls">
          {facetFilters}
          <label>Chart
            <select value={chartType} onChange={(event) => setChartType(event.target.value as ChartType)}>
              <option value="bar">Bar</option>
              <option value="donut">Donut</option>
              <option value="table">Table</option>
            </select>
          </label>
          {items.length > 10 ? <label>Categories
            <select value={topN} onChange={(event) => setTopN(Number(event.target.value))}>
              <option value={0}>All</option>
              <option value={5}>Top 5</option>
              <option value={10}>Top 10</option>
            </select>
          </label> : null}
        </div>
      </div>
      {supportsMissing ? <label className="analytics-missing-toggle">
        <input type="checkbox" checked={includeMissing} onChange={(event) => setIncludeMissing(event.target.checked)} />
        Include not recorded
      </label> : null}
      {chartType === 'table' ? (
        <div className="analytics-distribution-table">
          <button className="analytics-table-download" type="button" onClick={() => downloadDistributionCsv(title, displayItems, total)}><FileDown size={14} /> Download CSV</button>
          <table className="registry-table"><thead><tr><th>Category</th><th>Patients</th><th>Share</th></tr></thead>
            <tbody>{displayItems.map((item) => <tr key={item.label}><td>{item.label}</td><td>{item.count}</td><td>{total ? `${(item.count / total * 100).toFixed(1)}%` : '—'}</td></tr>)}</tbody>
          </table>
        </div>
      ) : <ClinicalChart height={230} option={option} exportTitle={title} />}
    </article>
  )
}

function FacetedChart({ title, subject, filters, paletteMode, sectionFilters, showFacetFilters = true, horizontal = false, defaultChartType = 'bar', countMode = 'records' }: {
  title: string
  subject: string
  filters: Filters
  paletteMode: PaletteMode
  sectionFilters?: Filters
  showFacetFilters?: boolean
  horizontal?: boolean
  defaultChartType?: ChartType
  countMode?: 'records' | 'patients' | 'observations'
}) {
  const [localFilters, setLocalFilters] = useState<Filters>({})
  const queryFilters = { ...filters, ...(sectionFilters ?? localFilters) }
  const facetQuery = useQuery({ ...analyticsQueryDefaults, queryKey: ['analytics-facet', subject, queryFilters, countMode], queryFn: () => fetchAnalyticsFacet(subject, queryFilters, countMode) })
  const facetFilters = showFacetFilters ? <div className="analytics-facet-filters">{Object.entries(facetQuery.data?.filters ?? {}).map(([key, values]) => <label key={key}>{key.replace('_', ' ')}<select value={localFilters[key] ?? ''} onChange={event => setLocalFilters(current => ({ ...current, [key]: event.target.value }))}><option value="">All</option>{values.map(value => <option key={value} value={value}>{value}</option>)}</select></label>)}</div> : null
  return <div className="analytics-faceted-chart">{facetQuery.isLoading ? <LoadingState label="Loading chart" /> : <DistributionChart title={title} items={facetQuery.data?.items ?? []} horizontal={horizontal} defaultChartType={defaultChartType} defaultTopN={horizontal ? 10 : 0} supportsMissing={false} facetFilters={facetFilters} paletteMode={paletteMode} />}</div>
}

function MolecularSummaryCards({ filters }: { filters: Filters }) {
  const query = useQuery({ ...analyticsQueryDefaults, queryKey: ['analytics-molecular-summary', filters], queryFn: () => fetchAnalyticsMolecularSummary(filters) })
  const items = query.data ? [
    ['Patients tested', query.data.patients_tested],
    ['Test events', query.data.test_events],
    ['Gene-result entries', query.data.result_entries],
    ['Methods recorded', query.data.methods_recorded],
  ] : []
  return <div className="molecular-summary-wrap">{query.isLoading ? <LoadingState label="Loading molecular summary" /> : <><div className="molecular-summary-cards">{items.map(([label, value]) => <article className="molecular-summary-card" key={String(label)}><span>{label}</span><strong>{value}</strong></article>)}</div><p className="molecular-summary-note">{query.data?.definition}</p></>}</div>
}

function MolecularChronologyChart({ filters, paletteMode }: { filters: Filters; paletteMode: PaletteMode }) {
  const [countMode, setCountMode] = useState<'events' | 'patients' | 'entries'>('events')
  const query = useQuery({ ...analyticsQueryDefaults, queryKey: ['analytics-molecular-chronology', filters, countMode], queryFn: () => fetchAnalyticsMolecularChronology(filters, countMode) })
  const items = query.data?.items ?? []
  const option: EChartsOption = {
    color: [chartPalettes[paletteMode][0]],
    tooltip: { trigger: 'axis' },
    grid: { left: 42, right: 20, top: 18, bottom: 36 },
    xAxis: { type: 'category', data: items.map(item => item.label), axisLabel: { fontSize: 10, rotate: 35 } },
    yAxis: { type: 'value', minInterval: 1 },
    series: [{ type: 'line', smooth: true, symbolSize: 7, data: items.map(item => item.count), areaStyle: { opacity: .12 } }],
  }
  return <article className="panel analytics-chart"><div className="panel-heading analytics-chart-heading"><h3>Molecular testing chronology</h3><div className="analytics-chart-controls"><label>Count<select value={countMode} onChange={event => setCountMode(event.target.value as 'events' | 'patients' | 'entries')}><option value="events">Test events</option><option value="patients">Patients</option><option value="entries">Result entries</option></select></label></div></div>{query.isLoading ? <LoadingState label="Loading chronology" /> : <ClinicalChart height={230} option={option} exportTitle="Molecular testing chronology" />}</article>
}

function MolecularResultCrossTab({ filters }: { filters: Filters }) {
  const [countMode, setCountMode] = useState<'entries' | 'events' | 'patients'>('entries')
  const [tableOpen, setTableOpen] = useState(false)
  const query = useQuery({ ...analyticsQueryDefaults, queryKey: ['analytics-molecular-result-breakdown', filters, countMode], queryFn: () => fetchAnalyticsMolecularResultBreakdown(filters, countMode) })
  const rows = useMemo(() => {
    const grouped = new Map<string, Record<string, string | number>>()
    for (const item of query.data?.rows ?? []) {
      const key = `${item.method}\u0000${item.gene}`
      const row = grouped.get(key) ?? { method: item.method, gene: item.gene }
      row[item.status] = item.count
      grouped.set(key, row)
    }
    return [...grouped.values()]
  }, [query.data])
  const statuses = query.data?.statuses ?? []
  const chartOption: EChartsOption = {
    color: chartPalettes.colorful,
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { type: 'scroll', bottom: 0, textStyle: { fontSize: 10 } },
    grid: { left: 132, right: 26, top: 18, bottom: 46 },
    xAxis: { type: 'value', minInterval: 1 },
    yAxis: { type: 'category', inverse: true, data: rows.map(row => `${row.method} — ${row.gene}`), axisLabel: { fontSize: 10, width: 120, overflow: 'truncate' } },
    series: statuses.map(status => ({ type: 'bar', stack: 'results', name: status, data: rows.map(row => Number(row[status] ?? 0)), label: { show: true, position: 'inside', fontSize: 9, formatter: '{c}' } })),
  }
  return <article className="panel molecular-cross-tab"><div className="panel-heading analytics-chart-heading"><div><h3>Method × gene × result</h3><p className="molecular-cross-tab-note">Each stacked bar shows Positive, Negative, and other statuses for one method–gene combination.</p></div><div className="analytics-chart-controls"><label>Count<select value={countMode} onChange={event => setCountMode(event.target.value as 'entries' | 'events' | 'patients')}><option value="entries">Result entries</option><option value="events">Test events</option><option value="patients">Patients</option></select></label></div></div>{query.isLoading ? <LoadingState label="Loading molecular result breakdown" /> : <><ClinicalChart height={Math.max(280, rows.length * 34 + 74)} option={chartOption} exportTitle="Molecular method gene result breakdown" /><div className="molecular-cross-tab-toggle"><button className="secondary-button" type="button" aria-expanded={tableOpen} onClick={() => setTableOpen(current => !current)}>{tableOpen ? 'Hide exact table' : 'Show exact table'}</button><span>{rows.length} method–gene combinations</span></div>{tableOpen ? <div className="analytics-table-wrap"><table className="registry-table"><thead><tr><th>Method</th><th>Gene</th>{statuses.map(status => <th key={status}>{status}</th>)}</tr></thead><tbody>{rows.map(row => <tr key={`${row.method}-${row.gene}`}><td>{row.method}</td><td>{row.gene}</td>{statuses.map(status => <td key={status}>{row[status] ?? 0}</td>)}</tr>)}</tbody></table></div> : null}</>}</article>
}

function AnalyticsSection({ eyebrow, title, description, filterSubject, filters, onViewPatients, children }: {
  eyebrow: string
  title: string
  description: string
  filterSubject: string
  filters: Filters
  paletteMode?: PaletteMode
  onViewPatients?: (title: string, subject: string, sectionFilters: Filters) => void
  children: (sectionFilters: Filters) => ReactNode
}) {
  void onViewPatients
  const [sectionFilters, setSectionFilters] = useState<Filters>({})
  const [showPatients, setShowPatients] = useState(false)
  const filterQuery = useQuery({ ...analyticsQueryDefaults, queryKey: ['analytics-section-filters', filterSubject, filters], queryFn: () => fetchAnalyticsFacet(filterSubject, filters) })
  const patientsQuery = useQuery({ ...analyticsQueryDefaults, queryKey: ['analytics-section-patients', filterSubject, filters, sectionFilters], queryFn: () => fetchAnalyticsPatientMatches(filterSubject, { ...filters, ...sectionFilters }), enabled: showPatients })
  const filterControls = Object.entries(filterQuery.data?.filters ?? {}).map(([key, values]) => <label key={key}>{key.replace('_', ' ')}<select value={sectionFilters[key] ?? ''} onChange={event => setSectionFilters(current => ({ ...current, [key]: event.target.value }))}><option value="">All</option>{values.map(value => <option key={value} value={value}>{value}</option>)}</select></label>)
  return <section className="analytics-chart-section analytics-domain-section"><div className="analytics-section-heading"><div><p className="eyebrow">{eyebrow}</p><h3>{title}</h3></div><div className="analytics-section-tools"><p>{description}</p>{filterControls.length ? <div className="analytics-section-filters">{filterControls}</div> : null}<button className="analytics-review-button" type="button" onClick={() => setShowPatients(true)}>View matching patients</button></div></div><div className="analytics-chart-grid">{children(sectionFilters)}</div>{showPatients ? <section className="panel analytics-patient-drilldown"><div className="panel-heading"><div><p className="eyebrow">Patient traceability</p><h3>{title}</h3><p className="analytics-drilldown-scope">{patientsQuery.data?.scope ?? 'Finding matching patients...'}</p></div><div className="analytics-drilldown-actions">{patientsQuery.data ? <button className="secondary-button" type="button" onClick={() => downloadPatientMatchesCsv(title, patientsQuery.data.items)}><FileDown size={16} /> Download details</button> : null}<button className="secondary-button" type="button" onClick={() => setShowPatients(false)}>Close</button></div></div>{patientsQuery.isLoading ? <LoadingState label="Finding matching patients" /> : <><p className="analytics-drilldown-count">{patientsQuery.data?.count ?? 0} patient{patientsQuery.data?.count === 1 ? '' : 's'} found</p><PatientTraceabilityTable items={patientsQuery.data?.items ?? []} /></>}</section> : null}</section>
}

export default function AnalyticsPage() {
  const [filters, setFilters] = useState<Filters>(initialFilters)
  const [paletteMode, setPaletteMode] = useState<PaletteMode>('colorful')
  const [drilldown, setDrilldown] = useState<{ title: string; subject: string; filters: Filters } | null>(null)
  const filterQuery = useQuery({ ...analyticsQueryDefaults, queryKey: ['analytics-filters'], queryFn: () => fetchAnalyticsFilters() })
  const summaryQuery = useQuery({ ...analyticsQueryDefaults, queryKey: ['analytics-summary', filters], queryFn: () => fetchAnalyticsSummary(filters) })
  const distributionQuery = useQuery({ ...analyticsQueryDefaults, queryKey: ['analytics-distributions', filters], queryFn: () => fetchAnalyticsDistributions(filters) })
  const survivalQuery = useQuery({ ...analyticsQueryDefaults, queryKey: ['analytics-survival', filters], queryFn: () => fetchAnalyticsSurvival(filters) })
  const drilldownQuery = useQuery({ ...analyticsQueryDefaults, queryKey: ['analytics-patient-matches', drilldown], queryFn: () => fetchAnalyticsPatientMatches(drilldown?.subject ?? '', drilldown?.filters ?? filters), enabled: Boolean(drilldown) })
  const filterOptions = filterQuery.data
  const kpis = summaryQuery.data?.kpis ?? {}
  const survival = survivalQuery.data?.survival ?? []
  const completeness = useMemo(() => distributionQuery.data?.completeness ?? [], [distributionQuery.data])
  const change = (key: string, value: string) => setFilters(current => ({ ...current, [key]: value }))
  const viewPatients = (title: string, subject = '', sectionFilters: Filters = {}) => setDrilldown({ title, subject, filters: { ...filters, ...sectionFilters } })
  const select = (key: string, items: Array<{ value: string; label: string }>) => <label className="analytics-filter">{key.replace('_', ' ')}<select value={filters[key]} onChange={e => change(key, e.target.value)}><option value="">All</option>{items.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>

  return <section className="page-grid">
    <section className="hero-panel analytics-hero"><div className="hero-copy"><p className="eyebrow">Read-only analytics</p><h2>Clinical outcomes workspace</h2><p className="hero-text">Published clinical records only. Filters define one patient cohort; blank fields remain missing.</p></div><div className="analytics-hero-actions"><label className="analytics-palette-control">Chart palette<select value={paletteMode} onChange={event => setPaletteMode(event.target.value as PaletteMode)} aria-label="Chart color palette">{Object.entries(paletteLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><button className="secondary-button" type="button" onClick={() => viewPatients('Cohort patients')}><Filter size={16} /> View patients</button><a className="secondary-button" href={buildAnalyticsExportUrl(filters)}><Download size={16} /> Export safe CSV</a></div></section>
    <section className="panel analytics-filters"><div className="panel-heading"><div><p className="eyebrow">Cohort filters</p><h3><Filter size={17} /> Global selection</h3></div><button className="secondary-button" type="button" onClick={() => setFilters(initialFilters)}>Clear filters</button></div><div className="analytics-filter-grid">
      <label className="analytics-filter">From<input type="date" value={filters.start_date} onChange={e => change('start_date', e.target.value)} /></label>
      <label className="analytics-filter">To<input type="date" value={filters.end_date} onChange={e => change('end_date', e.target.value)} /></label>
      {select('center', (filterOptions?.centers ?? []).map(x => ({ value: String(x.center_id), label: x.center__name })))}
      {select('doctor', (filterOptions?.doctors ?? []).map(x => ({ value: String(x.doctor_id), label: x.doctor__name })))}
      {select('diagnosis', (filterOptions?.diagnoses ?? []).map(x => ({ value: x, label: x })))}
      {select('stage', (filterOptions?.stages ?? []).map(x => ({ value: x, label: x })))}
      {select('biomarker', (filterOptions?.biomarkers ?? []).map(x => ({ value: x, label: x })))}
      {select('treatment', (filterOptions?.treatments ?? []).map(x => ({ value: x, label: x })))}
      <RegimenFilter value={filters.regimen} options={filterOptions?.regimens ?? []} onChange={(value) => change('regimen', value)} />
      {select('outcome', [{ value: 'progressed', label: 'Progressed' }, { value: 'deceased', label: 'Deceased' }])}
    </div></section>
    {summaryQuery.isLoading ? <LoadingState label="Calculating cohort metrics" /> : <section className="analytics-kpis">{Object.entries(kpis).map(([key, value]) => <article className="metric-card" key={key}><span>{labels[key]}</span><strong>{key === 'response_rate' && value !== null ? `${value}%` : value ?? '—'}</strong></article>)}</section>}
    {drilldown ? <section className="panel analytics-patient-drilldown"><div className="panel-heading"><div><p className="eyebrow">Patient traceability</p><h3>{drilldown.title}</h3><p className="analytics-drilldown-scope">{drilldownQuery.data?.scope ?? 'Finding matching patients...'}</p></div><div className="analytics-drilldown-actions">{drilldownQuery.data ? <button className="secondary-button" type="button" onClick={() => downloadPatientMatchesCsv(drilldown.title, drilldownQuery.data.items)}><FileDown size={16} /> Download list</button> : null}<button className="secondary-button" type="button" onClick={() => setDrilldown(null)}>Close</button></div></div>{drilldownQuery.isLoading ? <LoadingState label="Finding matching patients" /> : <><p className="analytics-drilldown-count">{drilldownQuery.data?.count ?? 0} patient{drilldownQuery.data?.count === 1 ? '' : 's'} found</p><PatientTraceabilityTable items={drilldownQuery.data?.items ?? []} /></>}</section> : null}
    {distributionQuery.isLoading ? <LoadingState label="Loading distributions" /> : <>
      <section className="analytics-chart-section analytics-domain-section"><div className="analytics-section-heading"><div><p className="eyebrow">Cohort overview</p><h3>Patient-level clinical summary</h3></div><div className="analytics-section-tools"><p>Latest available value per included patient.</p><button className="analytics-review-button" type="button" onClick={() => viewPatients('Cohort patients')}>View matching patients</button></div></div><div className="analytics-chart-grid"><DistributionChart title="Stage distribution" items={distributionQuery.data?.stage ?? []} paletteMode={paletteMode} /><DistributionChart title="Tumor grade" items={distributionQuery.data?.grade ?? []} defaultChartType="donut" paletteMode={paletteMode} /><DistributionChart title="Recorded responses" items={distributionQuery.data?.response ?? []} defaultChartType="donut" paletteMode={paletteMode} /></div></section>
      <AnalyticsSection eyebrow="Histopathology" title="Tumor pathology" description="Shared method and site filters apply to every pathology chart." filterSubject="histopathology" filters={filters} paletteMode={paletteMode} onViewPatients={viewPatients}>{sectionFilters => <><FacetedChart title="Histopathology method" subject="histopathology_method" filters={filters} sectionFilters={sectionFilters} showFacetFilters={false} paletteMode={paletteMode} /><FacetedChart title="Histopathology site" subject="histopathology_site" filters={filters} sectionFilters={sectionFilters} showFacetFilters={false} paletteMode={paletteMode} /><FacetedChart title="Histopathology diagnosis" subject="histopathology" filters={filters} sectionFilters={sectionFilters} showFacetFilters={false} paletteMode={paletteMode} horizontal /></>}</AnalyticsSection>
      <AnalyticsSection eyebrow="Molecular pathology" title="Method → gene → result" description="Patient, test-event, and result-entry charts are intentionally separated. Shared method and gene filters apply to every molecular chart." filterSubject="molecular" filters={filters} paletteMode={paletteMode} onViewPatients={viewPatients}>{sectionFilters => <><MolecularSummaryCards filters={{ ...filters, ...sectionFilters }} /><MolecularResultCrossTab filters={{ ...filters, ...sectionFilters }} /><FacetedChart title="Patients tested by method" subject="molecular_method" filters={filters} sectionFilters={sectionFilters} showFacetFilters={false} paletteMode={paletteMode} countMode="patients" /><FacetedChart title="Molecular test events by method" subject="molecular_method" filters={filters} sectionFilters={sectionFilters} showFacetFilters={false} paletteMode={paletteMode} countMode="observations" /><FacetedChart title="Gene-result entries by method" subject="molecular_method" filters={filters} sectionFilters={sectionFilters} showFacetFilters={false} paletteMode={paletteMode} countMode="records" /><FacetedChart title="Patients tested by gene" subject="molecular_gene" filters={filters} sectionFilters={sectionFilters} showFacetFilters={false} paletteMode={paletteMode} countMode="patients" horizontal /><FacetedChart title="Molecular result entries" subject="molecular" filters={filters} sectionFilters={sectionFilters} showFacetFilters={false} paletteMode={paletteMode} defaultChartType="donut" countMode="records" /><FacetedChart title="Molecular specimen" subject="molecular_specimen" filters={filters} sectionFilters={sectionFilters} showFacetFilters={false} paletteMode={paletteMode} countMode="observations" /><FacetedChart title="Molecular exon" subject="molecular_exon" filters={filters} sectionFilters={sectionFilters} showFacetFilters={false} paletteMode={paletteMode} countMode="records" horizontal /><MolecularChronologyChart filters={{ ...filters, ...sectionFilters }} paletteMode={paletteMode} /></>}</AnalyticsSection>
      <AnalyticsSection eyebrow="Cancer markers" title="Recorded marker tests" description="The unit filter applies to every cancer-marker chart." filterSubject="cancer_marker" filters={filters} paletteMode={paletteMode} onViewPatients={viewPatients}>{sectionFilters => <><FacetedChart title="Cancer marker recordings" subject="cancer_marker" filters={filters} sectionFilters={sectionFilters} showFacetFilters={false} paletteMode={paletteMode} horizontal /><FacetedChart title="Cancer marker unit" subject="cancer_marker_unit" filters={filters} sectionFilters={sectionFilters} showFacetFilters={false} paletteMode={paletteMode} /></>}</AnalyticsSection>
      <AnalyticsSection eyebrow="Systemic treatment" title="Modality, line, and recorded cycles" description="Shared line and modality filters apply to every treatment chart. Raw protocol text remains an audit view." filterSubject="treatment" filters={filters} paletteMode={paletteMode} onViewPatients={viewPatients}>{sectionFilters => <><FacetedChart title="Treatment modality" subject="treatment_modality" filters={filters} sectionFilters={sectionFilters} showFacetFilters={false} paletteMode={paletteMode} /><FacetedChart title="Line of treatment" subject="treatment_line" filters={filters} sectionFilters={sectionFilters} showFacetFilters={false} paletteMode={paletteMode} /><FacetedChart title="Raw treatment-cycle entries" subject="treatment" filters={filters} sectionFilters={sectionFilters} showFacetFilters={false} paletteMode={paletteMode} horizontal /></>}</AnalyticsSection>
      <AnalyticsSection eyebrow="Radiotherapy" title="Intent, site, and modality" description="Shared site and modality filters apply to every radiotherapy chart." filterSubject="radiotherapy" filters={filters} paletteMode={paletteMode} onViewPatients={viewPatients}>{sectionFilters => <><FacetedChart title="Radiotherapy intent" subject="radiotherapy" filters={filters} sectionFilters={sectionFilters} showFacetFilters={false} paletteMode={paletteMode} defaultChartType="donut" /><FacetedChart title="Radiotherapy site" subject="radiotherapy_site" filters={filters} sectionFilters={sectionFilters} showFacetFilters={false} paletteMode={paletteMode} /><FacetedChart title="Radiotherapy modality" subject="radiotherapy_modality" filters={filters} sectionFilters={sectionFilters} showFacetFilters={false} paletteMode={paletteMode} /></>}</AnalyticsSection>
      <AnalyticsSection eyebrow="Surgery" title="Modality and laterality" description="The laterality filter applies to both surgery charts." filterSubject="surgery" filters={filters} paletteMode={paletteMode} onViewPatients={viewPatients}>{sectionFilters => <><FacetedChart title="Surgery modality" subject="surgery" filters={filters} sectionFilters={sectionFilters} showFacetFilters={false} paletteMode={paletteMode} horizontal /><FacetedChart title="Surgery laterality" subject="surgery_laterality" filters={filters} sectionFilters={sectionFilters} showFacetFilters={false} paletteMode={paletteMode} /></>}</AnalyticsSection>
    </>}
    <section className="insight-grid"><article className="panel"><div className="panel-heading"><div><p className="eyebrow">Survival summary</p><h3><BarChart3 size={17} /> PFS and OS</h3></div></div>{survivalQuery.isLoading ? <LoadingState label="Calculating survival summary" /> : <><div className="analytics-table-wrap"><table className="registry-table"><thead><tr><th>Metric</th><th>Available</th><th>Median days</th><th>Median months</th></tr></thead><tbody>{survival.map(item => <tr key={item.metric}><td>{item.metric.toUpperCase()}</td><td>{item.available}</td><td>{formatMedianDays(item.median_days)}</td><td>{item.median_days === null ? '—' : (item.median_days / DAYS_PER_AVERAGE_MONTH).toFixed(1)}</td></tr>)}</tbody></table></div><p className="analytics-survival-note">Descriptive calculation only; not a Kaplan–Meier estimate. Months = median days ÷ 30.4375 (365.25 ÷ 12). <a href="https://nctn-data-archive.nci.nih.gov/system/files/dataset/NCT00310180-D1/NCT00310180-D1-Data-Dictionary.pdf" target="_blank" rel="noreferrer">Reference: NCI trial data dictionary</a>.</p></>}</article><article className="panel"><div className="panel-heading"><div><p className="eyebrow">Data quality</p><h3>Completeness</h3></div></div><div className="analytics-completeness">{completeness.map(item => <div key={item.label}><span>{item.label}</span><strong>{item.count}/{item.total}</strong><div><i style={{ width: `${item.total ? item.count / item.total * 100 : 0}%` }} /></div></div>)}</div></article></section>
    <section className="panel analytics-definitions"><p className="eyebrow"><ShieldCheck size={16} /> Calculation definitions</p>{Object.entries(summaryQuery.data?.definitions ?? {}).map(([key, value]) => <p key={key}><strong>{key.replace('_', ' ')}:</strong> {value}</p>)}</section>
  </section>
}
