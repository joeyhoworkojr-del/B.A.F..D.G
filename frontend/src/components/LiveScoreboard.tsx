import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { ScoreboardOut, LiveGameOut } from '../types'

function ago(iso: string): string {
  const s = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000))
  if (s < 90) return `${s}s ago`
  return `${Math.round(s / 60)}m ago`
}

function GameChip({ g }: { g: LiveGameOut }) {
  const live = g.state === 'in'
  const done = g.state === 'post'
  return (
    <div className={`shrink-0 rounded-lg border px-3 py-1.5 ${live ? 'border-signal-green/50 bg-signal-green/5' : 'border-terminal-border bg-terminal-surface'}`}>
      <div className="flex items-center gap-2 font-mono text-xs">
        <span className="text-zinc-300">{g.away_abbr || g.away}</span>
        <span className={done || live ? 'text-signal-amber' : 'text-zinc-600'}>
          {g.away_score ?? '–'}
        </span>
        <span className="text-zinc-600">@</span>
        <span className="text-zinc-300">{g.home_abbr || g.home}</span>
        <span className={done || live ? 'text-signal-amber' : 'text-zinc-600'}>
          {g.home_score ?? '–'}
        </span>
      </div>
      <div className="flex items-center gap-2 mt-0.5">
        {live && <span className="h-1.5 w-1.5 rounded-full bg-signal-green animate-pulse" />}
        <span className={`text-[10px] font-body ${live ? 'text-signal-green' : 'text-zinc-500'}`}>{g.detail}</span>
        {g.market_details && (
          <span className="text-[10px] font-mono text-zinc-600">· {g.market_details}{g.market_over_under ? ` O/U ${g.market_over_under}` : ''}</span>
        )}
      </div>
    </div>
  )
}

export function LiveScoreboard({ league, title }: { league: string; title?: string }) {
  const [board, setBoard] = useState<ScoreboardOut | null>(null)
  const [, force] = useState(0)

  const load = useCallback(() => {
    api.leagueScores(league).then(setBoard).catch(() => {})
  }, [league])

  useEffect(() => {
    load()
    const iv = setInterval(load, 60_000)
    const tick = setInterval(() => force(n => n + 1), 15_000)
    return () => { clearInterval(iv); clearInterval(tick) }
  }, [load])

  if (!board || !board.ok || board.games.length === 0) return null

  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between">
        <p className="text-[10px] font-display uppercase tracking-widest text-zinc-600">
          {title ?? 'Live board'}
        </p>
        <span className="text-[10px] font-mono text-zinc-600">
          {board.source} · updated {ago(board.fetched_at)}
        </span>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1">
        {board.games.map(g => <GameChip key={g.event_id} g={g} />)}
      </div>
    </div>
  )
}
