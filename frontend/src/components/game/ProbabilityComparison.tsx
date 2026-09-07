import type { MarketOut, ProbabilityKind } from '../../types'

const KIND_NOUN: Record<ProbabilityKind, string> = {
  win: 'win probability',
  cover: 'cover probability',
  total: 'over/under probability',
}

const pct1 = (v?: number | null) => (v == null ? '—' : `${(v * 100).toFixed(1)}%`)

function Bar({ label, value, tone, hint }: { label: string; value?: number | null; tone: string; hint?: string }) {
  const w = value == null ? 0 : Math.max(0, Math.min(1, value)) * 100
  return (
    <div className="grid grid-cols-[6.5rem_1fr_3.5rem] items-center gap-3">
      <span className="text-xs font-semibold text-zinc-400" title={hint}>{label}</span>
      <span className="h-2 overflow-hidden rounded-full bg-terminal-muted" aria-hidden="true">
        <span className={`block h-full rounded-full ${tone} motion-safe:transition-all motion-safe:duration-500`} style={{ width: `${w}%` }} />
      </span>
      <span className="text-right font-mono text-sm font-semibold tabular-nums text-zinc-100">{pct1(value)}</span>
    </div>
  )
}

/**
 * Model vs sportsbook (vig removed) vs prediction-market crowd, for both sides
 * of one market. The heading names exactly which probability is being compared
 * so a cover probability can't be read as a win probability.
 */
export function ProbabilityComparison({ market }: { market: MarketOut }) {
  const noun = KIND_NOUN[market.probability_kind]
  const hasCrowd = market.selections.some(s => s.crowd_prob != null)

  return (
    <div className="space-y-5">
      <p className="text-xs text-zinc-400">
        Comparing <span className="font-semibold text-zinc-200">{noun}</span> — {market.question}
      </p>

      {market.selections.map(sel => (
        <div key={sel.side} className="space-y-2">
          <div className="flex items-baseline justify-between gap-2">
            <h3 className="text-sm font-bold text-zinc-100">{sel.label}</h3>
            {sel.edge_pp != null && (
              <span className={`text-xs font-semibold ${sel.edge_pp > 0 ? 'text-signal-green' : 'text-zinc-400'}`}>
                {sel.edge_pp > 0 ? '+' : ''}{sel.edge_pp.toFixed(1)} percentage points vs book
              </span>
            )}
          </div>
          <Bar label="StatEdge" value={sel.model_prob} tone="bg-signal-green"
               hint={`The model's ${noun}`} />
          <Bar label="Sportsbook" value={sel.book_prob} tone="bg-zinc-500"
               hint="Sportsbook implied probability with the vig removed" />
          {hasCrowd && (
            <Bar label="Crowd" value={sel.crowd_prob} tone="bg-signal-blue"
                 hint="Prediction-market (Polymarket) consensus" />
          )}
        </div>
      ))}

      {!hasCrowd && (
        <p className="text-xs text-zinc-500">
          No prediction-market quote for this game, so the crowd column is omitted rather than estimated.
        </p>
      )}
    </div>
  )
}
