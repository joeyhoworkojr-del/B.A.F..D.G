import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import type { GamePropsOut, PropProjectionOut } from '../../types'

/** How many projections fit on the homepage before it stops being a strip. */
const SHOWN = 6

/**
 * Which projections are worth putting in front of someone who did not ask for
 * props. Passing yards dwarf everything else numerically, so ordering by the
 * number would show four quarterbacks; ordering by market keeps a quarterback,
 * a back and a receiver from each side.
 */
const MARKET_RANK: Record<string, number> = {
  pass_yards: 0, rush_yards: 1, rec_yards: 2, receptions: 3,
}

function ranked(projections: PropProjectionOut[]): PropProjectionOut[] {
  const seen = new Set<string>()
  return [...projections]
    .sort((a, b) => {
      const ra = MARKET_RANK[a.market] ?? 9
      const rb = MARKET_RANK[b.market] ?? 9
      return ra !== rb ? ra - rb : b.projection - a.projection
    })
    // One line per player: the same name three times is a table, not a strip.
    .filter(p => (seen.has(p.player) ? false : (seen.add(p.player), true)))
    .slice(0, SHOWN)
}

/**
 * Player projections for the game at the top of the board.
 *
 * These are projections, not posted prop lines — the label says so, because a
 * number beside a player's name reads as a betting line unless it is told not
 * to. Nothing renders at all if this game has no projections, rather than
 * leaving an empty heading behind.
 */
export function PropsStrip({ league, eventId }: { league: string; eventId: string }) {
  const [data, setData] = useState<GamePropsOut | null>(null)

  useEffect(() => {
    let alive = true
    setData(null)
    api.gameProps(league, eventId)
      .then(d => { if (alive) setData(d) })
      .catch(() => { if (alive) setData(null) })
    return () => { alive = false }
  }, [league, eventId])

  // A deployment without a projection source answers with an empty body rather
  // than a list, so the field is treated as optional here instead of trusted.
  const rows = ranked(data?.projections ?? [])
  if (rows.length === 0) return null

  return (
    <section aria-labelledby="props-strip" className="space-y-2.5">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 id="props-strip" className="text-xs font-bold uppercase tracking-widest text-zinc-500">
            Player projections
          </h2>
          <p className="mt-0.5 text-xs text-zinc-500">
            {/* Named from the response rather than from what was asked for: if
              the two ever disagree, the wrong label is worse than none. */}
          {data?.away_abbr} @ {data?.home_abbr} —{' '}
          {data?.status === 'pre' ? 'projected' : 'actual'} numbers, not posted lines
          </p>
        </div>
        <Link
          to={`/props?league=${league}&event=${encodeURIComponent(eventId)}`}
          className="whitespace-nowrap text-sm font-semibold text-brand hover:underline"
        >
          All props ›
        </Link>
      </div>
      <ul className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
        {rows.map(p => (
          <li
            key={`${p.athlete_id}-${p.market}`}
            className="min-w-[150px] shrink-0 rounded-xl border border-terminal-border bg-terminal-surface px-3 py-2.5"
          >
            <p className="truncate text-sm font-bold text-zinc-100">{p.player}</p>
            <p className="text-xs text-zinc-500">{p.team_abbr} · {p.position} · {p.label}</p>
            <p className="mt-1 font-mono text-lg font-black tabular-nums text-zinc-100">
              {p.projection.toFixed(1)}
            </p>
          </li>
        ))}
      </ul>
    </section>
  )
}
