import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type {
  AllScoreboardsOut, TodayResponse, EdgeOut, AccuracyResponse, TodayGameOut, GridironLeague,
} from '../types'
import { RatingChip } from '../components/EdgesTable'
import { Sparkline } from '../components/Sparkline'

const LEAGUE_META: Record<string, { label: string; icon: string }> = {
  wc: { label: 'Soccer', icon: '⚽' },
  mlb: { label: 'MLB', icon: '⚾' },
  nfl: { label: 'NFL', icon: '🏈' },
  cfl: { label: 'CFL', icon: '🍁' },
}

interface DashEdge extends EdgeOut {
  league: string
  matchup: string
}

function pct(p?: number | null): string {
  return p == null ? '—' : `${Math.round(p * 100)}%`
}

function ml(v?: number | null): string {
  if (v == null) return '—'
  return v > 0 ? `+${v}` : `${v}`
}

function Stat({ label, value, good }: { label: string; value: string; good?: boolean }) {
  return (
    <div className="rounded-xl border border-terminal-border bg-terminal-surface px-4 py-3">
      <p className="text-[10px] font-display uppercase tracking-widest text-zinc-500">{label}</p>
      <p className={`font-display text-xl font-bold mt-0.5 ${good ? 'text-signal-green' : 'text-zinc-100'}`}>{value}</p>
    </div>
  )
}

