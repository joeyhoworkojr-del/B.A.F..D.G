export interface Point { t: number; v: number }

/**
 * Minimal SVG line chart. Deliberately dependency-free and fixed-height so it
 * never causes layout shift while data streams in.
 */
export function MiniChart({
  points, height = 96, tone = 'var(--chart-tone, #2fd07a)', ariaLabel,
  yMin, yMax, formatY = (v: number) => String(v),
}: {
  points: Point[]
  height?: number
  tone?: string
  ariaLabel: string
  yMin?: number
  yMax?: number
  formatY?: (v: number) => string
}) {
  const w = 100, h = 100   // viewBox units; stretched by CSS
  const vs = points.map(p => p.v)
  const lo = yMin ?? Math.min(...vs)
  const hi = yMax ?? Math.max(...vs)
  const span = hi - lo || 1
  const n = points.length

  const xy = points.map((p, i) => {
    const x = n === 1 ? w / 2 : (i / (n - 1)) * w
    const y = h - ((p.v - lo) / span) * h
    return [x, y] as const
  })
  const d = xy.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`).join(' ')
  const last = points[n - 1]

  return (
    <figure className="m-0">
      <svg
        viewBox={`0 0 ${w} ${h}`}
        preserveAspectRatio="none"
        style={{ height, width: '100%' }}
        role="img"
        aria-label={`${ariaLabel}. Latest ${formatY(last.v)}.`}
      >
        <path d={d} fill="none" stroke={tone} strokeWidth="1.5" vectorEffect="non-scaling-stroke"
              strokeLinejoin="round" strokeLinecap="round" />
        {n === 1 && <circle cx={xy[0][0]} cy={xy[0][1]} r="2" fill={tone} vectorEffect="non-scaling-stroke" />}
      </svg>
      <figcaption className="mt-1 flex justify-between text-xs text-zinc-500">
        <span>{formatY(lo)}</span>
        <span className="font-mono font-semibold text-zinc-300">{formatY(last.v)}</span>
        <span>{formatY(hi)}</span>
      </figcaption>
    </figure>
  )
}
