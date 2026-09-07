import { Link } from 'react-router-dom'
import type { GameCommunityOut } from '../../types'

/**
 * What the community has committed to on this game.
 *
 * Percentages appear only once real picks exist. An empty game gets an
 * invitation, never a fabricated 50/50 — a consensus nobody voted in is worse
 * than no consensus at all.
 */
export function GameCommunity({
  data, homeAbbr, awayAbbr,
}: { data: GameCommunityOut | null; homeAbbr: string; awayAbbr: string }) {
  if (!data) return <div className="skeleton h-32 rounded-card" />

  // A partial payload must not take the game page down: the community block is
  // additive, so missing fields degrade to the empty state.
  const split = data.moneyline_split ?? {}
  const analysis = data.recent_analysis ?? []
  const totalPicks = data.total_picks ?? 0
  const hasSplit = Object.keys(split).length > 0

  return (
    <section aria-labelledby="community" className="rounded-card border border-terminal-border bg-terminal-surface">
      <header className="flex items-baseline justify-between border-b border-terminal-border px-4 py-3">
        <h2 id="community" className="text-sm font-bold text-zinc-100">Community</h2>
        <span className="text-xs text-zinc-500">
          {totalPicks} {totalPicks === 1 ? 'prediction' : 'predictions'}
        </span>
      </header>

      <div className="space-y-4 p-4">
        {!hasSplit ? (
          <p className="text-sm leading-relaxed text-zinc-400">
            {totalPicks === 0
              ? 'Be one of the first analysts to make your pick on this matchup.'
              : 'Not enough moneyline picks yet to show a split.'}
          </p>
        ) : (
          <div className="space-y-2">
            {([['away', awayAbbr], ['home', homeAbbr]] as const).map(([side, abbr]) => {
              const pct = split[side] ?? 0
              return (
                <div key={side}>
                  <div className="flex items-baseline justify-between text-sm">
                    <span className="font-semibold text-zinc-100">{abbr}</span>
                    <span className="font-mono tabular-nums text-zinc-400">{pct.toFixed(0)}%</span>
                  </div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-terminal-muted">
                    <div className="prob-fill h-full rounded-full bg-signal-blue" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              )
            })}
            <p className="text-xs text-zinc-500">
              Share of community moneyline picks. Not a model output.
            </p>
          </div>
        )}

        {analysis.length > 0 && (
          <div className="border-t border-terminal-border pt-3">
            <h3 className="text-xs font-bold uppercase tracking-wide text-zinc-500">Recent analysis</h3>
            <ul className="mt-2 space-y-3">
              {analysis.map((a, i) => (
                <li key={`${a.username}-${i}`}>
                  <div className="flex flex-wrap items-baseline gap-2 text-sm">
                    <Link to={`/@${a.username}`} className="font-mono font-semibold text-brand hover:underline">
                      @{a.username}
                    </Link>
                    <span className="font-semibold text-zinc-100">{a.selection}</span>
                    <span className="text-xs text-zinc-500">{a.confidence}%</span>
                  </div>
                  <p className="mt-1 text-sm leading-relaxed text-zinc-400">{a.reasoning}</p>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  )
}
