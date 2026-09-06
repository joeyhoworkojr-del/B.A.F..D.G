import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { TodayResponse, TodayGameOut, FootballLeague } from '../types'

const LEAGUES: { id: FootballLeague; label: string }[] = [
  { id: 'ncaaf', label: 'NCAAF' },
  { id: 'nfl', label: 'NFL' },
]

const fmtSpread = (s?: number | null) =>
  s == null ? '—' : s > 0 ? `+${s}` : `${s}`
const fmtML = (m?: number | null) =>
  m == null ? '—' : m > 0 ? `+${m}` : `${m}`

function StateBadge({ g }: { g: TodayGameOut['game'] }) {
  if (g.state === 'in') {
    const clock = g.clock ? `${g.period ? `Q${g.period} ` : ''}${g.clock}` : g.detail
    return (
      <span className="inline-flex items-center gap-1.5 text-[11px] font-bold text-signal-green">
        <span className="h-1.5 w-1.5 rounded-full bg-signal-green animate-pulse" />
        {clock}
      </span>
    )
  }
  if (g.state === 'post')
    return <span className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500">Final</span>
  // pre — show kickoff time (fall back to ESPN's own label if unparseable)
  let t = g.detail
  const d = new Date(g.kickoff)
  if (!isNaN(d.getTime())) {
    t = d.toLocaleString(undefined, { weekday: 'short', hour: 'numeric', minute: '2-digit' })
  }
  return <span className="text-[11px] font-medium text-zinc-400">{t}</span>
}

function TeamLine({
  name, abbr, logo, score, live, favored,
}: { name: string; abbr: string; logo?: string; score?: number | null; live: boolean; favored: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      {logo
        ? <img src={logo} alt="" className="h-6 w-6 object-contain" loading="lazy" />
        : <span className="grid h-6 w-6 place-items-center rounded bg-terminal-muted text-[10px] font-bold text-zinc-400">{abbr.slice(0, 3)}</span>}
      <span className={`truncate text-sm font-semibold ${favored ? 'text-zinc-100' : 'text-zinc-300'}`}>{name}</span>
      {live || score != null ? (
        <span className="ml-auto font-mono text-base font-bold text-zinc-100 tabular-nums">{score ?? 0}</span>
      ) : null}
    </div>
  )
}

/** One market column (Spread / Total / Money) with a home + away cell. */
function OddsCol({ top, bottom }: { top: string; bottom: string }) {
  const Cell = ({ v }: { v: string }) =>
    v === '—' ? (
      <div className="grid h-8 place-items-center text-zinc-600">🔒</div>
    ) : (
      <div className="grid h-8 place-items-center rounded-md border border-terminal-border bg-terminal-muted/60 text-[12px] font-semibold text-signal-amber tabular-nums">
        {v}
      </div>
    )
  return (
    <div className="flex w-[52px] shrink-0 flex-col gap-1.5 sm:w-[64px]">
      <Cell v={top} />
      <Cell v={bottom} />
    </div>
  )
}

function GameCard({ entry, league }: { entry: TodayGameOut; league: FootballLeague }) {
  const g = entry.game
  const live = g.state === 'in'
  const m = entry.model
  const spread = g.market_spread
  const ou = g.market_over_under
  const homeFav = spread != null ? spread < 0 : (m ? (m.calibrated_home_win ?? m.home_win_prob) >= 0.5 : false)

  // Model overlay: projected score + confidence + best edge (A/B only)
  const projHome = m?.proj_home_score
  const projAway = m?.proj_away_score
  const winPct = m ? Math.round(100 * (m.calibrated_home_win ?? m.home_win_prob)) : null
  const pick = m ? (homeFav ? g.home_abbr || g.home : g.away_abbr || g.away) : null
  const pickPct = winPct == null ? null : homeFav ? winPct : 100 - winPct
  const topEdge = entry.edges.find(e => e.rating === 'A' || e.rating === 'B')

  return (
    <Link
      to={`/game/${league}/${g.event_id}`}
      className="block rounded-xl border border-terminal-border bg-terminal-surface p-3 transition hover:border-signal-green/40"
    >
      <div className="flex items-start gap-3">
        {/* Teams + state */}
        <div className="min-w-0 flex-1 space-y-2">
          <TeamLine name={g.away} abbr={g.away_abbr} logo={g.away_logo} score={g.away_score} live={live || g.state === 'post'} favored={!homeFav} />
          <TeamLine name={g.home} abbr={g.home_abbr} logo={g.home_logo} score={g.home_score} live={live || g.state === 'post'} favored={homeFav} />
          <div className="flex items-center gap-2 pt-0.5">
            <StateBadge g={g} />
            {g.possession_abbr && live && (
              <span className="rounded bg-terminal-muted px-1.5 py-0.5 text-[9px] font-bold text-signal-amber">🏈 {g.possession_abbr}</span>
            )}
          </div>
        </div>

        {/* Odds columns */}
        <div className="flex shrink-0 gap-1.5">
          <OddsCol
            top={spread != null ? fmtSpread(-spread) : '—'}
            bottom={spread != null ? fmtSpread(spread) : '—'}
          />
          <OddsCol
            top={ou != null ? `O ${ou}` : '—'}
            bottom={ou != null ? `U ${ou}` : '—'}
          />
          <OddsCol
            top={fmtML(g.market_away_ml)}
            bottom={fmtML(g.market_home_ml)}
          />
        </div>
      </div>

      {/* Model overlay strip */}
      {m && (
        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-terminal-border/70 pt-2 text-[11px]">
          <span className="font-bold uppercase tracking-widest text-signal-green">Model</span>
          {projAway != null && projHome != null && (
            <span className="font-mono text-zinc-300 tabular-nums">
              proj {g.away_abbr} {projAway} – {projHome} {g.home_abbr}
            </span>
          )}
          {pick && pickPct != null && (
            <span className="text-zinc-400">
              lean <span className="font-semibold text-zinc-100">{pick} {pickPct}%</span>
            </span>
          )}
          {topEdge && (
            <span className="ml-auto rounded-full bg-signal-amber-dim px-2 py-0.5 font-bold text-signal-amber">
              EDGE {topEdge.rating} · {topEdge.selection}
            </span>
          )}
        </div>
      )}
    </Link>
  )
}

