import { useMemo, useState, useEffect } from 'react'

interface Props {
  /** Map of line ("2.5") → P(over) */
  overByLine: Record<string, number>
  unit: string            // "goals" | "points"
  title?: string
  /** Line to preselect (nearest available is used) */
  initialLine?: number
}

export function LineExplorer({ overByLine, unit, title, initialLine }: Props) {
  const lines = useMemo(
    () => Object.keys(overByLine).map(Number).sort((a, b) => a - b),
    [overByLine],
  )
  const [idx, setIdx] = useState(0)

  useEffect(() => {
    if (lines.length === 0) return
    const target = initialLine ?? lines[Math.floor(lines.length / 2)]
    let best = 0
    lines.forEach((l, i) => {
      if (Math.abs(l - target) < Math.abs(lines[best] - target)) best = i
    })
    setIdx(best)
  }, [lines, initialLine])

  if (lines.length === 0) return null

  const line = lines[Math.min(idx, lines.length - 1)]
  const over = overByLine[`${line}`] ?? 0
  const under = 1 - over

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-display uppercase tracking-widest text-zinc-500">
          {title ?? `Any-line over/under (${unit})`}
        </p>
        <span className="font-mono text-lg text-signal-amber">{line.toFixed(1)}</span>
      </div>

      <input
        type="range"
        min={0}
        max={lines.length - 1}
        step={1}
        value={idx}
        onChange={e => setIdx(Number(e.target.value))}
        className="w-full accent-signal-amber"
      />

      <div className="grid grid-cols-2 gap-3">
        <div className={`rounded-lg border p-3 text-center ${over >= 0.55 ? 'border-signal-green/40 bg-signal-green/5' : 'border-terminal-border bg-terminal-surface'}`}>
          <p className="text-[10px] font-display uppercase tracking-widest text-zinc-500">Over {line.toFixed(1)}</p>
          <p className={`font-mono text-2xl mt-1 ${over >= 0.55 ? 'text-signal-green' : 'text-zinc-300'}`}>
            {(over * 100).toFixed(1)}%
          </p>
          <p className="font-mono text-[10px] text-zinc-600">fair {over > 0.001 ? (1 / over).toFixed(2) : '—'}</p>
        </div>
        <div className={`rounded-lg border p-3 text-center ${under >= 0.55 ? 'border-signal-green/40 bg-signal-green/5' : 'border-terminal-border bg-terminal-surface'}`}>
          <p className="text-[10px] font-display uppercase tracking-widest text-zinc-500">Under {line.toFixed(1)}</p>
          <p className={`font-mono text-2xl mt-1 ${under >= 0.55 ? 'text-signal-green' : 'text-zinc-300'}`}>
            {(under * 100).toFixed(1)}%
          </p>
          <p className="font-mono text-[10px] text-zinc-600">fair {under > 0.001 ? (1 / under).toFixed(2) : '—'}</p>
        </div>
      </div>

      {/* Probability curve across all lines */}
      <div>
        <div className="flex items-end gap-0.5 h-14">
          {lines.map((l, i) => {
            const p = overByLine[`${l}`] ?? 0
            return (
              <button
                key={l}
                onClick={() => setIdx(i)}
                title={`Over ${l}: ${(p * 100).toFixed(1)}%`}
                className={`flex-1 rounded-t transition-colors ${i === idx ? 'bg-signal-amber' : 'bg-terminal-muted hover:bg-zinc-600'}`}
                style={{ height: `${Math.max(4, p * 100)}%` }}
              />
            )
          })}
        </div>
        <div className="flex justify-between font-mono text-[9px] text-zinc-600 mt-0.5">
          <span>{lines[0].toFixed(1)}</span>
          <span>P(over) by line</span>
          <span>{lines[lines.length - 1].toFixed(1)}</span>
        </div>
      </div>
    </div>
  )
}
