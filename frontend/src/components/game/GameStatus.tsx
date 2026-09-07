import { useEffect, useState } from 'react'
import type { LiveGameOut } from '../../types'

export type GamePhase = 'pre' | 'in' | 'post'

/** Countdown to kickoff, or null once it's passed / unparseable. */
export function useKickoffCountdown(kickoff?: string): string | null {
  const [, tick] = useState(0)
  useEffect(() => {
    const id = setInterval(() => tick(n => n + 1), 1000)
    return () => clearInterval(id)
  }, [])
  if (!kickoff) return null
  const t = new Date(kickoff).getTime()
  if (isNaN(t)) return null
  const ms = t - Date.now()
  if (ms <= 0) return null
  const total = Math.floor(ms / 1000)
  const d = Math.floor(total / 86400)
  const h = Math.floor((total % 86400) / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  if (d > 0) return `${d}d ${h}h`
  if (h > 0) return `${h}h ${m}m`
  return `${m}m ${String(s).padStart(2, '0')}s`
}

export function formatKickoff(kickoff?: string): string {
  if (!kickoff) return ''
  const d = new Date(kickoff)
  if (isNaN(d.getTime())) return ''
  return d.toLocaleString(undefined, {
    weekday: 'short', month: 'short', day: 'numeric',
    hour: 'numeric', minute: '2-digit',
  })
}

/**
 * The one place that decides how a game's state reads. Pre-game shows the
 * kickoff time and a countdown — never a 0–0 scoreline, which would imply the
 * game has started.
 */
export function GameStatus({ game, className = '' }: { game: LiveGameOut; className?: string }) {
  const countdown = useKickoffCountdown(game.kickoff)

  if (game.state === 'in') {
    const clock = [game.period ? `Q${game.period}` : null, game.clock || game.detail]
      .filter(Boolean).join(' ')
    return (
      <div className={`flex flex-wrap items-center gap-2 ${className}`}>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-signal-green/15 px-2.5 py-1 text-xs font-bold text-signal-green">
          <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-signal-green motion-safe:animate-pulse" />
          LIVE
        </span>
        <span className="font-mono text-sm font-semibold text-zinc-100">{clock}</span>
        {game.possession_abbr && (
          <span className="rounded bg-terminal-muted px-2 py-0.5 text-xs font-semibold text-zinc-300">
            {game.possession_abbr} ball
          </span>
        )}
        {game.down_distance && (
          <span className="text-xs text-zinc-400">{game.down_distance}</span>
        )}
      </div>
    )
  }

  if (game.state === 'post') {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <span className="rounded-full bg-terminal-muted px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-zinc-300">
          Final
        </span>
        <span className="text-xs text-zinc-400">{formatKickoff(game.kickoff)}</span>
      </div>
    )
  }

  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`}>
      <span className="rounded-full bg-terminal-muted px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-zinc-300">
        Pregame
      </span>
      <span className="text-xs text-zinc-300">{formatKickoff(game.kickoff) || game.detail}</span>
      {countdown && (
        <span className="text-xs text-zinc-400">
          · kickoff in <span className="font-mono font-semibold text-zinc-200">{countdown}</span>
        </span>
      )}
    </div>
  )
}
