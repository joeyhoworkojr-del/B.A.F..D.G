import type { BestEdgeOut, GradeBand, ProbabilityKind } from '../../types'
import { DataFreshnessBadge } from './DataFreshnessBadge'
import { oddsSourceLabel } from '../OddsSource'

const KIND_LABEL: Record<ProbabilityKind, string> = {
  win: 'Model win probability',
  cover: 'Model cover probability',
  total: 'Model over/under probability',
}

const pct1 = (v?: number | null) => (v == null ? '—' : `${(v * 100).toFixed(1)}%`)
const am = (v?: number | null) => (v == null ? '—' : v > 0 ? `+${v}` : `${v}`)

function gradeTone(grade: string): string {
  if (grade === 'A') return 'bg-signal-green/15 text-signal-green border-signal-green/50'
  if (grade === 'B') return 'bg-signal-amber/15 text-signal-amber border-signal-amber/50'
  if (grade === 'C') return 'bg-terminal-muted text-zinc-300 border-terminal-border'
  return 'bg-terminal-muted text-zinc-400 border-terminal-border'
}

export interface PrimaryEdgeCardProps {
  edge?: BestEdgeOut | null
  gradeScale: GradeBand[]
  fetchedAt?: string | null
  sourceOk?: boolean
  /** Jump to the full explanation for this market. */
  onExplain?: (marketKey: string) => void
}

/**
 * The single most important thing on the page: what the model would back, how
 * confident it is, what the book is paying, and how big the disagreement is.
 * Every number is labelled — no bare percentages.
 */
export function PrimaryEdgeCard({
  edge, gradeScale, fetchedAt, sourceOk = true, onExplain,
}: PrimaryEdgeCardProps) {
  if (!edge) {
    return (
      <section className="rounded-xl border border-terminal-border bg-terminal-surface p-4">
        <h2 className="text-sm font-bold text-zinc-100">Best available edge</h2>
        <p className="mt-2 text-sm text-zinc-400">
          The model currently agrees with the market on every posted line for this game,
          so there is no edge worth flagging. That is a result, not missing data.
        </p>
      </section>
    )
  }

  const band = gradeScale.find(b => b.grade === edge.grade)

  return (
    <section
      aria-labelledby="primary-edge-heading"
      className="rounded-xl border border-signal-green/40 bg-terminal-surface p-4"
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 id="primary-edge-heading" className="text-sm font-bold text-zinc-100">
          Best available edge
        </h2>
        <DataFreshnessBadge fetchedAt={fetchedAt} source={oddsSourceLabel(edge.source)} ok={sourceOk} />
      </div>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-zinc-400">
            Recommended · {edge.market_label}
          </p>
          <p className="mt-1 font-display text-3xl font-black leading-none text-zinc-100">
            {edge.label}
          </p>
          <p className="mt-1.5 text-xs text-zinc-400">
            at <span className="font-mono font-semibold text-zinc-200">{am(edge.price_american)}</span>
            {edge.assumed_price && <span className="text-signal-amber"> (−110 assumed — no quoted price)</span>}
          </p>
        </div>
        <div className={`rounded-lg border px-3 py-2 text-center ${gradeTone(edge.grade)}`}>
          <p className="font-display text-2xl font-black leading-none">{edge.grade}</p>
          <p className="mt-0.5 text-xs font-semibold">{band?.label ?? 'Grade'}</p>
        </div>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
        <div>
          <dt className="text-xs text-zinc-400">{KIND_LABEL[edge.probability_kind]}</dt>
          <dd className="font-mono text-lg font-bold tabular-nums text-signal-green">{pct1(edge.model_prob)}</dd>
        </div>
        <div>
          <dt className="text-xs text-zinc-400">Sportsbook (vig removed)</dt>
          <dd className="font-mono text-lg font-bold tabular-nums text-zinc-100">{pct1(edge.book_prob)}</dd>
        </div>
        <div>
          <dt className="text-xs text-zinc-400">Edge</dt>
          <dd className="font-mono text-lg font-bold tabular-nums text-signal-green">
            {edge.edge_pp != null ? `+${edge.edge_pp.toFixed(1)}` : '—'}
            <span className="ml-1 text-xs font-semibold text-zinc-400">percentage points</span>
          </dd>
        </div>
        <div>
          <dt className="text-xs text-zinc-400">Model fair price</dt>
          <dd className="font-mono text-lg font-bold tabular-nums text-zinc-100">{am(edge.fair_price_american)}</dd>
        </div>
      </dl>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-terminal-border/70 pt-3">
        <p className="text-xs text-zinc-400">
          Expected value{' '}
          <span className={`font-mono font-semibold ${(edge.ev_per_unit ?? 0) >= 0 ? 'text-signal-green' : 'text-signal-red'}`}>
            {edge.ev_per_unit == null ? '—' : `${edge.ev_per_unit >= 0 ? '+' : ''}${(edge.ev_per_unit * 100).toFixed(1)}%`}
          </span>{' '}
          per unit staked
        </p>
        {onExplain && (
          <button
            type="button"
            onClick={() => onExplain(edge.market_key)}
            className="rounded-lg border border-terminal-border px-3 py-1.5 text-xs font-bold text-zinc-200 hover:text-zinc-100"
          >
            Why this edge? ›
          </button>
        )}
      </div>
    </section>
  )
}
