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

function volume(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}k`
  return `$${v.toFixed(0)}`
}

function Marker({ at, color, label }: { at: number; color: string; label: string }) {
  return (
    <div
      className={`absolute -top-1 -bottom-1 w-[3px] rounded ${color}`}
      title={label}
      style={{ left: `calc(${Math.min(99, Math.max(1, at * 100))}% - 1.5px)` }}
    />
  )
}

function SignalLegend({ items }: { items: Array<{ dot: string; text: string } | null> }) {
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] font-mono text-zinc-500">
      {items.filter(Boolean).map((it, i) => (
        <span key={i} className="flex items-center gap-1">
          <span className={`inline-block h-2 w-2 rounded-sm ${it!.dot}`} />
          {it!.text}
        </span>
      ))}
    </div>
  )
}

function GameCard({ entry }: { entry: TodayGameOut }) {
  const g = entry.game
  const m = entry.model
  const pm = entry.polymarket
  const live = g.state === 'in'
  const done = g.state === 'post'
  const bookHome = impliedFromMl(g.market_home_ml)
  const topEdges = entry.edges.filter(e => e.edge_pp >= 1.5).slice(0, 3)
  const [open, setOpen] = useState(false)

  return (
    <div className={`card-lift rounded-xl border p-4 space-y-3 ${live ? 'border-signal-green/40' : 'border-terminal-border'} bg-terminal-surface`}>
      {/* Header */}
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
        <p className="text-xs text-zinc-600 font-body">
          No model coverage for this matchup{pm ? ' — but the crowd has a price:' : '.'}
          {pm && (
            <a href={pm.url} target="_blank" rel="noreferrer" className="ml-1 text-signal-purple hover:underline">
              {g.home_abbr || 'home'} {pct(pm.home_prob)} on Polymarket ({volume(pm.volume_usd)} traded)
            </a>
          )}
        </p>
      ) : (
        <>
          {/* Three signals, one scale: model fill, book marker, crowd marker */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-[10px] font-display uppercase tracking-widest text-zinc-600">
              <span>{g.home_abbr} win probability</span>
              <span className="text-zinc-500">{pct(m.home_win_prob)} model</span>
            </div>
            <div className="relative h-2.5 rounded-full bg-signal-red/30 overflow-visible">
              <div className="absolute inset-0 rounded-full overflow-hidden">
                <div className="prob-fill absolute inset-y-0 left-0 bg-signal-blue" style={{ width: `${m.home_win_prob * 100}%` }} />
              </div>
              {bookHome != null && <Marker at={bookHome} color="bg-signal-amber" label={`Sportsbook ${pct(bookHome)} (${mlToStr(g.market_home_ml)})`} />}
              {pm && <Marker at={pm.home_prob} color="bg-signal-purple" label={`Polymarket crowd ${pct(pm.home_prob)} · ${volume(pm.volume_usd)} traded`} />}
            </div>
            <SignalLegend items={[
              { dot: 'bg-signal-blue', text: `model ${pct(m.home_win_prob)}` },
              bookHome != null ? { dot: 'bg-signal-amber', text: `book ${pct(bookHome)} (${mlToStr(g.market_home_ml)})` } : null,
              pm ? { dot: 'bg-signal-purple', text: `crowd ${pct(pm.home_prob)} · ${volume(pm.volume_usd)}` } : null,
            ]} />
            {pm && Math.abs(m.home_win_prob - pm.home_prob) >= 0.05 && (
              <p className="text-[10px] font-mono">
                <span className={m.home_win_prob > pm.home_prob ? 'text-signal-green' : 'text-signal-red'}>
                  model {m.home_win_prob > pm.home_prob ? 'likes' : 'fades'} {g.home_abbr} vs the crowd's money
                </span>
                {' · '}
                <a href={pm.url} target="_blank" rel="noreferrer" className="text-signal-purple hover:underline">view market ↗</a>
              </p>
            )}
          </div>

          {/* Projection + market lines */}
          <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[11px] text-zinc-400">
            <span title="Model projected score">
              Proj: {g.away_abbr} {m.away_expected.toFixed(1)} @ {g.home_abbr} {m.home_expected.toFixed(1)}
            </span>
            {g.market_over_under != null && (
              <span title="Model probability the game goes over the market total">
                O/U {g.market_over_under}: <span className={m.over_prob >= 0.55 ? 'text-signal-green' : m.over_prob <= 0.45 ? 'text-signal-red' : ''}>Over {pct(m.over_prob)}</span>
              </span>
            )}
            {g.market_spread != null && (
              <span title="Model probability the home side covers the market spread">
                {g.home_abbr} {g.market_spread > 0 ? `+${g.market_spread}` : g.market_spread}: cover {pct(m.home_cover_prob)}
              </span>
            )}
          </div>

          {/* Edge chips + expandable detail */}
          {topEdges.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 pt-1">
              {topEdges.map((e, i) => (
                <span key={i} className="flex items-center gap-1.5 rounded-lg border border-terminal-border bg-terminal-muted/30 px-2 py-1">
                  <RatingChip rating={e.rating} />
                  <span className="text-[11px] font-body text-zinc-300">{e.selection}</span>
                  <span className="text-[10px] font-mono text-signal-green">+{e.edge_pp.toFixed(1)}pp</span>
                </span>
              ))}
              {entry.edges.length > 0 && (
                <button
                  onClick={() => setOpen(o => !o)}
                  className="text-[10px] font-display uppercase tracking-widest text-zinc-500 hover:text-zinc-300"
                >
                  {open ? 'hide detail ▲' : 'all markets ▼'}
                </button>
              )}
            </div>
          )}

          {open && (
            <div className="border-t border-terminal-muted/40 pt-2 space-y-1">
              {entry.edges.map((e, i) => (
                <div key={i} className="flex items-center justify-between text-[11px] font-mono">
                  <span className="text-zinc-400 truncate">{e.selection} <span className="text-zinc-600">· {e.market}</span></span>
                  <span className="flex items-center gap-2 shrink-0">
                    <span className="text-zinc-500">mdl {pct(e.model_prob)}</span>
                    <span className="text-zinc-600">mkt {pct(e.market_prob)}</span>
                    <span className={e.edge_pp >= 1.5 ? 'text-signal-green' : e.edge_pp <= -1.5 ? 'text-signal-red' : 'text-zinc-500'}>
                      {e.edge_pp >= 0 ? '+' : ''}{e.edge_pp.toFixed(1)}pp
                    </span>
                  </span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

function CardSkeleton() {
  return (
    <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4 space-y-3">
      <div className="skeleton h-4 w-2/3" />
      <div className="skeleton h-2.5 w-full" />
      <div className="skeleton h-3 w-1/2" />
    </div>
  )
}

export function Today() {
  const [league, setLeague] = useState<GridironLeague>('mlb')
  const [data, setData] = useState<TodayResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (lg: GridironLeague, silent = false) => {
    if (!silent) setLoading(true)
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
    const iv = setInterval(() => load(league, true), 120_000)
    return () => clearInterval(iv)
  }, [league, load])

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-100">
          Today — <span className="text-signal-amber">Model vs the Money</span>
        </h1>
        <p className="text-sm text-zinc-500 mt-1 font-body">
          Every game on today's board, auto-predicted with live weather and lineups. Three signals
          on one scale: <span className="text-signal-blue">the model</span>,{' '}
          <span className="text-signal-amber">the sportsbook</span>, and{' '}
          <span className="text-signal-purple">Polymarket's real-money crowd</span>.
        </p>
      </div>

      <div className="flex items-center gap-3">
        {LEAGUES.map(l => (
          <button
            key={l.id}
            onClick={() => setLeague(l.id)}
            className={`px-4 py-1.5 rounded-lg text-sm font-display font-medium ${
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
            {data.market_source ? `book: ${data.market_source} · ` : ''}updated {data.fetched_at.slice(11, 19)} UTC
          </span>
        )}
      </div>

      {loading && (
        <div className="space-y-3">
          <CardSkeleton /><CardSkeleton /><CardSkeleton />
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
        Book lines from the live ESPN feed; crowd prices from Polymarket (real-money prediction market);
        totals/spread edges assume −110 pricing. Probabilities, not promises — bet responsibly.
      </p>
    </div>
  )
}
