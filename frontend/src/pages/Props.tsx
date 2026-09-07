import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { PropsTable } from '../components/props/PropsTable'
import { DataFreshnessBadge } from '../components/game/DataFreshnessBadge'
import type { FootballLeague, GamePropsOut, TodayResponse } from '../types'

const LEAGUES: { id: FootballLeague; label: string }[] = [
  { id: 'ncaaf', label: 'NCAAF' },
  { id: 'nfl', label: 'NFL' },
]

const pill = (active: boolean) =>
  `tap inline-flex items-center rounded-full px-4 text-sm font-bold transition ${
    active ? 'bg-brand text-white shadow-card' : 'bg-terminal-muted text-zinc-400 hover:text-zinc-100'
  }`

/**
 * Player props.
 *
 * Projections are real — each player's published per-game usage rescaled by the
 * score the model projects for his team. What is missing is a posted prop line
 * to compare them against, and the page says so rather than implying an edge.
 */
export function Props() {
  const [params, setParams] = useSearchParams()
  const league = (params.get('league') as FootballLeague) || 'ncaaf'
  const eventId = params.get('event') || ''

  const [slate, setSlate] = useState<TodayResponse | null>(null)
  const [data, setData] = useState<GamePropsOut | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let alive = true
    api.today(league)
      .then(d => { if (alive) setSlate(d) })
      .catch((e: Error) => { if (alive) setError(e.message) })
    return () => { alive = false }
  }, [league])

  useEffect(() => {
    if (!eventId) { setData(null); return }
    let alive = true
    setLoading(true)
    api.gameProps(league, eventId)
      .then(d => { if (alive) { setData(d); setError(null) } })
      .catch((e: Error) => { if (alive) setError(e.message) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [league, eventId])

  const games = slate?.games ?? []

  const [homeRows, awayRows] = useMemo(() => {
    if (!data) return [[], []]
    return [
      data.projections.filter(p => p.team_abbr === data.home_abbr),
      data.projections.filter(p => p.team_abbr === data.away_abbr),
    ]
  }, [data])

  const setParam = (k: string, v: string) => {
    const next = new URLSearchParams(params)
    if (v) next.set(k, v); else next.delete(k)
    if (k === 'league') next.delete('event')
    setParams(next)
  }

  return (
    <div className="mx-auto w-full max-w-app px-4 py-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-black text-zinc-100">Player props</h1>
          <p className="mt-1 max-w-2xl text-sm text-zinc-400">
            Passing, rushing and receiving projections, built from each player’s published
            usage and scaled to the game the model expects.
          </p>
        </div>
        {data && (
          <DataFreshnessBadge
            fetchedAt={data.fetched_at} source={data.source}
            ok={data.source_ok} staleAfterSeconds={900}
          />
        )}
      </header>

      <div className="mt-4 flex flex-wrap gap-2">
        {LEAGUES.map(l => (
          <button key={l.id} type="button" onClick={() => setParam('league', l.id)}
            aria-pressed={league === l.id} className={pill(league === l.id)}>
            {l.label}
          </button>
        ))}
      </div>

      <div className="mt-3 max-w-md">
        <label htmlFor="props-game" className="block text-xs font-bold uppercase tracking-wide text-zinc-500">
          Game
        </label>
        <select
          id="props-game"
          value={eventId}
          onChange={e => setParam('event', e.target.value)}
          className="tap mt-1 w-full rounded-lg border border-terminal-border bg-terminal-muted px-3 text-sm text-zinc-100 focus:border-brand focus:bg-terminal-surface"
        >
          <option value="">Choose a game…</option>
          {games.map(({ game: g }) => (
            <option key={g.event_id} value={g.event_id}>
              {g.away} at {g.home}{g.state === 'in' ? ' — live' : ''}
            </option>
          ))}
        </select>
      </div>

      <p className="mt-4 rounded-lg border border-terminal-border bg-terminal-muted px-3 py-2 text-sm leading-relaxed text-zinc-500">
        These are projections, not prices. StatEdge has no source of posted player-prop
        lines, so nothing here is compared to a sportsbook number and no prop edge is
        claimed. Players without enough published usage are left out rather than estimated.
      </p>

      {error && <p role="alert" className="mt-5 text-sm text-signal-red">{error}</p>}

      {loading && (
        <div className="mt-5 grid gap-3 lg:grid-cols-2">
          {[0, 1].map(i => <div key={i} className="skeleton h-64 rounded-card" />)}
        </div>
      )}

      {!eventId && !loading && (
        <p className="mt-6 text-sm text-zinc-400">
          Pick a game above to see its projections, or{' '}
          <Link to="/" className="font-semibold text-brand hover:underline">browse the slate</Link>.
        </p>
      )}

      {data && !loading && data.projections.length === 0 && (
        <p className="mt-6 rounded-card border border-terminal-border bg-terminal-muted p-5 text-sm leading-relaxed text-zinc-400">
          No player has enough published usage for this game yet. Early in a season, or for
          a team the feed covers thinly, there is nothing solid to project from — so nothing
          is shown rather than a guess.
        </p>
      )}

      {data && !loading && data.projections.length > 0 && (
        <>
          {data.status !== 'pre' && (
            <p className="mt-5 rounded-lg border border-signal-amber/40 bg-signal-amber-dim px-3 py-2 text-sm font-semibold text-signal-amber">
              This game is under way, so these are actual statistics so far — not projections.
            </p>
          )}
          <div className="mt-5 grid gap-3 lg:grid-cols-2">
            <PropsTable teamAbbr={data.away_abbr} teamName={data.away} rows={awayRows} />
            <PropsTable teamAbbr={data.home_abbr} teamName={data.home} rows={homeRows} />
          </div>
          <p className="mt-4 text-xs leading-relaxed text-zinc-500">
            {data.note} Model version <span className="font-mono">{data.model_version}</span>.
          </p>
        </>
      )}
    </div>
  )
}
