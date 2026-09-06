import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { AllScoreboardsOut, LiveGameOut } from '../types'

const LABEL: Record<string, string> = { nfl: 'NFL', ncaaf: 'NCAAF' }

function Item({ g }: { g: LiveGameOut }) {
  const live = g.state === 'in'
  const done = g.state === 'post'
  return (
    <Link
      to={`/game/${g.league}/${g.event_id}`}
      className="flex items-center gap-2 whitespace-nowrap border-r border-terminal-border/70 px-4 py-1.5 hover:bg-terminal-muted/60"
    >
      <span className="text-[9px] font-bold uppercase tracking-wider text-zinc-600">{LABEL[g.league] ?? g.league}</span>
      <span className="font-mono text-xs text-zinc-200">
        {g.away_abbr || g.away} {done || live ? g.away_score ?? 0 : ''} @ {g.home_abbr || g.home} {done || live ? g.home_score ?? 0 : ''}
      </span>
      {live && <span className="h-1.5 w-1.5 rounded-full bg-signal-green animate-pulse" />}
      <span className={`text-[10px] ${live ? 'text-signal-green' : 'text-zinc-500'}`}>
        {live ? `${g.period ? `Q${g.period} ` : ''}${g.clock || g.detail}` : g.detail}
      </span>
      {g.market_details && (
        <span className="text-[10px] font-mono text-signal-amber">{g.market_details}</span>
      )}
    </Link>
  )
}

/** Scrolling scores tape across the top — NFL + NCAA football. */
export function TickerTape() {
  const [games, setGames] = useState<LiveGameOut[]>([])

  useEffect(() => {
    const load = () =>
      api.liveScores()
        .then((b: AllScoreboardsOut) =>
          setGames(Object.values(b.boards).flatMap(x => x.games).filter(g => g.state !== 'pre' || g.market_details)))
        .catch(() => {})
    load()
    const iv = setInterval(load, 60_000)
    return () => clearInterval(iv)
  }, [])

  if (games.length === 0) return null
  const doubled = [...games, ...games]   // seamless loop
  // Keep a calm, readable pace no matter how many games are on the board:
  // ~7s of travel per game, so a big Saturday slate doesn't whip past.
  const duration = Math.min(600, Math.max(90, games.length * 7))

  return (
    <div className="ticker-mask overflow-hidden border-b border-terminal-border bg-terminal-surface/70">
      <div className="ticker-track" style={{ animationDuration: `${duration}s` }}>
        {doubled.map((g, i) => <Item key={`${g.league}-${g.event_id}-${i}`} g={g} />)}
      </div>
    </div>
  )
}
