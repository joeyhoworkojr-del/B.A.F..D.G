import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import type { GamePropsOut, PropMarketOut, PropProjectionOut } from '../../types'

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

/**
 * What a projection is made of, in one line.
 *
 * A projection with nothing behind it is an assertion. This says where it came
 * from: the season average, where recent form pulled it, how volatile the
 * player actually is and whether that spread is his own or a league-wide
 * stand-in. The spread is the part that matters most — the whole over/under
 * probability comes out of it, and two players with the same average and
 * different spreads are not the same bet.
 */
function Provenance({ row }: { row: PropProjectionOut }) {
  const bits: string[] = [`season ${row.season_avg.toFixed(1)}`]

  if (row.recent_avg != null && row.form_weight) {
    bits.push(`last games ${row.recent_avg.toFixed(1)}`)
  }
  if (row.opponent_mult != null && row.opponent_mult !== 1 && row.opponent_abbr) {
    const harder = row.opponent_mult < 1
    bits.push(`vs ${row.opponent_abbr} ${harder ? '−' : '+'}${Math.abs((row.opponent_mult - 1) * 100).toFixed(0)}%`)
  }
  if (row.sigma != null) {
    // Said plainly, including when it is a stand-in rather than his own.
    bits.push(
      row.sigma_source === 'player'
        ? `± ${row.sigma.toFixed(1)} over ${row.sigma_games} games`
        : `± ${row.sigma.toFixed(1)} (market average spread)`,
    )
  }

  if (bits.length <= 1) return null
  return (
    <p className="mt-0.5 font-mono text-[11px] tabular-nums leading-relaxed text-zinc-500">
      {bits.join(' · ')}
    </p>
  )
}

const american = (v: number) => (v > 0 ? `+${Math.round(v)}` : `${Math.round(v)}`)

/**
 * The posted line beside the projection, and what the gap is worth.
 *
 * This is the part that makes a projection a bet rather than a statistic. The
 * four numbers stay four numbers for the same reason they do on the game
 * lines: the model's probability, what the price alone needs, the expected
 * value, and which book is paying it. A single score out of a hundred would
 * read as a chance of winning, which none of them is.
 */
function PostedLine({ market }: { market: PropMarketOut }) {
  const best = market.best
  if (!best) return null
  const edge = market.difference

  return (
    <div className="mt-1 rounded-lg bg-terminal-muted/40 px-2 py-1.5">
      <p className="font-mono text-[11px] tabular-nums text-zinc-300">
        {/* A yes-or-no market has no line, and showing a zero gap would read
            as agreement rather than as not applicable. */}
        {market.posted_line != null && edge != null ? (
          <>
            line {market.posted_line.toFixed(1)}
            <span className={edge >= 0 ? 'text-brand' : 'text-signal-red'}>
              {' '}({edge >= 0 ? '+' : ''}{edge.toFixed(1)})
            </span>
            {' · '}
          </>
        ) : (
          <span className="font-sans text-zinc-500">no line · </span>
        )}
        <span className="font-sans font-bold uppercase">{best.side}</span>
        {' '}{american(best.price_american)}
        <span className="text-zinc-500"> at {best.book}</span>
        {market.books > 1 && (
          <span className="text-zinc-500"> of {market.books}</span>
        )}
      </p>
      <p className="mt-0.5 font-mono text-[11px] tabular-nums text-zinc-500">
        model {(best.model_prob * 100).toFixed(1)}% · break-even{' '}
        {(best.break_even_prob * 100).toFixed(1)}% ·{' '}
        <span className={best.ev_per_unit >= 0 ? 'text-signal-green' : 'text-signal-red'}>
          {best.ev_per_unit >= 0 ? '+' : ''}{(best.ev_per_unit * 100).toFixed(1)}% EV
        </span>
      </p>
    </div>
  )
}

function hasLine(m: PropProjectionOut['posted']): m is PropMarketOut {
  return !!m && 'best' in m && !!m.best
}

function PlayerRow({ row, actual }: { row: PropProjectionOut; actual: boolean }) {
  return (
    <li className="flex items-start gap-3 py-2.5">
      <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-full bg-terminal-muted text-[11px] font-bold text-zinc-400">
        {row.team_abbr.slice(0, 3)}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-bold text-zinc-100">{row.player}</p>
        <p className="text-xs text-zinc-500">{row.position} · {row.label}</p>
        {/* An actual is a fact and has no projection to explain. */}
        {!actual && <Provenance row={row} />}
        {!actual && hasLine(row.posted) && <PostedLine market={row.posted} />}
      </div>
      <div className="shrink-0 text-right">
        {/* Anytime touchdown is a chance, not a quantity. "0.5 touchdowns" is
            not a thing anyone bets on; "39% to score" is. */}
        <p className="font-mono text-xl font-black tabular-nums text-zinc-100">
          {!actual && row.yes_prob != null
            ? `${Math.round(row.yes_prob * 100)}%`
            : row.projection.toFixed(1)}
        </p>
        <p className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
          {actual ? 'actual' : row.yes_prob != null ? 'to score' : 'projected'}
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
