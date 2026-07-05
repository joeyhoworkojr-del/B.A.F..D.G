/** Dependency-free SVG sparkline with gradient fill — the "stock chart". */
interface Props {
  data: number[]
  width?: number
  height?: number
  stroke?: string
  id?: string
}

export function Sparkline({ data, width = 320, height = 96, stroke = '#2563eb', id = 'spark' }: Props) {
  if (data.length < 2) {
    return (
      <div className="flex items-center justify-center text-[11px] font-body text-zinc-600" style={{ height }}>
        Chart appears after a few graded picks
      </div>
    )
  }
  const min = Math.min(...data, 0)
  const max = Math.max(...data, 0)
  const span = max - min || 1
  const px = (i: number) => (i / (data.length - 1)) * (width - 8) + 4
  const py = (v: number) => height - 8 - ((v - min) / span) * (height - 16)
  const points = data.map((v, i) => `${px(i).toFixed(1)},${py(v).toFixed(1)}`).join(' ')
  const zeroY = py(0)
  const positive = data[data.length - 1] >= 0

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" style={{ height }}>
      <defs>
        <linearGradient id={`${id}-fill`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={positive ? stroke : '#dc2626'} stopOpacity="0.25" />
          <stop offset="100%" stopColor={positive ? stroke : '#dc2626'} stopOpacity="0" />
        </linearGradient>
      </defs>
      {min < 0 && max > 0 && (
        <line x1="4" x2={width - 4} y1={zeroY} y2={zeroY} stroke="#cbd5e1" strokeDasharray="3 3" strokeWidth="1" />
      )}
      <polygon
        points={`4,${height - 8} ${points} ${width - 4},${height - 8}`}
        fill={`url(#${id}-fill)`}
      />
      <polyline
        points={points}
        fill="none"
        stroke={positive ? stroke : '#dc2626'}
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  )
}
