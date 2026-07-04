import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { AllScoreboardsOut, TodayResponse, EdgeOut } from '../types'
import { RatingChip } from '../components/EdgesTable'

const LEAGUE_META: Record<string, { label: string; icon: string }> = {
  wc: { label: 'World Cup', icon: '⚽' },
  mlb: { label: 'MLB', icon: '⚾' },
  nfl: { label: 'NFL', icon: '🏈' },
  cfl: { label: 'CFL', icon: '🍁' },
}

interface DashEdge extends EdgeOut {
  league: string
  matchup: string
}

function Tile({ to, icon, title, desc }: { to: string; icon: string; title: string; desc: string }) {
  return (
    <Link to={to} className="card-lift block rounded-xl border border-terminal-border bg-terminal-surface p-4">
      <div className="text-2xl">{icon}</div>
      <p className="font-display font-semibold text-zinc-100 mt-2">{title}</p>
      <p className="text-xs text-zinc-500 font-body mt-1">{desc}</p>
    </Link>
  )
}

export function Dashboard() {
  const [boards, setBoards] = useState<AllScoreboardsOut | null>(null)
  const [edges, setEdges] = useState<DashEdge[] | null>(null)

  useEffect(() => {
    const load = () => {
      api.liveScores().then(setBoards).catch(() => {})
      Promise.allSettled((['mlb', 'nfl', 'cfl'] as const).map(lg => api.today(lg)))
        .then(results => {
          const all: DashEdge[] = []
          results.forEach(r => {
            if (r.status !== 'fulfilled') return
            const t: TodayResponse = r.value
            t.games.forEach(g => {
              g.edges.forEach(e => {
                if (e.edge_pp >= 2.5) {
                  all.push({ ...e, league: t.league, matchup: `${g.game.away_abbr} @ ${g.game.home_abbr}` })
                }
              })
            })
          })
          all.sort((a, b) => b.edge_pp - a.edge_pp)
          setEdges(all.slice(0, 6))
        })
    }
    load()
    const iv = setInterval(load, 120_000)
    return () => clearInterval(iv)
  }, [])

  const liveGames = boards
    ? Object.values(boards.boards).flatMap(b => b.games.filter(g => g.state === 'in').map(g => ({ ...g })))
    : []
  const anyGames = boards
    ? Object.values(boards.boards).some(b => b.games.length > 0)
    : false

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 space-y-8">
      {/* Hero */}
      <div className="text-center space-y-3 py-6">
        <h1 className="font-display text-4xl font-bold tracking-tight">
          <span className="text-signal-amber">STAT</span><span className="text-zinc-100">EDGE</span>
        </h1>
        <p className="text-zinc-400 font-body max-w-xl mx-auto">
          Honest win and over/under probabilities for the World Cup, NFL, CFL, and MLB —
          adjusted live for weather and lineups, and measured against the sportsbook
          and Polymarket's real-money crowd.
        </p>
        <div className="flex justify-center gap-3 pt-1">
          <Link to="/today" className="rounded-lg bg-signal-amber px-5 py-2 font-display font-semibold text-terminal-bg hover:bg-amber-400">
            ⚡ Today's slate
          </Link>
          <Link to="/best-bets" className="rounded-lg border border-terminal-border bg-terminal-surface px-5 py-2 font-display font-semibold text-zinc-200 hover:border-signal-amber">
            Best bets
          </Link>
        </div>
      </div>

      {/* Live now */}
      {liveGames.length > 0 && (
        <div className="rounded-xl border border-signal-green/40 bg-signal-green/5 p-4 space-y-2">
          <p className="text-[10px] font-display uppercase tracking-widest text-signal-green">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-signal-green animate-pulse mr-1.5 align-middle" />
            Live right now
          </p>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {liveGames.map(g => (
              <div key={`${g.league}-${g.event_id}`} className="shrink-0 rounded-lg border border-terminal-border bg-terminal-surface px-3 py-1.5">
                <div className="font-mono text-xs text-zinc-300">
                  {LEAGUE_META[g.league]?.icon} {g.away_abbr} {g.away_score} @ {g.home_abbr} {g.home_score}
                </div>
                <div className="text-[10px] text-signal-green font-body">{g.detail}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top edges */}
      <div className="space-y-2">
        <div className="flex items-baseline justify-between">
          <h2 className="font-display text-sm uppercase tracking-widest text-zinc-400">
            Biggest model-vs-market gaps right now
          </h2>
          <Link to="/today" className="text-xs font-body text-signal-amber hover:underline">full slate →</Link>
        </div>
        {edges === null ? (
          <div className="grid gap-2 sm:grid-cols-2">
            <div className="skeleton h-14" /><div className="skeleton h-14" />
          </div>
        ) : edges.length === 0 ? (
          <div className="rounded-xl border border-terminal-border bg-terminal-surface p-5 text-center">
            <p className="text-sm text-zinc-500 font-body">
              {anyGames
                ? 'Model and markets agree on today\'s board — check back as lines move.'
                : 'No games with live markets on the board right now.'}
            </p>
          </div>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2">
            {edges.map((e, i) => (
              <Link key={i} to="/today" className="card-lift flex items-center gap-3 rounded-xl border border-terminal-border bg-terminal-surface px-3 py-2.5">
                <RatingChip rating={e.rating} />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-body text-zinc-200 truncate">{e.selection}</p>
                  <p className="text-[10px] font-mono text-zinc-600">{LEAGUE_META[e.league]?.icon} {e.matchup} · {e.market}</p>
                </div>
                <span className="font-mono text-sm text-signal-green shrink-0">+{e.edge_pp.toFixed(1)}pp</span>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Predictors */}
      <div className="space-y-2">
        <h2 className="font-display text-sm uppercase tracking-widest text-zinc-400">Predictors</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Tile to="/soccer" icon="⚽" title="World Cup" desc="Dixon-Coles engine, team news, venue weather, any-line goals totals." />
          <Tile to="/nfl" icon="🏈" title="NFL" desc="Expected points, spread covers, totals at any line, QB scratches." />
          <Tile to="/cfl" icon="🍁" title="CFL" desc="Three-down scoring model with prairie wind and QB availability." />
          <Tile to="/mlb" icon="⚾" title="MLB" desc="Poisson runs with park factors — Coors included. Starting pitchers matter." />
        </div>
      </div>

      {/* Footer links */}
      <div className="flex justify-center gap-6 pt-4 border-t border-terminal-border text-xs font-body text-zinc-500">
        <Link to="/rankings" className="hover:text-zinc-200">Power rankings</Link>
        <Link to="/history" className="hover:text-zinc-200">Prediction history</Link>
        <Link to="/about" className="hover:text-zinc-200">About the models</Link>
      </div>
    </div>
  )
}
