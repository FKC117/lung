// LEGACY_UI: current backend has no legacy-review endpoint.
import { useDeferredValue, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchLegacyUnlinkedHistories } from '../api'
import { EmptyState, LoadingState } from '../components/registry-ui'

export default function LegacyDraftReviewPage() {
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('open')
  const [page, setPage] = useState(1)
  const deferredQuery = useDeferredValue(query)
  const reviewQuery = useQuery({
    queryKey: ['legacy-unlinked-histories', deferredQuery, page, status],
    queryFn: () => fetchLegacyUnlinkedHistories(deferredQuery, page, status),
  })
  const data = reviewQuery.data

  return (
    <section className="page-stack">
      <section className="panel registry-panel">
        <p className="eyebrow">Legacy Data Review</p>
        <h2>Unlinked draft history chains</h2>
        <p className="section-copy">
          These rows are read-only audit records. Their referenced observation parent is absent from the legacy
          source, so they cannot be safely published or imported yet.
        </p>
        <div className="filter-row legacy-review-filters">
          <label>
            Find legacy history or observation ID
            <input
              value={query}
              onChange={(event) => {
                setQuery(event.target.value)
                setPage(1)
              }}
              placeholder="Example: 8"
            />
          </label>
          <label>
            Review state
            <select
              value={status}
              onChange={(event) => {
                setStatus(event.target.value)
                setPage(1)
              }}
            >
              <option value="open">Open</option>
              <option value="reviewed">Reviewed</option>
              <option value="resolved">Resolved</option>
            </select>
          </label>
          <span className="result-chip">{data?.count ?? 0} root chains</span>
        </div>
      </section>

      <section className="panel registry-panel">
        {reviewQuery.isLoading ? (
          <LoadingState label="Loading legacy review queue" />
        ) : data?.results.length ? (
          <>
            <div className="registry-table-wrap">
              <table className="registry-table">
                <thead>
                  <tr>
                    <th>Legacy history ID</th>
                    <th>Missing observation ID</th>
                    <th>Marital status</th>
                    <th>First diagnosis</th>
                    <th>Legacy created</th>
                    <th>Review state</th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((row) => (
                    <tr key={row.legacy_history_id}>
                      <td>{row.legacy_history_id}</td>
                      <td>{row.missing_observation_id}</td>
                      <td>{row.marital_status || ''}</td>
                      <td>{row.first_diagnosis_date || ''}</td>
                      <td>{row.created_at || ''}</td>
                      <td><span className="status-pill status-draft">{row.resolution_status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pagination-row">
              <button className="pager-button" type="button" disabled={!data.previous} onClick={() => setPage(page - 1)}>
                Previous
              </button>
              <span className="pagination-label">Page {data.page}</span>
              <button className="pager-button" type="button" disabled={!data.next} onClick={() => setPage(page + 1)}>
                Next
              </button>
            </div>
          </>
        ) : (
          <EmptyState title="No matching review rows" detail="Try another ID or review state." />
        )}
        <Link className="back-link" to="/patients">Back to registry</Link>
      </section>
    </section>
  )
}
