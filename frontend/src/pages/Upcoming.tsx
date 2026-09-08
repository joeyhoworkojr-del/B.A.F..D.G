import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { DataFreshnessBadge } from '../components/game/DataFreshnessBadge'
import type { FootballLeague, TodayGameOut, UpcomingResponse } from '../types'

const LEAGUES: FootballLeague[] = ['ncaaf', 'nfl']
const DAY_CHOICES = [3, 7, 14] as const
const LEAGUE_LABEL: Record<FootballLeague, string> = { ncaaf: 'College', nfl: 'NFL' }

const pct = (v?: number | null) => (v == null ? '—' : `${Math.round(v * 100)}%`)

interface Entry { league: FootballLeague; entry: TodayGameOut }

function dayKey(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? 'Scheduled' : d.toDateString()
}

function dayLabel(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return 'Kickoff time to be confirmed'
  return d.toLocaleDateString(undefined, {
    weekday: 'long', month: 'short', day: 'numeric',
  })
}

function kickoffTime(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime())
    ? 'TBD'
    : d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

/** One scheduled game with the projection already attached. */
function UpcomingRow({ league, entry }: Entry) {
  const g = entry.game
  const m = entry.model
  const homeWin = m?.calibrated_home_win ?? m?.home_win_prob ?? null
  const favourite =
    homeWin == null ? null : homeWin >= 0.5 ? g.home_abbr : g.away_abbr
  const favProb = homeWin == null ? null : Math.max(homeWin, 1 - homeWin)

  return (
    <Link
      to={`/game/${league}/${g.event_id}`}
      state={{ game: g }}
      className="block min-w-0 rounded-card border border-terminal-border bg-terminal-surface p-4 card-lift"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-xs font-bold text-zinc-500">
          {kickoffTime(g.kickoff)}
        </span>
        <span className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
          {league === 'ncaaf' ? 'NCAAF' : 'NFL'}
        </span>
      </div>

      <div className="mt-2 space-y-1.5">
        {([[g.away, g.away_abbr], [g.home, g.home_abbr]] as const).map(([name, abbr]) => (
          <div key={abbr} className="flex items-center gap-2.5">
            <span className="grid h-6 w-9 shrink-0 place-items-center rounded bg-terminal-muted text-xs font-bold text-zinc-400">
              {abbr}
            </span>
            <span className="truncate text-sm font-bold text-zinc-100">{name}</span>
          </div>
        ))}
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-3 border-t border-terminal-border pt-3 text-sm">
        <div>
          <dt className="text-xs text-zinc-400">Model favourite</dt>
          <dd className="font-mono font-bold tabular-nums text-zinc-100">
            {favourite ? `${favourite} ${pct(favProb)}` : 'Not modelled'}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-zinc-400">Projected score</dt>
          <dd className="font-mono font-bold tabular-nums text-zinc-100">
            {m
              ? `${(m.proj_away_score ?? m.away_expected).toFixed(0)}–${(m.proj_home_score ?? m.home_expected).toFixed(0)}`
              : '—'}
          </dd>
        </div>
      </dl>

      {!entry.mapped && (
        <p className="mt-2 text-xs text-zinc-500">
          One of these teams is not in the ratings, so there is no projection for this game.
        </p>
      )}
    </Link>
  )
}

/**
 * The week ahead.
 *
 * Every scheduled game is fetched with its projection already computed, so
 * this page renders predictions rather than promising them. Where a game has
 * no projection — an unmapped team — it says so instead of showing a blank
 * that reads as a missing number.
 */
