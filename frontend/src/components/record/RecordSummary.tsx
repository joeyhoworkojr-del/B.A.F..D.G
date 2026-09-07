import type { PickRecord } from '../../types'

const pct = (v?: number | null) => (v == null ? '—' : `${(v * 100).toFixed(1)}%`)
const units = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}u`

/**
 * A verified record.
 *
 * A null win rate renders as an em dash, never 0% — an account with nothing
 * settled has no win rate, and showing zero would read as a losing analyst.
 */
export function RecordSummary({ record, compact = false }: { record: PickRecord; compact?: boolean }) {
  const cells = [
    { label: 'Record', value: `${record.wins}-${record.losses}${record.pushes ? `-${record.pushes}` : ''}` },
    { label: 'Win rate', value: pct(record.win_rate) },
    { label: 'Units', value: record.graded ? units(record.units) : '—',
      tone: record.graded ? (record.units >= 0 ? 'good' : 'bad') : 'flat' },
    { label: 'ROI', value: record.roi_pct == null ? '—' : `${record.roi_pct >= 0 ? '+' : ''}${record.roi_pct.toFixed(1)}%`,
      tone: record.roi_pct == null ? 'flat' : record.roi_pct >= 0 ? 'good' : 'bad' },
  ]

  return (
    <dl className={`grid gap-px overflow-hidden rounded-card border border-terminal-border bg-terminal-border ${
      compact ? 'grid-cols-2 sm:grid-cols-4' : 'grid-cols-2 lg:grid-cols-4'
    }`}>
      {cells.map(c => (
        <div key={c.label} className="bg-terminal-surface px-4 py-3">
          <dt className="text-xs font-bold uppercase tracking-wide text-zinc-500">{c.label}</dt>
          <dd className={`mt-0.5 font-mono text-xl font-black tabular-nums ${
            c.tone === 'good' ? 'text-signal-green'
            : c.tone === 'bad' ? 'text-signal-red' : 'text-zinc-100'
          }`}>
            {c.value}
          </dd>
        </div>
      ))}
    </dl>
  )
}

export function PickRow({ pick }: { pick: import('../../types').PickOut }) {
  const tone =
    pick.result === 'win' ? 'border-signal-green/40 bg-signal-green/5'
    : pick.result === 'loss' ? 'border-signal-red/30 bg-signal-red/5'
    : 'border-terminal-border bg-terminal-surface'

  const label =
    pick.result === 'pending' ? (pick.locked ? 'In play' : 'Open')
    : pick.result.charAt(0).toUpperCase() + pick.result.slice(1)

  const labelTone =
    pick.result === 'win' ? 'text-signal-green'
    : pick.result === 'loss' ? 'text-signal-red'
    : pick.result === 'pending' ? 'text-zinc-500' : 'text-zinc-400'

  return (
    <li className={`min-w-0 rounded-card border p-4 ${tone}`}>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="font-bold uppercase tracking-wide text-zinc-500">
          {pick.league === 'ncaaf' ? 'NCAAF' : pick.league.toUpperCase()}
        </span>
        <span className="text-zinc-500">{pick.away} at {pick.home}</span>
        <span className={`ml-auto font-bold ${labelTone}`}>{label}</span>
      </div>

      <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-base font-bold text-zinc-100">{pick.selection}</span>
        <span className="text-xs text-zinc-500">{pick.confidence}% confidence</span>
        {pick.graded && pick.result !== 'push' && pick.result !== 'void' && (
          <span className={`ml-auto font-mono text-sm font-bold tabular-nums ${
            pick.units >= 0 ? 'text-signal-green' : 'text-signal-red'
          }`}>
            {pick.units >= 0 ? '+' : ''}{pick.units.toFixed(2)}u
          </span>
        )}
      </div>

      {pick.reasoning && (
        <p className="mt-2 text-sm leading-relaxed text-zinc-400">{pick.reasoning}</p>
      )}
      {pick.final_home != null && (
        <p className="mt-2 text-xs text-zinc-500">
          Final {pick.away} {pick.final_away} — {pick.home} {pick.final_home}
        </p>
      )}
    </li>
  )
}
