import { MiniChart, type Point } from './MiniChart'

export interface LineMovementChartProps {
  points: Point[]
  label: string
  /** Rendered when there isn't enough real history to draw anything. */
  emptyMessage?: string
}

/**
 * How the market line has moved. Only ever plots points we actually observed —
 * with fewer than two real readings it says so instead of drawing a line.
 */
export function LineMovementChart({ points, label, emptyMessage }: LineMovementChartProps) {
  if (points.length < 2) {
    return (
      <p className="text-sm text-zinc-400">
        {emptyMessage ??
          'Line history isn’t recorded yet, so there is nothing to plot. Only the current line is known.'}
      </p>
    )
  }
  const first = points[0].v
  const last = points[points.length - 1].v
  const delta = last - first
  return (
    <div className="space-y-2">
      <p className="text-xs text-zinc-400">
        {label} moved from <span className="font-mono font-semibold text-zinc-200">{first}</span> to{' '}
        <span className="font-mono font-semibold text-zinc-200">{last}</span>{' '}
        <span className={delta === 0 ? 'text-zinc-400' : delta > 0 ? 'text-signal-amber' : 'text-signal-blue'}>
          ({delta > 0 ? '+' : ''}{delta.toFixed(1)})
        </span>
      </p>
      <MiniChart points={points} ariaLabel={`${label} movement`} tone="#f5c518"
                 formatY={v => v.toFixed(1)} />
    </div>
  )
}