export function Upcoming() {
  const [days, setDays] = useState<number>(7)
  // Which leagues to show. Both by default; a filter narrows what is already
  // fetched rather than refetching, so switching it is instant.
  const [leagues, setLeagues] = useState<FootballLeague[]>(LEAGUES)
  // A specific day, or null for the whole window.
  const [day, setDay] = useState<string | null>(null)
  const [feeds, setFeeds] = useState<Record<string, UpcomingResponse>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    setLoading(true)
    Promise.allSettled(LEAGUES.map(lg => api.upcoming(lg, days)))
      .then(results => {
        if (!alive) return
        const next: Record<string, UpcomingResponse> = {}
        let failures = 0
        results.forEach((r, i) => {
          if (r.status === 'fulfilled') next[LEAGUES[i]] = r.value
          else failures++
        })
        setFeeds(next)
        setError(failures === LEAGUES.length ? 'Both league schedules are unreachable.' : null)
        setLoading(false)
      })
    return () => { alive = false }
  }, [days])

  const byDay = useMemo(() => {
    const all: Entry[] = leagues.flatMap(lg =>
      (feeds[lg]?.games ?? []).map(entry => ({ league: lg, entry })))
    all.sort((a, b) => (a.entry.game.kickoff || '').localeCompare(b.entry.game.kickoff || ''))
    const groups = new Map<string, Entry[]>()
    for (const row of all) {
      const key = dayKey(row.entry.game.kickoff)
      groups.set(key, [...(groups.get(key) ?? []), row])
    }
    return [...groups.entries()]
  }, [feeds, leagues])

  // Every day that actually has a game, so the picker never offers an empty one.
  const availableDays = byDay.map(([key, rows]) => ({
    key, label: dayLabel(rows[0].entry.game.kickoff), count: rows.length,
  }))
  const visibleDays = day ? byDay.filter(([key]) => key === day) : byDay

  const toggleLeague = (lg: FootballLeague) => {
    setLeagues(prev => {
      const next = prev.includes(lg) ? prev.filter(l => l !== lg) : [...prev, lg]
      // Turning the last one off would leave an empty page with no way back.
      return next.length ? next : prev
    })
  }

  const responses = Object.values(feeds)
  const oldest = responses.map(f => f.fetched_at).filter(Boolean).sort()[0]
  const sourceOk = responses.length > 0 && responses.every(f => f.source_ok)
  const truncated = responses.filter(f => f.truncated)
  const totalScheduled = responses.reduce((n, f) => n + f.total_scheduled, 0)
  const totalPredicted = responses.reduce((n, f) => n + f.predicted, 0)

  return (
    <div className="mx-auto w-full max-w-app px-4 py-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-black text-zinc-100">Upcoming</h1>
          <p className="mt-1 text-sm text-zinc-400">
            Every scheduled NFL and college game in the next {days} days, each with the
            model's pre-game call.
          </p>
        </div>
        <DataFreshnessBadge fetchedAt={oldest} ok={sourceOk} source="ESPN" />
      </header>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="text-xs font-bold uppercase tracking-wide text-zinc-500">League</span>
        {LEAGUES.map(lg => (
          <button
            key={lg}
            type="button"
            onClick={() => toggleLeague(lg)}
            aria-pressed={leagues.includes(lg)}
            className={`tap rounded-full border px-3 text-sm font-semibold transition ${
              leagues.includes(lg)
                ? 'border-brand bg-brand-soft text-brand'
                : 'border-terminal-border bg-terminal-surface text-zinc-500 hover:text-zinc-100'
            }`}
          >
            {LEAGUE_LABEL[lg]}
          </button>
        ))}
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-2">
        <span className="text-xs font-bold uppercase tracking-wide text-zinc-500">Window</span>
        {DAY_CHOICES.map(d => (
          <button
            key={d}
            type="button"
            onClick={() => setDays(d)}
            aria-pressed={days === d}
            className={`tap rounded-full border px-3 text-sm font-semibold transition ${
              days === d
                ? 'border-brand bg-brand-soft text-brand'
                : 'border-terminal-border bg-terminal-surface text-zinc-400 hover:text-zinc-100'
            }`}
          >
            {d} days
          </button>
        ))}
      </div>

      {error && <p role="alert" className="mt-5 text-sm text-signal-red">{error}</p>}

      {loading && byDay.length === 0 && (
        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2, 3, 4, 5].map(i => <div key={i} className="skeleton h-44 rounded-card" />)}
        </div>
      )}

      {!loading && byDay.length === 0 && !error && (
        <p className="mt-6 text-sm text-zinc-400">
          Nothing is scheduled in the next {days} days.
        </p>
      )}

      {truncated.length > 0 && (
        <p className="mt-5 rounded-lg border border-signal-amber/40 bg-signal-amber-dim px-3 py-2 text-sm text-signal-amber">
          {totalPredicted} of {totalScheduled} scheduled games are projected here. A full
          college slate is several hundred games, so the board is capped at the earliest
          kickoffs — open a game directly for its projection.
        </p>
      )}

      {availableDays.length > 1 && (
        <div className="mt-3 flex gap-1.5 overflow-x-auto pb-1 no-scrollbar">
          <button
            type="button"
            onClick={() => setDay(null)}
            aria-pressed={day === null}
            className={`tap shrink-0 rounded-lg border px-3 text-sm font-semibold transition ${
              day === null
                ? 'border-brand bg-brand-soft text-brand'
                : 'border-terminal-border bg-terminal-surface text-zinc-400 hover:text-zinc-100'
            }`}
          >
            All {days} days
          </button>
          {availableDays.map(d => (
            <button
              key={d.key}
              type="button"
              onClick={() => setDay(d.key === day ? null : d.key)}
              aria-pressed={day === d.key}
              className={`tap shrink-0 whitespace-nowrap rounded-lg border px-3 text-sm font-semibold transition ${
                day === d.key
                  ? 'border-brand bg-brand-soft text-brand'
                  : 'border-terminal-border bg-terminal-surface text-zinc-400 hover:text-zinc-100'
              }`}
            >
              {d.label} <span className="text-zinc-500">({d.count})</span>
            </button>
          ))}
        </div>
      )}

      {visibleDays.map(([key, rows]) => (
        <section key={key} className="mt-8">
          <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-500">
            {dayLabel(rows[0].entry.game.kickoff)} · {rows.length} game{rows.length === 1 ? '' : 's'}
          </h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {rows.map(row => (
              <UpcomingRow key={`${row.league}:${row.entry.game.event_id}`} {...row} />
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
