import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { DataFreshnessBadge } from '../components/game/DataFreshnessBadge'
import type { FootballLeague, TodayGameOut, TodayResponse } from '../types'

const LEAGUES: FootballLeague[] = ['ncaaf', 'nfl']
const POLL_MS = 20_000

const pct = (v?: number | null) => (v == null ? '—' : `${Math.round(v * 100)}%`)

interface LiveEntry { league: FootballLeague; entry: TodayGameOut }

/**
 * Every in-progress game across both leagues.
 *
 * Freshness is read off each league payload's own `fetched_at`, not off the
 * poll timer: if a refresh fails the last good games stay on screen and their
 * timestamp visibly ages, rather than a spinning clock implying live data.
 */
function useLiveSlate() {
  const [feeds, setFeeds] = useState<Record<string, TodayResponse>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const nonce = useRef(0)

  const refresh = useCallback(() => {
    const mine = ++nonce.current
    Promise.allSettled(LEAGUES.map(lg => api.today(lg)))
      .then(results => {
        if (mine !== nonce.current) return
        const next: Record<string, TodayResponse> = {}
        let failures = 0
        results.forEach((r, i) => {
          if (r.status === 'fulfilled') next[LEAGUES[i]] = r.value
          else failures++
        })
        // Merge rather than replace, so one league failing doesn't blank the other.
        setFeeds(prev => ({ ...prev, ...next }))
        setError(failures === LEAGUES.length ? 'Both league feeds are unreachable.' : null)
        setLoading(false)
      })
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, POLL_MS)
    return () => clearInterval(id)
  }, [refresh])

  const live: LiveEntry[] = LEAGUES.flatMap(lg =>
    (feeds[lg]?.games ?? [])
      .filter(g => g.game.state === 'in')
      .map(entry => ({ league: lg, entry })))

  const oldest = Object.values(feeds)
    .map(f => f.fetched_at)
    .filter(Boolean)
    .sort()[0]

  const sourceOk = Object.values(feeds).every(f => f.source_ok)

  return { live, loading, error, fetchedAt: oldest, sourceOk, hasFeeds: Object.keys(feeds).length > 0 }
}

function LiveRow({ league, entry }: LiveEntry) {
  const g = entry.game
  const model = entry.model
  const homeWin = model
    ? (model.live && model.live_home_win != null ? model.live_home_win
       : (model.calibrated_home_win ?? model.home_win_prob))
    : null

  return (
    <Link
      to={`/game/${league}/${g.event_id}`}
      state={{ game: g }}
      className="block min-w-0 rounded-card border border-signal-green/40 bg-terminal-surface p-4 card-lift"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="inline-flex items-center gap-2 rounded-full bg-signal-green/15 px-2.5 py-1 text-xs font-bold text-signal-green">
          <span className="h-1.5 w-1.5 rounded-full bg-signal-green" />
          LIVE · {g.period ? `Q${g.period} ` : ''}{g.clock || g.detail}
        </span>
        <span className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
          {league === 'ncaaf' ? 'NCAAF' : 'NFL'}
        </span>
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_auto]">
        <div className="min-w-0 space-y-2">
          {([['away', g.away, g.away_abbr, g.away_score],
             ['home', g.home, g.home_abbr, g.home_score]] as const).map(([side, name, abbr, score]) => (
            <div key={side} className="flex items-center gap-2.5">
              <span className="grid h-7 w-9 shrink-0 place-items-center rounded bg-terminal-muted text-xs font-bold text-zinc-400">
                {abbr}
              </span>
              <span className="truncate text-sm font-bold text-zinc-100">{name}</span>
              <span className="ml-auto font-mono text-2xl font-black tabular-nums text-zinc-100">
                {score ?? 0}
              </span>
            </div>
          ))}
        </div>

        {homeWin != null && (
          <div className="shrink-0 border-terminal-border sm:border-l sm:pl-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
              Live win probability
            </p>
            <p className="mt-1 font-mono text-lg font-black tabular-nums text-zinc-100">
              {g.home_abbr} {pct(homeWin)}
            </p>
            <p className="text-xs text-zinc-500">{g.away_abbr} {pct(1 - homeWin)}</p>
          </div>
        )}
      </div>

      {g.down_distance && (
        <p className="mt-3 border-t border-terminal-border pt-2 text-sm text-zinc-400">
          <span className="font-semibold text-zinc-300">{g.possession_abbr ?? ''}</span>{' '}
          {g.down_distance}
        </p>
      )}
      {g.last_play && (
        <p className="mt-1 text-sm leading-relaxed text-zinc-500">{g.last_play}</p>
      )}
    </Link>
  )
}

export function Live() {
  const { live, loading, error, fetchedAt, sourceOk, hasFeeds } = useLiveSlate()

  return (
    <div className="mx-auto w-full max-w-app px-4 py-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-black text-zinc-100">Live</h1>
          <p className="mt-1 text-sm text-zinc-400">
            Every NFL and college football game currently in progress, with the model’s
            in-game win probability.
          </p>
        </div>
        <DataFreshnessBadge
          fetchedAt={fetchedAt}
          source="ESPN"
          ok={sourceOk && !error}
          staleAfterSeconds={90}
        />
      </header>

      {error && (
        <p role="alert" className="mt-5 text-sm text-signal-red">{error}</p>
      )}

      {loading && !hasFeeds && (
        <div className="mt-5 grid gap-3 lg:grid-cols-2">
          {[0, 1].map(i => <div key={i} className="skeleton h-48 rounded-card" />)}
        </div>
      )}

      {hasFeeds && live.length === 0 && (
        <p className="mt-6 rounded-card border border-terminal-border bg-terminal-muted p-5 text-sm text-zinc-400">
          No games are in progress right now. This is an empty schedule, not a broken feed —
          the source last answered {fetchedAt ? 'successfully' : 'without a timestamp'}.{' '}
          <Link to="/" className="font-semibold text-brand hover:underline">See the full slate</Link>.
        </p>
      )}

      {live.length > 0 && (
        <div className="mt-5 grid gap-3 lg:grid-cols-2">
          {live.map(({ league, entry }) => (
            <LiveRow key={`${league}:${entry.game.event_id}`} league={league} entry={entry} />
          ))}
        </div>
      )}
    </div>
  )
}