export function Dashboard() {
  const [boards, setBoards] = useState<AllScoreboardsOut | null>(null)
  const [slates, setSlates] = useState<Record<string, TodayResponse>>({})
  const [edges, setEdges] = useState<DashEdge[] | null>(null)
  const [acc, setAcc] = useState<AccuracyResponse | null>(null)
  const [boardLeague, setBoardLeague] = useState<GridironLeague>('mlb')

  useEffect(() => {
    const load = () => {
      api.liveScores().then(setBoards).catch(() => {})
      api.accuracy().then(setAcc).catch(() => {})
      Promise.allSettled((['mlb', 'nfl', 'cfl'] as const).map(lg => api.today(lg)))
        .then(results => {
          const all: DashEdge[] = []
          const byLeague: Record<string, TodayResponse> = {}
          results.forEach(r => {
            if (r.status !== 'fulfilled') return
            const t = r.value
            byLeague[t.league] = t
            t.games.forEach(g => {
              g.edges.forEach(e => {
                if (e.edge_pp >= 2.5) {
                  all.push({ ...e, league: t.league, matchup: `${g.game.away_abbr} @ ${g.game.home_abbr}` })
                }
              })
            })
          })
          all.sort((a, b) => b.edge_pp - a.edge_pp)
          setEdges(all.slice(0, 5))
          setSlates(byLeague)
        })
    }
    load()
    const iv = setInterval(load, 120_000)
    return () => clearInterval(iv)
  }, [])

  const liveGames = boards
    ? Object.values(boards.boards).flatMap(b => b.games.filter(g => g.state === 'in'))
    : []
  const perf = acc?.performance
  const board = slates[boardLeague]
  const boardGames: TodayGameOut[] = (board?.games ?? []).filter(g => g.game.market_spread != null || g.game.market_home_ml != null).slice(0, 5)
  const projCards = Object.values(slates)
    .flatMap(t => t.games.filter(g => g.mapped && g.model && g.game.market_spread != null))
    .slice(0, 4)

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 space-y-8">
      {/* ── Hero + Model performance card ── */}
      <div className="grid gap-6 lg:grid-cols-2 items-center">
        <div className="space-y-4 py-4">
          <h1 className="font-display text-5xl font-bold leading-tight tracking-tight">
            <span className="text-zinc-100">Smarter bets.</span><br />
            <span className="text-signal-amber">Real edge.</span>
          </h1>
          <p className="text-zinc-400 font-body max-w-md">
            Data-driven sports analysis with real market tracking and model projections —
            the sportsbook, the Polymarket crowd, and our engine on one screen.
          </p>
          <div className="flex gap-3 pt-1">
            <Link to="/today" className="rounded-xl bg-signal-amber px-5 py-2.5 font-display font-semibold text-white hover:bg-blue-700 shadow-sm">
              ⚡ Today's Edge
            </Link>
            <Link to="/best-bets" className="rounded-xl border border-terminal-border bg-terminal-surface px-5 py-2.5 font-display font-semibold text-zinc-200 hover:border-signal-amber">
              Best Bets
            </Link>
          </div>
          <p className="text-xs text-zinc-500 font-body">
            🛡 Every pick snapshotted pre-game and auto-graded — <Link to="/track" className="text-signal-amber hover:underline">see the verified track record</Link>.
          </p>
        </div>

        {/* Model performance (real, from the graded ledger) */}
        <div className="card-lift rounded-2xl border border-terminal-border bg-terminal-surface p-5 space-y-4">
          <div className="flex items-baseline justify-between">
            <p className="font-display font-semibold text-zinc-100">Model P/L <span className="text-zinc-500 font-normal text-sm">(all sports, units)</span></p>
            <Link to="/track" className="text-xs font-body text-signal-amber hover:underline">details →</Link>
          </div>
          <div>
            <span className={`font-display text-4xl font-bold ${((perf?.profit_units ?? 0) >= 0) ? 'text-signal-green' : 'text-signal-red'}`}>
              {perf?.profit_units != null ? `${perf.profit_units >= 0 ? '+' : ''}${perf.profit_units.toFixed(1)}u` : '—'}
            </span>
            {perf?.roi_pct != null && (
              <span className="ml-2 rounded-lg bg-signal-amber-dim px-2 py-0.5 text-xs font-mono text-signal-amber">
                ROI {perf.roi_pct >= 0 ? '+' : ''}{perf.roi_pct}%
              </span>
            )}
          </div>
          <Sparkline data={perf?.series ?? []} id="dash-pl" />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <Stat label="Graded picks" value={`${perf?.total_picks ?? 0}`} />
            <Stat label="Win rate" value={pct(perf?.win_rate)} good={(perf?.win_rate ?? 0) > 0.5} />
            <Stat label="Avg edge" value={perf?.avg_edge_pp != null ? `${perf.avg_edge_pp >= 0 ? '+' : ''}${perf.avg_edge_pp.toFixed(1)}pp` : '—'} good={(perf?.avg_edge_pp ?? 0) > 0} />
            <Stat label="Pending" value={`${acc?.pending ?? 0}`} />
          </div>
        </div>
      </div>

      {/* ── Live Now ── */}
      {liveGames.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-baseline justify-between">
            <h2 className="font-display font-semibold text-zinc-100">
              Live Now <span className="ml-1 inline-block h-2 w-2 rounded-full bg-signal-green animate-pulse align-middle" />
              <span className="ml-2 text-sm font-normal text-zinc-500">{liveGames.length} in progress</span>
            </h2>
            <Link to="/today" className="text-xs font-body text-signal-amber hover:underline">view all live →</Link>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {liveGames.slice(0, 6).map(g => (
              <Link key={`${g.league}-${g.event_id}`} to="/today" className="card-lift rounded-xl border border-terminal-border bg-terminal-surface p-4">
                <div className="flex items-center justify-between font-display font-semibold text-zinc-100">
                  <span>{g.away_abbr || g.away} <span className="text-signal-amber font-mono">{g.away_score ?? 0}</span></span>
                  <span className="text-zinc-600 text-sm">@</span>
                  <span><span className="text-signal-amber font-mono">{g.home_score ?? 0}</span> {g.home_abbr || g.home}</span>
                </div>
                <div className="flex justify-between mt-1.5 text-[11px] font-body">
                  <span className="text-signal-green">{g.detail}</span>
                  <span className="text-zinc-500">{LEAGUE_META[g.league]?.icon} {LEAGUE_META[g.league]?.label}</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* ── Top Model Edges + Market Board ── */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-terminal-border bg-terminal-surface p-5 space-y-3">
          <div className="flex items-baseline justify-between">
            <h2 className="font-display font-semibold text-zinc-100">Top Model Edges <span className="ml-1 rounded bg-signal-amber-dim px-1.5 py-0.5 text-[10px] font-mono text-signal-amber">LIVE</span></h2>
            <Link to="/today" className="text-xs font-body text-signal-amber hover:underline">view all →</Link>
          </div>
          {edges === null ? (
            <div className="space-y-2"><div className="skeleton h-10" /><div className="skeleton h-10" /><div className="skeleton h-10" /></div>
          ) : edges.length === 0 ? (
            <p className="text-sm text-zinc-500 font-body py-6 text-center">Model and markets agree right now — edges appear as lines move.</p>
          ) : (
            edges.map((e, i) => (
              <Link key={i} to="/today" className="flex items-center gap-3 rounded-xl px-2 py-2 hover:bg-terminal-muted/60">
                <span className="w-5 text-center font-display font-bold text-zinc-500">{i + 1}</span>
                <RatingChip rating={e.rating} />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-body font-medium text-zinc-200 truncate">{e.selection}</p>
                  <p className="text-[10px] font-mono text-zinc-500">{LEAGUE_META[e.league]?.icon} {e.matchup} · {e.market}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="font-display font-bold text-signal-amber">+{e.edge_pp.toFixed(1)}pp</p>
                  <p className="text-[10px] font-mono text-zinc-500">win {pct(e.model_prob)}</p>
                </div>
              </Link>
            ))
          )}
        </div>

        <div className="rounded-2xl border border-terminal-border bg-terminal-surface p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-display font-semibold text-zinc-100">Market Board</h2>
            <div className="flex gap-1">
              {(['mlb', 'nfl', 'cfl'] as GridironLeague[]).map(lg => (
                <button
                  key={lg}
                  onClick={() => setBoardLeague(lg)}
                  className={`rounded-lg px-2.5 py-1 text-xs font-display font-medium ${
                    boardLeague === lg ? 'bg-signal-amber text-white' : 'text-zinc-400 hover:bg-terminal-muted'
                  }`}
                >
                  {LEAGUE_META[lg]?.icon} {lg.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
          {boardGames.length === 0 ? (
            <p className="text-sm text-zinc-500 font-body py-6 text-center">No priced {boardLeague.toUpperCase()} games on the board right now.</p>
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[10px] font-display uppercase tracking-widest text-zinc-500 border-b border-terminal-border">
                  <th className="text-left py-1.5">Game</th>
                  <th className="text-right py-1.5">Spread</th>
                  <th className="text-right py-1.5">Total</th>
                  <th className="text-right py-1.5">ML</th>
                </tr>
              </thead>
              <tbody>
                {boardGames.map(g => (
                  <tr key={g.game.event_id} className="border-b border-terminal-muted/60">
                    <td className="py-2">
                      <p className="font-body font-medium text-zinc-200">{g.game.away_abbr} @ {g.game.home_abbr}</p>
                      <p className="text-[10px] text-zinc-500">{g.game.detail}</p>
                    </td>
                    <td className="text-right font-mono text-zinc-300">
                      {g.game.market_spread != null ? `${g.game.home_abbr} ${g.game.market_spread > 0 ? '+' : ''}${g.game.market_spread}` : '—'}
                    </td>
                    <td className="text-right font-mono text-zinc-300">
                      {g.game.market_over_under != null ? `O ${g.game.market_over_under}` : '—'}
                    </td>
                    <td className="text-right font-mono text-signal-red">{ml(g.game.market_home_ml)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* ── Model Projection vs Market ── */}
      {projCards.length > 0 && (
        <div className="space-y-2">
          <h2 className="font-display font-semibold text-zinc-100">Model Projection vs. Market</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {projCards.map(g => {
              const modelSpread = -(g.model!.home_expected - g.model!.away_expected)
              const edge = g.game.market_spread != null ? g.game.market_spread - modelSpread : null
              return (
                <Link key={g.game.event_id} to="/today" className="card-lift rounded-xl border border-terminal-border bg-terminal-surface p-4 space-y-2">
                  <p className="font-body text-xs text-zinc-500 truncate">{g.game.away_abbr} @ {g.game.home_abbr} · {g.game.detail}</p>
                  <p className="font-display font-bold text-lg text-zinc-100">
                    {g.game.home_abbr} {g.game.market_spread! > 0 ? '+' : ''}{g.game.market_spread}
                  </p>
                  <div className="grid grid-cols-3 text-center text-[11px] font-mono">
                    <div><p className="text-zinc-500">Market</p><p className="text-zinc-200">{g.game.market_spread}</p></div>
                    <div><p className="text-zinc-500">Model</p><p className="text-zinc-200">{modelSpread.toFixed(1)}</p></div>
                    <div><p className="text-zinc-500">Edge</p><p className={edge != null && Math.abs(edge) >= 1 ? 'text-signal-green font-bold' : 'text-zinc-400'}>{edge != null ? `${edge >= 0 ? '+' : ''}${edge.toFixed(1)}` : '—'}</p></div>
                  </div>
                </Link>
              )
            })}
          </div>
        </div>
      )}

      {/* ── Feature strip ── */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 pt-4 border-t border-terminal-border">
        {[
          ['🧠', 'Proprietary models', 'Dixon-Coles soccer, expected-points football, Poisson baseball with park factors.'],
          ['📈', 'Market tracking', 'Live lines from the book plus Polymarket\'s real-money crowd — three signals, one scale.'],
          ['🛡', 'Verified results', 'Every pick snapshotted pre-game and auto-graded against finals.', '/track'],
          ['🌦', 'Live conditions', 'Weather and lineups re-price every prediction the moment news lands.'],
        ].map(([icon, title, desc, to], i) => (
          <div key={i} className="space-y-1">
            <div className="text-xl">{icon}</div>
            <p className="font-display font-semibold text-sm text-zinc-100">{title}</p>
            <p className="text-xs text-zinc-500 font-body">{desc}</p>
            {to && <Link to={to as string} className="text-xs text-signal-amber hover:underline">Learn more →</Link>}
          </div>
        ))}
      </div>

      <div className="flex justify-center gap-6 pt-2 text-xs font-body text-zinc-500">
        <Link to="/rankings" className="hover:text-zinc-200">Power rankings</Link>
        <Link to="/history" className="hover:text-zinc-200">My history</Link>
        <Link to="/about" className="hover:text-zinc-200">About the models</Link>
      </div>
    </div>
  )
}
