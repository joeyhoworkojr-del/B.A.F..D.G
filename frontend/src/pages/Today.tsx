import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { TodayResponse, TodayGameOut, GridironLeague } from '../types'
import { RatingChip } from '../components/EdgesTable'

const LEAGUES: { id: GridironLeague; label: string }[] = [
  { id: 'mlb', label: '⚾ MLB' },
  { id: 'nfl', label: '🏈 NFL' },
  { id: 'cfl', label: '🍁 CFL' },
]

function pct(p: number): string { return `${Math.round(p * 100)}%` }

function mlToStr(ml?: number | null): string {
  if (ml == null) return '—'
  return ml > 0 ? `+${ml}` : `${ml}`
}

function impliedFromMl(ml?: number | null): number | null {
  if (ml == null || ml === 0) return null
  const dec = ml > 0 ? 1 + ml / 100 : 1 + 100 / Math.abs(ml)
  return 1 / dec
}

function GameCard({ entry }: { entry: TodayGameOut }) {
  const g = entry.game
  const m = entry.model
  const live = g.state === 'in'
  const done = g.state === 'post'
  const marketHome = impliedFromMl(g.market_home_ml)
  const topEdges = entry.edges.filter(e => e.edge_pp >= 1.5).slice(0, 3)

  return (
    <div className={`rounded-xl border p-4 space-y-3 ${live ? 'border-signal-green/40' : 'border-terminal-border'} bg-terminal-surface`}>
      {/* Header: teams + live state */}
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="font-display font-semibold text-sm text-zinc-100 truncate">
            {g.away} <span className="text-zinc-600">@</span> {g.home}
          </p>
          <p className={`text-[11px] font-body ${live ? 'text-signal-green' : 'text-zinc-500'}`}>
            {live && <span className="inline-block h-1.5 w-1.5 rounded-full bg-signal-green animate-pulse mr-1.5 align-middle" />}
            {g.detail}
          </p>
        </div>
        {(live || done) && (
          <div className="font-mono text-xl text-signal-amber whitespace-nowrap">
            {g.away_score ?? 0}–{g.home_score ?? 0}
          </div>
        )}
      </div>

      {!entry.mapped || !m ? (
        <p className="text-xs text-zinc-600 font-body">No model coverage for this matchup.</p>
      ) : (
        <>
          {/* Model vs market on the moneyline */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-[10px] font-display uppercase tracking-widest text-zinc-600">
              <span>Model: {g.home_abbr} {pct(m.home_win_prob)}</span>
              {marketHome != null && <span>Money: {g.home_abbr} {pct(marketHome)} ({mlToStr(g.market_home_ml)})</span>}
            </div>
            <div className="relative h-2 rounded-full bg-signal-red/40 overflow-hidden">
              <div className="absolute inset-y-0 left-0 bg-signal-blue" style={{ width: `${m.home_win_prob * 100}%` }} />
              {marketHome != null && (
                <div
                  className="absolute inset-y-0 w-0.5 bg-signal-amber"
                  title={`Market-implied ${pct(marketHome)}`}
                  style={{ left: `${marketHome * 100}%` }}
                />
              )}
            </div>
            <p className="text-[10px] font-mono text-zinc-600">
              blue = model ({g.home_abbr} win) · <span className="text-signal-amber">| market money</span>
              {marketHome != null && m && Math.abs(m.home_win_prob - marketHome) >= 0.04 && (
                <span className={m.home_win_prob > marketHome ? ' text-signal-green' : ' text-signal-red'}>
                  {' '}· model {m.home_win_prob > marketHome ? 'likes' : 'fades'} {g.home_abbr} vs the public
                </span>
              )}
            </p>
          </div>

          {/* Expected score + totals vs market line */}
          <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[11px] text-zinc-400">
            <span>Proj: {g.away_abbr} {m.away_expected.toFixed(1)} @ {g.home_abbr} {m.home_expected.toFixed(1)}</span>
            {g.market_over_under != null && (
              <span>
                O/U {g.market_over_under}: <span className={m.over_prob >= 0.55 ? 'text-signal-green' : m.over_prob <= 0.45 ? 'text-signal-red' : ''}>Over {pct(m.over_prob)}</span>
              </span>
            )}
            {g.market_spread != null && (
              <span>{g.home_abbr} {g.market_spread > 0 ? `+${g.market_spread}` : g.market_spread}: cover {pct(m.home_cover_prob)}</span>
            )}
          </div>

          {/* Edge chips */}
          {topEdges.length > 0 && (
            <div className="flex flex-wrap gap-2 pt-1">
              {topEdges.map((e, i) => (
                <span key={i} className="flex items-center gap-1.5 rounded-lg border border-terminal-border bg-terminal-muted/30 px-2 py-1">
                  <RatingChip rating={e.rating} />
                  <span className="text-[11px] font-body text-zinc-300">{e.selection}</span>
                  <span className="text-[10px] font-mono text-signal-green">+{e.edge_pp.toFixed(1)}pp</span>
                </span>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

export function Today() {
  const [league, setLeague] = useState<GridironLeague>('mlb')
  const [data, setData] = useState<TodayResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (lg: GridironLeague) => {
    setLoading(true)
    setError(null)
    try {
      setData(await api.today(lg))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load slate')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(league)
    const iv = setInterval(() => load(league), 120_000)
    return () => clearInterval(iv)
  }, [league, load])

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-100">
          Today — <span className="text-signal-amber">Model vs the Money</span>
        </h1>
        <p className="text-sm text-zinc-500 mt-1 font-body">
          Every game on today's board, auto-predicted with live weather and lineups, side by side
          with the live sportsbook market — see where the model disagrees with the public's money.
        </p>
      </div>

      <div className="flex items-center gap-3">
        {LEAGUES.map(l => (
          <button
            key={l.id}
            onClick={() => setLeague(l.id)}
            className={`px-4 py-1.5 rounded-lg text-sm font-display font-medium transition-colors ${
              league === l.id
                ? 'bg-signal-amber text-terminal-bg'
                : 'bg-terminal-surface border border-terminal-border text-zinc-400 hover:text-zinc-100'
            }`}
          >
            {l.label}
          </button>
        ))}
        {data && (
          <span className="ml-auto text-[10px] font-mono text-zinc-600">
            {data.market_source ? `market: ${data.market_source} · ` : ''}updated {data.fetched_at.slice(11, 19)} UTC
          </span>
        )}
      </div>

      {loading && (
        <div className="rounded-xl border border-terminal-border bg-terminal-surface p-8 text-center">
          <p className="text-sm text-zinc-500 font-body animate-pulse">Predicting today's slate…</p>
        </div>
      )}

      {error && <p className="text-sm text-signal-red font-body">{error}</p>}

      {!loading && data && data.games.length === 0 && (
        <div className="rounded-xl border border-terminal-border bg-terminal-surface p-8 text-center">
          <p className="text-sm text-zinc-400 font-body">
            No {league.toUpperCase()} games on the board today{data.source_ok ? '' : ' (live feed temporarily unreachable)'}.
          </p>
        </div>
      )}

      {!loading && data && data.games.map(entry => (
        <GameCard key={entry.game.event_id} entry={entry} />
      ))}

      <p className="text-[10px] text-zinc-600 italic">
        Market lines from the live ESPN feed; totals/spread edges assume −110 pricing. Probabilities, not promises — bet responsibly.
      </p>
    </div>
  )
}
