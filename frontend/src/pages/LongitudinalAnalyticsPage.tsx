// LEGACY_UI: this screen targets the retired longitudinal analytics API.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState, type ComponentType } from 'react'
import { Activity, CalendarRange, Download, Dna, ShieldCheck, Stethoscope, Users } from 'lucide-react'
import type { EChartsOption } from 'echarts'
import { buildMolecularPatientTraceExportUrl, fetchAnalyticsReviewQueue, fetchCurrentUser, fetchLongitudinalAnalytics, refreshLongitudinalAnalytics, updateAnalyticsReviewTask } from '../api'
import { ClinicalChart } from '../components/ClinicalChart'
import { LoadingState } from '../components/registry-ui'

type PaletteMode = 'standard' | 'colorful' | 'tropical' | 'aurora'
type ChartType = 'bar' | 'donut' | 'table'

const palettes: Record<PaletteMode, string[]> = {
  standard: ['#0f766e', '#168aa2', '#3f74ad', '#5e6f91', '#7c6a9f', '#4f8b72', '#a77a45', '#b25b70', '#8b9650', '#4b8891', '#7288a9', '#8b7697'],
  colorful: ['#2563eb', '#db2777', '#f97316', '#16a34a', '#7c3aed', '#0891b2', '#eab308', '#dc2626', '#14b8a6', '#9333ea', '#f43f5e', '#65a30d'],
  tropical: ['#00b8a9', '#24a8f2', '#8b5cf6', '#f54291', '#ff7a45', '#fbc531', '#a3d65c', '#24d4a8', '#2f80ed', '#ff5e7d', '#ef4444', '#c084fc'],
  aurora: ['#00e5ff', '#00b0ff', '#2979ff', '#651fff', '#aa00ff', '#d500f9', '#ff0080', '#ff1744', '#ff6d00', '#ffd600', '#aeea00', '#00e676'],
}
const paletteLabels: Record<PaletteMode, string> = { standard: 'Standard', colorful: 'Colorful', tropical: 'Tropical', aurora: 'Aurora' }

function DistributionChart({ title, items, paletteMode, defaultChartType = 'bar' }: { title: string; items: Array<{ label: string; count: number }>; paletteMode: PaletteMode; defaultChartType?: ChartType }) {
  const [chartType, setChartType] = useState<ChartType>(defaultChartType)
  const total = items.reduce((sum, item) => sum + item.count, 0)
  const palette = palettes[paletteMode]
  const usesMulticolorBars = paletteMode !== 'standard'
  const barItems = [...items].reverse()
  const barData = usesMulticolorBars
    ? barItems.map((item, index) => ({ value: item.count, itemStyle: { color: palette[index % palette.length] } }))
    : barItems.map((item) => item.count)
  const option: EChartsOption = chartType === 'donut' ? {
    color: palette,
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, type: 'scroll' },
    series: [{ type: 'pie', radius: ['42%', '68%'], center: ['50%', '43%'], label: { formatter: '{b}: {c}' }, data: items.map((item) => ({ name: item.label, value: item.count })) }],
  } : {
    color: palette,
    grid: { left: 112, right: 24, top: 20, bottom: 24 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', minInterval: 1 },
    yAxis: { type: 'category', data: barItems.map((item) => item.label), axisLabel: { width: 100, overflow: 'truncate' } },
    series: [{ type: 'bar', data: barData, barMaxWidth: 28, itemStyle: usesMulticolorBars ? { borderRadius: [0, 6, 6, 0] } : { color: '#0f766e', borderRadius: [0, 6, 6, 0] } }],
  }
  return <article className="panel analytics-chart"><div className="panel-heading analytics-chart-heading"><h3>{title}</h3><div className="analytics-chart-controls"><label>Chart<select value={chartType} onChange={(event) => setChartType(event.target.value as ChartType)}><option value="bar">Bar</option><option value="donut">Donut</option><option value="table">Table</option></select></label></div></div>{chartType === 'table' ? <div className="analytics-table-wrap longitudinal-distribution-table"><table className="registry-table"><thead><tr><th>Category</th><th>Events</th><th>Share</th></tr></thead><tbody>{items.map((item) => <tr key={item.label}><td>{item.label}</td><td>{item.count}</td><td>{total ? `${(item.count / total * 100).toFixed(1)}%` : '—'}</td></tr>)}</tbody></table></div> : <ClinicalChart option={option} height={chartType === 'donut' ? 290 : Math.max(230, items.length * 30 + 55)} exportTitle={title} />}</article>
}

