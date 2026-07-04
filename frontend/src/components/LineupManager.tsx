import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { KeyPlayerOut } from '../types'

interface Props {
  sport: 'soccer' | 'nfl' | 'cfl' | 'mlb'
  homeTeam: string   // team code
  awayTeam: string
  homeLabel?: string
  awayLabel?: string
  /** Called after any availability change so the parent can re-run the prediction */
  onChanged?: () => void
}

const STATUS_ORDER: Array<KeyPlayerOut['status']> = ['fit', 'doubtful', 'out']

const STATUS_STYLE: Record<KeyPlayerOut['status'], string> = {
  fit: 'text-signal-green border-signal-green/40',
  doubtful: 'text-signal-amber border-signal-amber/40',
  out: 'text-signal-red border-signal-red/40 bg-signal-red/10',
}

function PlayerRow({
  player,
  onSet,
}: {
  player: KeyPlayerOut
  onSet: (status: KeyPlayerOut['status']) => void
}) {
  return (
    <div className="flex items-center justify-between gap-2 py-1 border-b border-terminal-muted/30">
      <div className="min-w-0">
        <span className="text-xs font-body text-zinc-300 truncate">{player.name}</span>
        <span className="ml-1.5 font-mono text-[10px] text-zinc-600">{player.position}</span>
      </div>
      <div className="flex gap-1">
        {STATUS_ORDER.map(s => (
          <button
            key={s}
            onClick={() => onSet(s)}
            className={`
              rounded border px-1.5 py-0.5 text-[10px] font-display uppercase tracking-wide transition-colors
              ${player.status === s ? STATUS_STYLE[s] : 'border-terminal-muted text-zinc-600 hover:text-zinc-400'}
            `}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}

function TeamColumn({
  sport,
  team,
  label,
  onChanged,
}: {
  sport: 'soccer' | 'nfl' | 'cfl' | 'mlb'
  team: string
  label: string
  onChanged?: () => void
}) {
  const [players, setPlayers] = useState<KeyPlayerOut[]>([])

  const load = useCallback(() => {
    if (team) api.lineup(sport, team).then(setPlayers).catch(() => setPlayers([]))
  }, [sport, team])

  useEffect(() => { load() }, [load])

  async function setStatus(player: string, status: KeyPlayerOut['status']) {
    try {
      await api.setPlayerStatus(sport, team, player, status)
      load()
      onChanged?.()
    } catch { /* keep previous state on failure */ }
  }

  if (!team) return null

  return (
    <div>
      <p className="text-[10px] font-display uppercase tracking-widest text-zinc-500 mb-1">{label}</p>
      {players.length === 0 ? (
        <p className="text-xs text-zinc-600 font-body">No tracked key players.</p>
      ) : (
        players.map(p => (
          <PlayerRow key={p.name} player={p} onSet={s => setStatus(p.name, s)} />
        ))
      )}
    </div>
  )
}

export function LineupManager({ sport, homeTeam, awayTeam, homeLabel, awayLabel, onChanged }: Props) {
  const [open, setOpen] = useState(false)

  if (!homeTeam || !awayTeam) return null

  return (
    <div className="rounded-lg border border-terminal-border bg-terminal-surface/60">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-3 py-2 text-left"
      >
        <span className="text-xs font-display uppercase tracking-widest text-zinc-400">
          🩹 Team news / availability
        </span>
        <span className="text-zinc-600 text-xs">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="px-3 pb-3 space-y-2">
          <p className="text-[11px] text-zinc-500 font-body">
            Mark key players out or doubtful — the model re-prices the match instantly.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <TeamColumn sport={sport} team={homeTeam} label={homeLabel ?? homeTeam} onChanged={onChanged} />
            <TeamColumn sport={sport} team={awayTeam} label={awayLabel ?? awayTeam} onChanged={onChanged} />
          </div>
        </div>
      )}
    </div>
  )
}
