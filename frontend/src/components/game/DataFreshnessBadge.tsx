import { useEffect, useState } from 'react'

/** Seconds since an ISO timestamp, ticking once a second. */
export function useSecondsSince(iso?: string | null): number | null {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])
  if (!iso) return null
  const t = new Date(iso).getTime()
  if (isNaN(t)) return null
  return Math.max(0, Math.round((now - t) / 1000))
}

export function formatAge(seconds: number | null): string {
  if (seconds == null) return 'unknown'
  if (seconds < 60) return `${seconds}s ago`
  const m = Math.floor(seconds / 60)
  if (m < 60) return `${m} min ago`
  const h = Math.floor(m / 60)
  return `${h} hr ago`
}

export interface DataFreshnessBadgeProps {
  /** ISO timestamp of the data currently on screen. */
  fetchedAt?: string | null
  /** Where the numbers came from, e.g. "ESPN BET". Always shown. */
  source?: string | null
  /** Older than this and we warn the user rather than pretending it's live. */
  staleAfterSeconds?: number
  /** False when the last fetch failed — we're showing the last good data. */
  ok?: boolean
  className?: string
}

/**
 * Source + age for any data-driven panel. Goes amber when the data is older
 * than it should be and red when the feed is failing, so a stale number is
 * never presented as a live one.
 */
export function DataFreshnessBadge({
  fetchedAt, source, staleAfterSeconds = 90, ok = true, className = '',
}: DataFreshnessBadgeProps) {
  const age = useSecondsSince(fetchedAt)
  const stale = age != null && age > staleAfterSeconds
  const tone = !ok
    ? 'text-signal-red'
    : stale ? 'text-signal-amber' : 'text-zinc-400'
  const label = !ok
    ? 'Feed unreachable — showing last good data'
    : stale ? `Stale · updated ${formatAge(age)}` : `Updated ${formatAge(age)}`

  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs ${tone} ${className}`}
      title={fetchedAt ? new Date(fetchedAt).toLocaleString() : undefined}
    >
      <span
        aria-hidden="true"
        className={`h-1.5 w-1.5 rounded-full ${
          !ok ? 'bg-signal-red' : stale ? 'bg-signal-amber' : 'bg-signal-green'
        }`}
      />
      {source ? <span className="font-semibold text-zinc-300">{source}</span> : null}
      {source ? <span aria-hidden="true" className="text-zinc-500">·</span> : null}
      <span>{label}</span>
    </span>
  )
}