export function Dashboard() {
  const [league, setLeague] = useState<FootballLeague>('ncaaf')
  const [data, setData] = useState<TodayResponse | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback((lg: FootballLeague) => {
    api.today(lg)
      .then(d => { setData(d); setError('') })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    setLoading(true)
    setData(null)
    load(league)
    const iv = setInterval(() => load(league), 30_000)   // live refresh
    return () => clearInterval(iv)
  }, [league, load])

  const games = data?.games ?? []
  const liveCount = games.filter(x => x.game.state === 'in').length

  return (
    <div className="mx-auto max-w-3xl px-3 py-4 sm:px-4">
      {/* Sport tabs */}
      <div className="mb-4 flex items-center gap-2">
        {LEAGUES.map(l => (
          <button
            key={l.id}
            onClick={() => setLeague(l.id)}
            className={`rounded-full px-4 py-1.5 text-sm font-bold transition ${
              league === l.id
                ? 'bg-zinc-100 text-terminal-bg'
                : 'bg-terminal-surface text-zinc-400 hover:text-zinc-100'
            }`}
          >
            {l.label}
          </button>
        ))}
        {liveCount > 0 && (
          <span className="ml-auto inline-flex items-center gap-1.5 text-xs font-bold text-signal-green">
            <span className="h-1.5 w-1.5 rounded-full bg-signal-green animate-pulse" />
            {liveCount} live
          </span>
        )}
      </div>

      {/* Column headers */}
      <div className="mb-2 flex items-center px-3 text-[10px] font-bold uppercase tracking-wider text-zinc-500">
        <span className="flex-1">{league === 'ncaaf' ? 'College Football' : 'NFL'}</span>
        <div className="flex gap-1.5">
          <span className="w-[52px] text-center sm:w-[64px]">Spread</span>
          <span className="w-[52px] text-center sm:w-[64px]">Total</span>
          <span className="w-[52px] text-center sm:w-[64px]">Money</span>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-signal-red/40 bg-terminal-surface p-4 text-sm text-signal-red">
          Couldn’t load the slate: {error}
        </div>
      )}

      {loading && !data && (
        <div className="space-y-3">
          {[0, 1, 2, 3].map(i => <div key={i} className="skeleton h-28 rounded-xl" />)}
        </div>
      )}

      {!loading && games.length === 0 && !error && (
        <div className="rounded-xl border border-dashed border-terminal-border bg-terminal-surface p-10 text-center">
          <p className="font-display text-lg font-bold text-zinc-100">No games on the board</p>
          <p className="mx-auto mt-1 max-w-sm text-sm text-zinc-500">
            There are no {league === 'ncaaf' ? 'college football' : 'NFL'} games in today’s window.
            Check back on game day — live scores, lines, and model projections appear here automatically.
          </p>
        </div>
      )}

      <div className="space-y-2.5">
        {games.map(entry => (
          <GameCard key={entry.game.event_id} entry={entry} league={league} />
        ))}
      </div>

      {data && (
        <p className="mt-4 text-center text-[10px] text-zinc-600">
          Live lines &amp; scores via ESPN{data.market_source ? ` · book: ${data.market_source}` : ''} · model auto-refreshes every 30s
        </p>
      )}
    </div>
  )
}