type MolecularRow = { method: string; specimen: string; gene: string; exon: string; result: string; count: number }
type MolecularPatientRow = { registry_id: string; patient_source_id: number; age: number | null; sex: string; observation_source_id: number | null; molecular_test_source_id: number; molecular_result_source_id: number; tested_at: string | null; method: string; specimen: string; gene: string; exon: string; result: string }
type MolecularFilterKey = 'method' | 'specimen' | 'gene' | 'exon' | 'result'

function MolecularCrossFilter({ rows, patientRows, paletteMode, dates }: { rows: MolecularRow[]; patientRows: MolecularPatientRow[]; paletteMode: PaletteMode; dates: { start_date: string; end_date: string } }) {
  const [filters, setFilters] = useState<Record<MolecularFilterKey, string>>({ method: '', specimen: '', gene: '', exon: '', result: '' })
  const [tableOpen, setTableOpen] = useState(false)
  const [tablePage, setTablePage] = useState(0)
  const options = (key: MolecularFilterKey) => [...new Set(rows.map((row) => row[key]))].sort()
  const filtered = rows.filter((row) => (Object.keys(filters) as MolecularFilterKey[]).every((key) => !filters[key] || row[key] === filters[key]))
  const filteredPatientRows = patientRows.filter((row) => (Object.keys(filters) as MolecularFilterKey[]).every((key) => !filters[key] || row[key] === filters[key]))
  const total = filtered.reduce((sum, row) => sum + row.count, 0)
  const totalPages = Math.max(1, Math.ceil(filteredPatientRows.length / 10))
  const currentPage = Math.min(tablePage, totalPages - 1)
  const pageRows = filteredPatientRows.slice(currentPage * 10, currentPage * 10 + 10)
  const aggregate = (key: MolecularFilterKey) => Object.entries(filtered.reduce<Record<string, number>>((result, row) => ({ ...result, [row[key]]: (result[row[key]] ?? 0) + row.count }), {})).map(([label, count]) => ({ label, count })).sort((left, right) => right.count - left.count || left.label.localeCompare(right.label))
  const select = (key: MolecularFilterKey, label: string) => <label className="analytics-filter" key={key}>{label}<select value={filters[key]} onChange={(event) => { setTablePage(0); setFilters((current) => ({ ...current, [key]: event.target.value })) }}><option value="">All</option>{options(key).map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
  const exportFilters = { ...dates, ...filters }
  return <section className="analytics-chart-section analytics-domain-section"><div className="analytics-section-heading"><div><p className="eyebrow">Molecular test fragments</p><h3>Assay context and result-level detail</h3></div><div className="analytics-section-tools"><p>Filter across linked assay and result attributes to answer a specific molecular question.</p></div></div><div className="analytics-filter-grid molecular-fragment-filters">{select('method', 'Method')}{select('specimen', 'Specimen')}{select('gene', 'Gene')}{select('exon', 'Exon')}{select('result', 'Result')}<button className="secondary-button" type="button" onClick={() => { setTablePage(0); setFilters({ method: '', specimen: '', gene: '', exon: '', result: '' }) }}>Clear molecular filters</button></div><div className="molecular-filter-result"><p><strong>{total}</strong> molecular result event{total === 1 ? '' : 's'} match the selected assay/result filters.</p><div><a className="secondary-button" href={buildMolecularPatientTraceExportUrl({ ...exportFilters, mode: 'summary' })}><Download size={15} /> Download patient summary CSV</a><a className="secondary-button" href={buildMolecularPatientTraceExportUrl({ ...exportFilters, mode: 'trace' })}><Users size={15} /> Download this table CSV</a></div></div><div className="analytics-chart-grid"><DistributionChart title="Matched tests by method" items={aggregate('method')} paletteMode={paletteMode} /><DistributionChart title="Matched tests by specimen" items={aggregate('specimen')} paletteMode={paletteMode} /><DistributionChart title="Matched results by gene" items={aggregate('gene')} paletteMode={paletteMode} defaultChartType="donut" /><DistributionChart title="Matched results by exon" items={aggregate('exon')} paletteMode={paletteMode} /><DistributionChart title="Matched result status" items={aggregate('result')} paletteMode={paletteMode} defaultChartType="donut" /></div><div className="molecular-combination-actions"><button className="secondary-button" type="button" aria-expanded={tableOpen} onClick={() => setTableOpen((current) => !current)}>{tableOpen ? 'Hide matching patient event table' : `Show matching patient event table (${filteredPatientRows.length})`}</button></div>{tableOpen ? <><div className="analytics-table-wrap molecular-combination-table"><table className="registry-table"><thead><tr><th>Registry ID</th><th>Age</th><th>Sex</th><th>Method</th><th>Specimen</th><th>Gene</th><th>Exon</th><th>Result</th><th>Tested at</th></tr></thead><tbody>{pageRows.map((row) => <tr key={row.molecular_result_source_id}><td><a href={`/entries/patients/${row.patient_source_id}`} target="_blank" rel="noreferrer">{row.registry_id}</a></td><td>{row.age ?? '—'}</td><td>{row.sex}</td><td>{row.method}</td><td>{row.specimen}</td><td>{row.gene}</td><td>{row.exon}</td><td>{row.result}</td><td>{row.tested_at ?? '—'}</td></tr>)}</tbody></table></div><div className="molecular-table-pagination"><span>Showing {filteredPatientRows.length ? currentPage * 10 + 1 : 0}–{Math.min((currentPage + 1) * 10, filteredPatientRows.length)} of {filteredPatientRows.length}</span><div><button className="secondary-button" type="button" disabled={currentPage === 0} onClick={() => setTablePage((page) => Math.max(0, page - 1))}>Previous</button><span>Page {currentPage + 1} of {totalPages}</span><button className="secondary-button" type="button" disabled={currentPage >= totalPages - 1} onClick={() => setTablePage((page) => Math.min(totalPages - 1, page + 1))}>Next</button></div></div></> : null}</section>
}

function MolecularQualitySection({ quality, repeats }: { quality: { test_total: number; result_total: number; missing_test_date: number; missing_method: number; missing_specimen: number; missing_gene: number; missing_exon: number; missing_result: number }; repeats: Array<{ registry_id: string; patient_source_id: number; age: number | null; sex: string; gene: string; test_events: number; result_categories: number; first_tested_at: string | null; last_tested_at: string | null; discordant: boolean }> }) {
  const [page, setPage] = useState(0)
  const totalPages = Math.max(1, Math.ceil(repeats.length / 10))
  const currentPage = Math.min(page, totalPages - 1)
  const rows = repeats.slice(currentPage * 10, currentPage * 10 + 10)
  const checks: Array<[string, number, number]> = [
    ['Tests without tested date', quality.missing_test_date, quality.test_total], ['Tests without method', quality.missing_method, quality.test_total], ['Tests without specimen', quality.missing_specimen, quality.test_total],
    ['Results without gene', quality.missing_gene, quality.result_total], ['Results without exon', quality.missing_exon, quality.result_total], ['Results without result status', quality.missing_result, quality.result_total],
  ]
  const repeatReview = <article className="panel molecular-repeat-table"><div className="panel-heading"><div><p className="eyebrow">Repeat-assay review</p><h3>{repeats.length} patient–gene combinations with more than one assay</h3></div></div><div className="analytics-table-wrap"><table className="registry-table"><thead><tr><th>Registry ID</th><th>Age</th><th>Sex</th><th>Gene</th><th>Assays</th><th>Result categories</th><th>First test</th><th>Last test</th><th>Review flag</th></tr></thead><tbody>{rows.map((row) => <tr key={`${row.patient_source_id}-${row.gene}`}><td><a href={`/entries/patients/${row.patient_source_id}`} target="_blank" rel="noreferrer">{row.registry_id}</a></td><td>{row.age ?? '—'}</td><td>{row.sex}</td><td>{row.gene}</td><td>{row.test_events}</td><td>{row.result_categories}</td><td>{row.first_tested_at ?? '—'}</td><td>{row.last_tested_at ?? '—'}</td><td>{row.discordant ? 'Discordant — review' : 'Repeated, consistent'}</td></tr>)}</tbody></table></div><div className="molecular-table-pagination"><span>Showing {repeats.length ? currentPage * 10 + 1 : 0}–{Math.min((currentPage + 1) * 10, repeats.length)} of {repeats.length}</span><div><button className="secondary-button" type="button" disabled={currentPage === 0} onClick={() => setPage((value) => Math.max(0, value - 1))}>Previous</button><span>Page {currentPage + 1} of {totalPages}</span><button className="secondary-button" type="button" disabled={currentPage >= totalPages - 1} onClick={() => setPage((value) => Math.min(totalPages - 1, value + 1))}>Next</button></div></div></article>
  return <section className="analytics-chart-section analytics-domain-section"><div className="analytics-section-heading"><div><p className="eyebrow">Molecular quality and repeat testing</p><h3>Completeness and repeat-assay review</h3></div><div className="analytics-section-tools"><p>Discordant means more than one recorded result category for the same patient and gene across separate assays; it is a review flag, not an automatic reconciliation.</p></div></div>{repeatReview}<div className="molecular-quality-grid">{checks.map(([label, missing, total]) => <article className="panel" key={label}><span>{label}</span><strong>{missing}/{total}</strong><small>{total ? `${(missing / total * 100).toFixed(1)}% missing` : 'No rows'}</small></article>)}</div></section>
}

function ReviewQueue() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['analytics-review-queue'], queryFn: fetchAnalyticsReviewQueue })
  const [draftNotes, setDraftNotes] = useState<Record<string, string>>({})
  const [queueOpen, setQueueOpen] = useState(false)
  const [expandedTask, setExpandedTask] = useState<string | null>(null)
  const [page, setPage] = useState(0)
  const update = useMutation({ mutationFn: ({ key, status, notes }: { key: string; status: string; notes: string }) => updateAnalyticsReviewTask(key, status, notes), onSuccess: () => client.invalidateQueries({ queryKey: ['analytics-review-queue'] }) })
  const noteFor = (key: string, persisted: string) => draftNotes[key] ?? persisted
  const items = query.data?.items ?? []
  const pageSize = 5
  const totalPages = Math.max(1, Math.ceil(items.length / pageSize))
  const currentPage = Math.min(page, totalPages - 1)
  const pageItems = items.slice(currentPage * pageSize, currentPage * pageSize + pageSize)
  return <section className="panel review-queue"><div className="panel-heading"><div><p className="eyebrow">Validation review workflow</p><h3>Start in Longitudinal Insights, review in Entries</h3></div><button className="secondary-button" type="button" aria-expanded={queueOpen} onClick={() => setQueueOpen((value) => !value)}>{queueOpen ? 'Hide review queue' : `Review queue (${items.length})`}</button></div>{queueOpen ? <><p className="review-queue-guidance">Notes and decisions stay in analytics. If correction is needed, open the exact source row in Django Admin; Admin enforces the user’s access and change permission.</p>{query.isLoading ? <LoadingState label="Loading review queue" /> : <div className="review-task-list">{pageItems.map((item) => {
    const queryString = new URLSearchParams()
    if (item.observation_id) queryString.set('observation_id', String(item.observation_id))
    if (item.review_section) queryString.set('review_section', item.review_section)
    const sourceUrl = `/entries/patients/${item.patient_source_id}${queryString.size ? `?${queryString}` : ''}`
    const notes = noteFor(item.task_key, item.notes)
    const correctionTargets = item.correction_targets ?? []
    const expanded = expandedTask === item.task_key
    return <article className="review-task" key={item.task_key}><div className="review-task-summary"><div><p className="review-task-title">{item.title}</p><small>{item.registry_id} · {item.reason}</small></div><div className="review-task-actions"><span className={`review-status review-status-${item.status}`}>{item.status.replaceAll('_', ' ')}</span><button className="secondary-button" type="button" aria-expanded={expanded} onClick={() => setExpandedTask(expanded ? null : item.task_key)}>{expanded ? 'Close' : 'Review'}</button></div></div>{expanded ? <div className="review-task-detail"><section className="review-task-decision"><p className="eyebrow">Review decision</p><div className="review-task-field"><label>Status<select value={item.status} disabled={update.isPending} onChange={(event) => update.mutate({ key: item.task_key, status: event.target.value, notes })}><option value="open">Open</option><option value="in_review">In review</option><option value="accepted">Accepted</option><option value="needs_correction">Needs correction</option></select></label><label>Review note<textarea aria-label={`Review notes for ${item.title}`} value={notes} onChange={(event) => setDraftNotes((current) => ({ ...current, [item.task_key]: event.target.value }))} placeholder="Stored outside Entries" rows={3} /></label></div><button className="secondary-button" type="button" disabled={update.isPending} onClick={() => update.mutate({ key: item.task_key, status: item.status, notes })}>Save review</button></section><section className="review-task-source"><p className="eyebrow">Source actions</p><div><a className="secondary-button" href={sourceUrl} target="_blank" rel="noreferrer">Open exact Entries card</a>{item.status === 'needs_correction' ? correctionTargets.length ? correctionTargets.map((target) => <a className="secondary-button" href={target.url} target="_blank" rel="noreferrer" key={target.url}>Django Admin: {target.label}</a>) : <small>The exact source row is unavailable for this review item.</small> : null}</div>{item.history[0] ? <small>Last review: {item.history[0].changed_by} · {new Date(item.history[0].changed_at).toLocaleDateString()}</small> : null}</section></div> : null}</article>
  })}</div>}<div className="molecular-table-pagination review-pagination"><span>Showing {items.length ? currentPage * pageSize + 1 : 0}–{Math.min((currentPage + 1) * pageSize, items.length)} of {items.length}</span><div><button className="secondary-button" type="button" disabled={currentPage === 0} onClick={() => setPage((value) => Math.max(0, value - 1))}>Previous</button><span>Page {currentPage + 1} of {totalPages}</span><button className="secondary-button" type="button" disabled={currentPage >= totalPages - 1} onClick={() => setPage((value) => Math.min(totalPages - 1, value + 1))}>Next</button></div></div></> : null}</section>
}

