import { LoaderCircle } from 'lucide-react'

export function DataBadge({
  label,
  value,
}: {
  label: string
  value?: string | null
}) {
  return (
    <div className="data-badge">
      <span>{label}</span>
      <strong>{value || ''}</strong>
    </div>
  )
}

export function DataPoint({
  label,
  value,
}: {
  label: string
  value?: string | number | null
}) {
  return (
    <div className="data-point">
      <span>{label}</span>
      <strong>{value === null || value === undefined || value === '' ? '' : value}</strong>
    </div>
  )
}

export function ListPanel({
  title,
  items,
}: {
  title: string
  items: Array<string | null | undefined>
}) {
  const cleanItems = items.filter(
    (item): item is string => Boolean(item && item.trim()),
  )

  return (
    <section className="list-panel">
      <p className="list-panel-title">{title}</p>
      {cleanItems.length ? (
        <div className="list-panel-items">
          {cleanItems.map((item, index) => (
            <span key={`${title}-${index}`} className="mini-chip">
              {item}
            </span>
          ))}
        </div>
      ) : (
        <p className="list-panel-empty">No data recorded</p>
      )}
    </section>
  )
}

export function LoadingState({ label }: { label: string }) {
  return (
    <div className="state-card" role="status" aria-live="polite">
      <LoaderCircle className="spin" size={20} />
      <span>{label}</span>
    </div>
  )
}

export function EmptyState({
  title,
  detail,
}: {
  title: string
  detail: string
}) {
  return (
    <div className="state-card state-card-empty">
      <p className="empty-title">{title}</p>
      <p>{detail}</p>
    </div>
  )
}
