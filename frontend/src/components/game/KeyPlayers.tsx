import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import type { GamePropsOut, PropProjectionOut } from '../../types'

/** The groups a football page reads in, and the markets that belong to each. */
const GROUPS: { label: string; markets: string[] }[] = [
  { label: 'Passing', markets: ['pass_yards'] },
  { label: 'Rushing', markets: ['rush_yards'] },
  { label: 'Receiving', markets: ['rec_yards'] },
]

/** The leading projection per team in a group — one name a side, as a comparison. */
function pair(rows: PropProjectionOut[], markets: string[], away: string, home: string) {
  const inGroup = rows
    .filter(r => markets.includes(r.market))
    .sort((a, b) => b.projection - a.projection)
  const pick = (abbr: string) => inGroup.find(r => r.team_abbr === abbr) ?? null
  return [pick(away), pick(home)].filter(Boolean) as PropProjectionOut[]
}

function PlayerRow({ row, actual }: { row: PropProjectionOut; actual: boolean }) {
  return (
    <li className="flex items-center gap-3 py-2.5">
      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-terminal-muted text-[11px] font-bold text-zinc-400">
        {row.team_abbr.slice(0, 3)}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-bold text-zinc-100">{row.player}</p>
        <p className="text-xs text-zinc-500">{row.position} · {row.label}</p>
      </div>
      <div className="shrink-0 text-right">
        <p className="font-mono text-xl font-black tabular-nums text-zinc-100">
          {row.projection.toFixed(1)}
        </p>
        <p className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
          {actual ? 'actual' : 'projected'}
        </p>
      </div>
    </li>
  )
}

/**
 * Key players, by position group.
 *
 * These are the model's projections — each player's published per-game usage
 * rescaled to the game StatEdge expects — not posted prop lines, and the
 * labels say which. Once a game is under way the same rows report what has
 * actually happened, which is a different claim and is marked differently.
 */
export function KeyPlayers({ league, eventId }: { league: string; eventId: string }) {
  const [data, setData] = useState<GamePropsOut | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let alive = true
    setData(null)
    setFailed(false)
    api.gameProps(league, eventId)
      .then(d => { if (alive) setData(d) })
      .catch(() => { if (alive) setFailed(true) })
    return () => { alive = false }
  }, [league, eventId])

  const rows = data?.projections ?? []
  const groups = GROUPS
    .map(g => ({ ...g, rows: pair(rows, g.markets, data?.away_abbr ?? '', data?.home_abbr ?? '') }))
    .filter(g => g.rows.length > 0)

  if (failed || (data && groups.length === 0)) {
    return (
      <section className="rounded-card border border-terminal-border bg-terminal-surface p-4">
        <h2 className="text-base font-bold text-zinc-100">Key players</h2>
        <p className="mt-1.5 text-sm text-zinc-500">
          No player projections for this game yet. They need published per-game usage
          for these teams, which arrives once a season has games in it.
        </p>
      </section>
    )
  }

  return (
    <section aria-labelledby="key-players" className="rounded-card border border-terminal-border bg-terminal-surface">
      <div className="flex items-baseline justify-between gap-3 px-4 pt-4">
        <h2 id="key-players" className="text-base font-bold text-zinc-100">Key players</h2>
        <Link
          to={`/props?league=${league}&event=${encodeURIComponent(eventId)}`}
          className="text-sm font-semibold text-brand hover:underline"
        >
          Full comparison ›
        </Link>
      </div>

      {!data && <div className="space-y-2 p-4"><div className="skeleton h-14 rounded-lg" /><div className="skeleton h-14 rounded-lg" /></div>}

      {groups.map(group => (
        <div key={group.label} className="border-t border-terminal-border/70 px-4 first:border-t-0">
          <p className="pt-3 text-xs font-bold uppercase tracking-widest text-zinc-500">
            {group.label}
          </p>
          <ul className="divide-y divide-terminal-border/60">
            {group.rows.map(row => (
              <PlayerRow key={`${row.athlete_id}-${row.market}`} row={row} actual={row.actual} />
            ))}
          </ul>
        </div>
      ))}

      {data && (
        <p className="border-t border-terminal-border px-4 py-2.5 text-xs leading-relaxed text-zinc-500">
          {data.status === 'pre'
            ? 'Projections from published per-game usage, scaled to the score the model expects. These are not posted prop lines.'
            : 'Actual production so far in this game.'}
        </p>
      )}
    </section>
  )
}
