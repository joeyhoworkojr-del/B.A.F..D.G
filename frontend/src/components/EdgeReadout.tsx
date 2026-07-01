/** EdgeReadout — signature terminal-style probability meter */
interface Props {
  probability: number  // [0, 1]
  label: string
  sublabel?: string
  size?: 'sm' | 'md' | 'lg'
  color?: 'amber' | 'green' | 'red' | 'blue'
}

const COLOR = {
  amber: { bar: 'bg-signal-amber', text: 'text-signal-amber', glow: 'shadow-signal-amber/20' },
  green: { bar: 'bg-signal-green', text: 'text-signal-green', glow: 'shadow-signal-green/20' },
  red:   { bar: 'bg-signal-red',   text: 'text-signal-red',   glow: 'shadow-signal-red/20' },
  blue:  { bar: 'bg-signal-blue',  text: 'text-signal-blue',  glow: 'shadow-signal-blue/20' },
}

export function EdgeReadout({ probability, label, sublabel, size = 'md', color = 'amber' }: Props) {
  const pct = Math.round(probability * 100)
  const c = COLOR[color]
  const tickPositions = [0, 25, 50, 75, 100]

  return (
    <div className={`flex flex-col gap-1 ${size === 'lg' ? 'gap-2' : ''}`}>
      <div className="flex items-baseline justify-between">
        <span className="font-display text-xs uppercase tracking-widest text-zinc-400">{label}</span>
        <span className={`font-mono font-medium ${size === 'lg' ? 'text-3xl' : size === 'sm' ? 'text-lg' : 'text-2xl'} ${c.text}`}>
          {pct}<span className="text-sm opacity-60">%</span>
        </span>
      </div>

      {/* Tick marks */}
      <div className="relative">
        <div className="h-1.5 w-full rounded-full bg-terminal-muted overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${c.bar}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="flex justify-between mt-0.5">
          {tickPositions.map(t => (
            <span key={t} className="font-mono text-[9px] text-zinc-600">{t}</span>
          ))}
        </div>
      </div>

      {sublabel && (
        <span className="text-xs text-zinc-500 font-body">{sublabel}</span>
      )}
    </div>
  )
}
