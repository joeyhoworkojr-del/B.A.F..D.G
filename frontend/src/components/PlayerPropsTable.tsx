import type { PlayerPropOut } from '../types'

interface Props {
  props: PlayerPropOut[]
  homeCode: string
  awayCode: string
  homeFlag: string
  awayFlag: string
}

export function PlayerPropsTable({ props, homeCode, homeFlag, awayFlag }: Omit<Props, 'awayCode'> & { awayCode?: string }) {
  if (props.length === 0) {
    return (
      <p className="text-sm text-zinc-500 italic">
        No seeded scorer data for these teams.
      </p>
    )
  }

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-4 gap-2 text-xs font-display uppercase tracking-widest text-zinc-500 border-b border-terminal-border pb-1">
        <span>Player</span>
        <span className="text-right">Anytime</span>
        <span className="text-right">2+ Goals</span>
        <span className="text-right">xG</span>
      </div>
      {props.map(p => {
        const isHome = p.team === homeCode
        const flag = isHome ? homeFlag : awayFlag
        return (
          <div key={`${p.name}-${p.team}`} className="grid grid-cols-4 gap-2 items-center py-1 border-b border-terminal-muted/50">
            <div className="flex items-center gap-1.5">
              <span className="text-sm">{flag}</span>
              <span className="text-xs font-body text-zinc-200 truncate">{p.name}</span>
            </div>
            <span className="text-right font-mono text-sm text-signal-amber">
              {(p.anytime_scorer * 100).toFixed(0)}%
            </span>
            <span className="text-right font-mono text-sm text-zinc-300">
              {(p.two_plus_goals * 100).toFixed(0)}%
            </span>
            <span className="text-right font-mono text-xs text-zinc-500">
              {p.xg.toFixed(2)}
            </span>
          </div>
        )
      })}
      <p className="text-[10px] text-zinc-600 italic pt-1">
        Anytime = P(≥1 goal). Shares grounded in tournament goal records.
        Cannot see today's lineup — treat as soft estimates.
      </p>
    </div>
  )
}
