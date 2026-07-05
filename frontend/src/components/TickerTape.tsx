import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { AllScoreboardsOut, LiveGameOut } from '../types'

const ICONS: Record<string, string> = { wc: '⚽', mlb: '⚾', nfl: '🏈', cfl: '🍁' }

function Item({ g }: { g: LiveGameOut }) {
  const live = g.state === 'in'
  const done = g.state === 'post'
  return (
    <Link to="/today" className="flex items-center gap-2 px-4 py-1.5 whitespace-nowrap border-r border-terminal-border/70 hover:bg-terminal-muted/60">
      <span>{ICONS[g.league] ?? '•'}</span>
      <span className="font-mono text-xs text-zinc-200">
        {g.away_abbr || g.away} {done || live ? g.away_score ?? 0 : ''} @ {g.home_abbr || g.home} {done || live ? g.home_score ?? 0 : ''}
      </span>
      {live && <span className="h-1.5 w-1.5 rounded-full bg-signal-green animate-pulse" />}
      <span className={`text-[10px] font-body ${live ? 'text-signal-green' : 'text-zinc-500'}`}>{g.detail}</span>
      {g.market_details && (
        <span className="text-[10px] font-mono text-signal-amber">{g.market_details}{g.market_over_under ? ` · O/U ${g.market_over_under}` : ''}</span>
      )}
    </Link>
  )
}

/** Stock-market style scrolling tape of every game + live line, all leagues. */
export function TickerTape() {
  const [games, setGames] = useState<LiveGameOut[]>([])

  useEffect(() => {
    const load = () =>
      api.liveScores()
        .then((b: AllScoreboardsOut) => setGames(Object.values(b.boards).flatMap(x => x.games)))
        .catch(() => {})
    load()
    const iv = setInterval(load, 60_000)
    return () => clearInterval(iv)
  }, [])

  if (games.length === 0) return null
  const doubled = [...games, ...games]   // seamless loop

  return (
    <div className="ticker-mask overflow-hidden border-b border-terminal-border bg-white/70">
      <div className="ticker-track">
        {doubled.map((g, i) => <Item key={`${g.league}-${g.event_id}-${i}`} g={g} />)}
      </div>
    </div>
  )
}
