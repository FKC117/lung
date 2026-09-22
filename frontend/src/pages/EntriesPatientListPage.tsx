import { useDeferredValue, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Plus, Search } from 'lucide-react'
import { Link } from 'react-router-dom'

import { fetchEntriesPatients } from '../api'

export default function EntriesPatientListPage() {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const deferredSearch = useDeferredValue(search)
  const patientsQuery = useQuery({ queryKey: ['entries-patients', deferredSearch, page], queryFn: () => fetchEntriesPatients(deferredSearch, page, 24) })
  const patients = patientsQuery.data?.results ?? []
  const total = patientsQuery.data?.count ?? 0

  return <section className="page-grid">
    <section className="hero-panel hero-panel-tight"><div className="hero-copy"><p className="eyebrow">Entries workspace</p><h2>Structured patient records</h2><p className="hero-text">Patients and observations recorded through the normalized Entries API.</p></div><Link className="primary-button" to="/entries/new"><Plus size={16} />Structured entry</Link></section>
    <section className="panel panel-compact"><div className="search-row"><Search className="search-icon" size={18} /><input className="search-input" value={search} onChange={event => { setSearch(event.target.value); setPage(1) }} placeholder="Search registry ID, patient name, phone, or registration no." /></div></section>
    <section className="panel"><div className="panel-heading"><div><p className="eyebrow">Entries patients</p><h3>{patientsQuery.isLoading ? 'Loading records…' : `${total} matching patient${total === 1 ? '' : 's'}`}</h3></div><div className="header-badges"><span className="data-pill">{total ? `${(page - 1) * 24 + 1}-${Math.min(page * 24, total)} of ${total}` : '0 records'}</span></div></div><div className="registry-table-wrap"><table className="registry-table"><thead><tr><th>Registry ID</th><th>Patient</th><th>Phone</th><th>Registration no.</th><th /></tr></thead><tbody>{patients.map(patient => <tr key={patient.id}><td>{patient.patient_id}</td><td>{patient.name}</td><td>{patient.phone || '—'}</td><td>{patient.registration_no || '—'}</td><td><Link to={`/entries/patients/${patient.id}`}>Open record</Link></td></tr>)}{!patientsQuery.isLoading && !patients.length ? <tr><td colSpan={5}>No Entries patient records found.</td></tr> : null}</tbody></table></div>{total > 24 ? <div className="entry-form-actions"><button type="button" className="secondary-button" disabled={!patientsQuery.data?.previous} onClick={() => setPage(current => current - 1)}>Previous</button><button type="button" className="secondary-button" disabled={!patientsQuery.data?.next} onClick={() => setPage(current => current + 1)}>Next</button></div> : null}</section>
  </section>
}