export default function LongitudinalAnalyticsPage() {
  const [dates, setDates] = useState({ start_date: '', end_date: '' })
  const [paletteMode, setPaletteMode] = useState<PaletteMode>('colorful')
  const [snapshotDetailsOpen, setSnapshotDetailsOpen] = useState(false)
  const query = useQuery({ queryKey: ['longitudinal-analytics', 'study-order-v2', dates], queryFn: () => fetchLongitudinalAnalytics(dates) })
  const currentUser = useQuery({ queryKey: ['current-user'], queryFn: fetchCurrentUser })
  const client = useQueryClient()
  const refresh = useMutation({ mutationFn: refreshLongitudinalAnalytics, onSuccess: () => client.invalidateQueries({ queryKey: ['longitudinal-analytics'] }) })
  const data = query.data
  const chronologyOption = useMemo<EChartsOption>(() => {
    const types = ['Observations', 'Molecular tests', 'Treatment cycles', 'Response assessments']
    const months = [...new Set((data?.chronology ?? []).map((item) => item.month))]
    return {
      color: palettes[paletteMode],
      tooltip: { trigger: 'axis' },
      legend: { bottom: 0 },
      grid: { left: 42, right: 20, top: 26, bottom: 48 },
      xAxis: { type: 'category', data: months.map((month) => new Date(`${month}T00:00:00`).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })) },
      yAxis: { type: 'value', minInterval: 1 },
      series: types.map((type) => ({ name: type, type: 'line', smooth: true, showSymbol: false, data: months.map((month) => data?.chronology.find((item) => item.month === month && item.event_type === type)?.count ?? 0) })),
    }
  }, [data, paletteMode])

  const metrics: Array<[string, number, ComponentType<{ size?: number }>]> = [
    ['Patients with observations', data?.metrics.patients_with_observations ?? 0, Stethoscope],
    ['Clinical observations', data?.metrics.observations ?? 0, Activity],
    ['Molecular tests', data?.metrics.molecular_tests ?? 0, Dna],
    ['Treatment cycles', data?.metrics.treatment_cycles ?? 0, CalendarRange],
  ]

  return <>
    <section className="hero-panel analytics-hero longitudinal-hero">
      <div className="hero-copy"><p className="eyebrow">Separate read-only workspace</p><h2>Oncology Longitudinal Insights</h2><p className="hero-text">Event-level analysis built from the Entries clinical source. This workspace never writes to clinical records.</p></div>
      <div className="analytics-hero-actions"><label className="analytics-palette-control">Chart palette<select value={paletteMode} onChange={(event) => setPaletteMode(event.target.value as PaletteMode)}>{Object.entries(paletteLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><div className="longitudinal-scope"><ShieldCheck size={18} /><span>Entries-backed materialized views</span></div></div>
    </section>
    <section className="panel analytics-filters longitudinal-filters"><div className="panel-heading"><div><p className="eyebrow">Event window</p><h3>Filter by actual event date</h3></div><button className="secondary-button" type="button" onClick={() => setDates({ start_date: '', end_date: '' })}>Clear dates</button></div><div className="analytics-filter-grid"><label className="analytics-filter">From<input type="date" value={dates.start_date} onChange={(event) => setDates((current) => ({ ...current, start_date: event.target.value }))} /></label><label className="analytics-filter">To<input type="date" value={dates.end_date} onChange={(event) => setDates((current) => ({ ...current, end_date: event.target.value }))} /></label></div></section>
    <ReviewQueue />
    {query.isLoading ? <LoadingState label="Loading longitudinal event data" /> : query.isError ? <section className="panel"><p>The analytics projection is unavailable. Refresh it with <code>python manage.py refresh_analytics</code>.</p></section> : <>
      <section className={`panel analytics-snapshot-status analytics-snapshot-${data?.freshness.status ?? 'current'}`}><div><p className="eyebrow">Analytics snapshot</p><h3>{data?.freshness.status === 'stale' ? 'Refresh required' : 'Current and validated'}</h3><p>{data?.freshness.reason}</p></div><div className="analytics-snapshot-actions"><button className="secondary-button" type="button" onClick={() => setSnapshotDetailsOpen((value) => !value)}>{snapshotDetailsOpen ? 'Hide details' : 'Why?'}</button>{currentUser.data?.role === 'admin' ? <button className="secondary-button" type="button" disabled={refresh.isPending} onClick={() => refresh.mutate()}>{refresh.isPending ? 'Refreshing…' : 'Refresh now'}</button> : null}</div>{snapshotDetailsOpen ? <div className="analytics-snapshot-details">{data?.freshness.differences.length ? data.freshness.differences.map((item) => <p key={item.dataset}><strong>{item.dataset}:</strong> Entries has {item.entries_rows}; analytics snapshot has {item.analytics_rows}.</p>) : <p>No source/projection row-count differences were detected.</p>}{refresh.isError ? <p className="analytics-freshness-warning">Refresh failed: {(refresh.error as Error).message}</p> : null}</div> : null}</section>
      <section className="analytics-kpis longitudinal-kpis">{metrics.map(([label, value, Icon]) => <article className="metric-card" key={String(label)}><span>{label as string}</span><strong>{value as number}</strong><Icon size={18} /></article>)}</section>
      <section className="analytics-chart-section analytics-domain-section"><div className="analytics-section-heading"><div><p className="eyebrow">1. Cohort description</p><h3>Who is represented in this study cohort?</h3></div><div className="analytics-section-tools"><p>One registered patient per row; profile charts are not clinical-event counts.</p></div></div><div className="analytics-chart-grid"><DistributionChart title="Patients by sex" items={data?.distributions.sex ?? []} paletteMode={paletteMode} defaultChartType="donut" /><DistributionChart title="Age at registration" items={data?.distributions.age_band ?? []} paletteMode={paletteMode} /><DistributionChart title="District" items={data?.distributions.district ?? []} paletteMode={paletteMode} /><DistributionChart title="Thana" items={data?.distributions.thana ?? []} paletteMode={paletteMode} /><DistributionChart title="Economic status" items={data?.distributions.economic_status ?? []} paletteMode={paletteMode} defaultChartType="donut" /><DistributionChart title="Blood group" items={data?.distributions.blood_group ?? []} paletteMode={paletteMode} defaultChartType="donut" /><DistributionChart title="Patient type" items={data?.distributions.patient_type ?? []} paletteMode={paletteMode} /></div></section>
      <section className="analytics-chart-section analytics-domain-section"><div className="analytics-section-heading"><div><p className="eyebrow">2. Diagnosis and pathology</p><h3>Baseline disease classification and tissue findings</h3></div><div className="analytics-section-tools"><p>Diagnosis and histopathology are separate recorded event streams.</p></div></div><div className="analytics-chart-grid"><DistributionChart title="Diagnosis group" items={data?.breakdowns.diagnosis_group ?? []} paletteMode={paletteMode} /><DistributionChart title="Primary site" items={data?.breakdowns.diagnosis_site ?? []} paletteMode={paletteMode} /><DistributionChart title="Histopathology type" items={data?.breakdowns.pathology_type ?? []} paletteMode={paletteMode} defaultChartType="donut" /><DistributionChart title="Histopathology grade" items={data?.breakdowns.pathology_grade ?? []} paletteMode={paletteMode} /></div></section>
      <section className="analytics-chart-section analytics-domain-section"><div className="analytics-section-heading"><div><p className="eyebrow">3. Disease characterization</p><h3>Stage and molecular profile</h3></div><div className="analytics-section-tools"><p>Clinical and pathological staging remain separate; molecular results remain assay-level.</p></div></div>
      <section className="panel analytics-chart longitudinal-timeline"><div className="panel-heading"><div><p className="eyebrow">Event chronology</p><h3>Clinical activity over time</h3></div><p>Each line counts source events, never carried-forward observation values.</p></div><ClinicalChart option={chronologyOption} height={310} exportTitle="Oncology longitudinal event chronology" /></section>
      <section className="analytics-chart-grid"><DistributionChart title="TNM stage assessments" items={data?.distributions.stage ?? []} paletteMode={paletteMode} /><DistributionChart title="Molecular results by gene" items={data?.distributions.molecular ?? []} paletteMode={paletteMode} defaultChartType="donut" /></section>
      <section className="analytics-chart-section analytics-domain-section"><div className="analytics-section-heading"><div><p className="eyebrow">Staging fragments</p><h3>Clinical and pathological TNM are separate event types</h3></div><div className="analytics-section-tools"><p>Each assessment is counted at its own recorded staging event; neither stream is substituted for the other.</p></div></div><div className="analytics-chart-grid"><DistributionChart title="Clinical stage assessments" items={data?.breakdowns.clinical_stage ?? []} paletteMode={paletteMode} /><DistributionChart title="Pathological stage assessments" items={data?.breakdowns.pathological_stage ?? []} paletteMode={paletteMode} /></div></section>
      <MolecularCrossFilter rows={data?.molecular_combinations ?? []} patientRows={data?.molecular_patient_rows ?? []} paletteMode={paletteMode} dates={dates} />
      <MolecularQualitySection quality={data?.molecular_quality ?? { test_total: 0, result_total: 0, missing_test_date: 0, missing_method: 0, missing_specimen: 0, missing_gene: 0, missing_exon: 0, missing_result: 0 }} repeats={data?.molecular_repeats ?? []} />
      </section>
      <section className="analytics-chart-section analytics-domain-section"><div className="analytics-section-heading"><div><p className="eyebrow">4. Treatment exposure</p><h3>Systemic treatment, surgery, and radiotherapy</h3></div><div className="analytics-section-tools"><p>Treatment cycles are counted at cycle grain; procedures remain distinct event types.</p></div></div><div className="analytics-chart-grid"><DistributionChart title="Treatment cycles by line" items={data?.distributions.treatment_line ?? []} paletteMode={paletteMode} /></div></section>
      <section className="analytics-chart-section analytics-domain-section"><div className="analytics-section-heading"><div><p className="eyebrow">5. Response and outcomes</p><h3>Response assessments and recorded outcomes</h3></div><div className="analytics-section-tools"><p>Response frameworks are separate from treatment outcomes.</p></div></div>
      <section className="analytics-chart-section analytics-domain-section"><div className="analytics-section-heading"><div><p className="eyebrow">Response-assessment fragments</p><h3>RECIST, iRECIST, and pathological response remain distinct</h3></div><div className="analytics-section-tools"><p>Response categories are event counts within their assessment framework, not a combined response rate.</p></div></div><div className="analytics-chart-grid"><DistributionChart title="RECIST 1.1 response assessments" items={data?.breakdowns.recist_response ?? []} paletteMode={paletteMode} defaultChartType="donut" /><DistributionChart title="iRECIST response assessments" items={data?.breakdowns.irecist_response ?? []} paletteMode={paletteMode} defaultChartType="donut" /><DistributionChart title="Pathological response assessments" items={data?.breakdowns.pathological_response ?? []} paletteMode={paletteMode} defaultChartType="donut" /></div></section>
      </section>
      <section className="insight-grid"><article className="panel analytics-definitions"><p className="eyebrow"><ShieldCheck size={16} /> Scope and safeguards</p>{Object.entries(data?.definitions ?? {}).map(([key, value]) => <p key={key}><strong>{key.replaceAll('_', ' ')}:</strong> {value}</p>)}</article><article className="panel longitudinal-quality"><div className="panel-heading"><div><p className="eyebrow">Data quality</p><h3>Missing event dates</h3></div></div>{Object.entries(data?.data_quality ?? {}).map(([key, value]) => <div key={key}><span>{key.replaceAll('_', ' ')}</span><strong>{value.missing_event_dates}/{value.total_rows}</strong></div>)}</article></section>
    </>}
  </>
}
