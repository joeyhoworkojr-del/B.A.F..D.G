import type { WhyFactorOut } from '../types'

interface Props {
  factors: WhyFactorOut[]
}

export function WhyPanel({ factors }: Props) {
  const maxAbs = Math.max(...factors.map(f => Math.abs(f.value)), 0.01)

  return (
    <div className="space-y-2">
      <p className="text-[10px] font-display uppercase tracking-widest text-zinc-600">
        Why — signed contributions to home win probability
      </p>
      {factors.map((f, i) => {
        const isPos = f.value >= 0
        const pct = Math.abs(f.value) / maxAbs * 100
        return (
          <div key={i} className="flex items-center gap-3">
            <span className="w-40 text-xs text-zinc-400 font-body truncate">{f.label}</span>
            <div className="flex-1 relative h-4 flex items-center">
              <div className="absolute left-1/2 right-0 h-px bg-terminal-muted" />
              <div className="absolute right-1/2 left-0 h-px bg-terminal-muted" />
              {isPos ? (
                <div
                  className="absolute left-1/2 h-3 rounded-r bg-signal-blue/70"
                  style={{ width: `${pct / 2}%` }}
                />
              ) : (
                <div
                  className="absolute right-1/2 h-3 rounded-l bg-signal-red/70"
                  style={{ width: `${pct / 2}%` }}
                />
              )}
            </div>
            <span className={`font-mono text-xs w-14 text-right ${isPos ? 'text-signal-blue' : 'text-signal-red'}`}>
              {isPos ? '+' : ''}{(f.value * 100).toFixed(1)}pp
            </span>
          </div>
        )
      })}
    </div>
  )
}
