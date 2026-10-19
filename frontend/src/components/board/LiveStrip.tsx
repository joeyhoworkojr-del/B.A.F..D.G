import { Link } from 'react-router-dom'
import type { BoardEntry } from '../../types'

/**
 * Games in progress, across the top.
 *
 * Only ever rendered when something is actually live. An empty strip with a
 * green dot above it implies the opposite of what is true, and a row of
 * placeholder cards on a Tuesday is worse than no row.
 */
export function LiveStrip({ games }: { games: BoardEntry[] }) {
  if (games.length === 0) return null

  return (
    <section aria-labelledby="live-strip">
      <div className="mb-2 flex items-center justify-between gap-3">
        <h2 id="live-strip" className="flex items-center gap-2 text-base font-bold text-zinc-100">
          <span className="h-2 w-2 animate-pulse rounded-full bg-brand" />
          Live games
        </h2>
        {games.length > 3 && (
          <span className="text-xs font-semibold text-zinc-500">
            {games.length} in progress
          </span>
        )}
      </div>

      <ul className="flex gap-2.5 overflow-x-auto pb-1 no-scrollbar">
        {games.map(({ game: g, league }) => (
          <li key={`${league}-${g.event_id}`} className="shrink-0">
            <Link
              to={`/game/${league}/${g.event_id}`}
              state={{ game: g }}
              className="tap block w-[168px] rounded-card border border-terminal-border bg-terminal-surface p-3 hover:border-brand/50"
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="truncate text-xs font-bold text-brand">
                  {g.period ? `Q${g.period} ` : ''}{g.clock || g.detail}
                </span>
                {g.market_provider && (
                  <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
                    {league.toUpperCase()}
                  </span>
                )}
              </div>
              {([['away', g.away_abbr, g.away_logo, g.away_score],
                 ['home', g.home_abbr, g.home_logo, g.home_score]] as const).map(
                ([side, abbr, logo, score]) => (
                  <div key={side} className="mt-2 flex items-center gap-2">
                    {logo
                      ? <img src={logo} alt="" className="h-5 w-5 object-contain" loading="lazy" />
                      : <span className="h-5 w-5 rounded bg-terminal-muted" aria-hidden="true" />}
                    <span className="truncate text-sm font-bold text-zinc-100">{abbr}</span>
                    <span className="ml-auto font-mono text-lg font-black tabular-nums text-zinc-100">
                      {score ?? 0}
                    </span>
                  </div>
                ),
              )}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}
