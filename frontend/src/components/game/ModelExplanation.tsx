import type { GradeBand, MarketOut, TodayModelOut } from '../../types'

const pct1 = (v?: number | null) => (v == null ? '—' : `${(v * 100).toFixed(1)}%`)

/**
 * Why the model lands where it does on this market, and how the grade is
 * calculated — so a letter grade is never an unexplained badge.
 */
export function ModelExplanation({
  market, model, gradeScale, modelVersion,
}: {
  market: MarketOut
  model?: TodayModelOut | null
  gradeScale: GradeBand[]
  modelVersion: string
}) {
  const pick = [...market.selections].sort(
    (a, b) => (b.edge_pp ?? -Infinity) - (a.edge_pp ?? -Infinity),
  )[0]

  return (
    <div className="space-y-4 text-sm text-zinc-300">
      <div>
        <h3 className="text-sm font-bold text-zinc-100">How this number is built</h3>
        <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm">
          <li>
            Team ratings produce expected points for each side, which give a projected
            score of{' '}
            <span className="font-mono font-semibold text-zinc-100">
              {model?.proj_away_score ?? '—'}–{model?.proj_home_score ?? '—'}
            </span>.
          </li>
          <li>
            That margin and total are turned into a {market.probability_kind === 'win' ? 'win' : market.probability_kind === 'cover' ? 'cover' : 'over/under'}{' '}
            probability using the league's historical spread of outcomes.
          </li>
          {model?.market_anchored && (
            <li>
              The headline number is then pulled toward the sportsbook's no-vig line,
              because the closing line is the sharpest public estimate available.
            </li>
          )}
          <li>
            Before any edge is claimed, the model is shrunk toward a coin flip to strip
            out over-confidence. Only what survives that is shown as an edge.
          </li>
        </ul>
      </div>

      <div>
        <h3 className="text-sm font-bold text-zinc-100">The edge on {market.label.toLowerCase()}</h3>
        <p className="mt-2">
          Model {pct1(pick?.model_prob)} vs sportsbook {pct1(pick?.book_prob)} (vig removed) on{' '}
          <span className="font-semibold text-zinc-100">{pick?.label}</span> — a gap of{' '}
          <span className="font-semibold text-signal-green">
            {pick?.edge_pp == null ? '—' : `${pick.edge_pp > 0 ? '+' : ''}${pick.edge_pp.toFixed(1)} percentage points`}
          </span>.
        </p>
      </div>

      <div>
        <h3 className="text-sm font-bold text-zinc-100">How grades are calculated</h3>
        <p className="mt-2 text-sm">
          The grade is purely the size of that probability gap:
        </p>
        <ul className="mt-2 space-y-1">
          {gradeScale.map(b => (
            <li key={b.grade} className="flex items-baseline gap-2 text-sm">
              <span className="w-6 font-mono font-bold text-zinc-100">{b.grade}</span>
              <span className="text-zinc-400">
                {b.grade === '-' ? 'below 1.5' : `${b.min_edge_pp}+`} percentage points — {b.label}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <p className="border-t border-terminal-border/70 pt-3 text-xs text-zinc-500">
        Model version <span className="font-mono">{modelVersion}</span>. A grade is a measure of
        disagreement with the market, not a guarantee — nothing public reliably beats a closing line.
      </p>
    </div>
  )
}
