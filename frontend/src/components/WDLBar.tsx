/** Win / Draw / Loss probability bar */
interface Props {
  homeWin: number
  draw: number
  awayWin: number
  homeLabel: string
  awayLabel: string
}

export function WDLBar({ homeWin, draw, homeLabel, awayLabel }: Omit<Props, 'awayWin'> & { awayWin?: number }) {
  const hw = Math.round(homeWin * 100)
  const dr = Math.round(draw * 100)
  const aw = 100 - hw - dr

  return (
    <div className="space-y-2">
      <div className="flex h-8 w-full overflow-hidden rounded-lg">
        <div
          className="flex items-center justify-center bg-signal-blue text-white text-xs font-mono font-medium transition-all duration-700"
          style={{ width: `${hw}%` }}
        >
          {hw >= 10 ? `${hw}%` : ''}
        </div>
        <div
          className="flex items-center justify-center bg-zinc-600 text-white text-xs font-mono transition-all duration-700"
          style={{ width: `${dr}%` }}
        >
          {dr >= 8 ? `${dr}%` : ''}
        </div>
        <div
          className="flex items-center justify-center bg-signal-red text-white text-xs font-mono font-medium transition-all duration-700"
          style={{ width: `${aw}%` }}
        >
          {aw >= 10 ? `${aw}%` : ''}
        </div>
      </div>

      <div className="flex justify-between text-xs text-zinc-400 font-body">
        <span className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-sm bg-signal-blue" />
          {homeLabel} {hw}%
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-sm bg-zinc-600" />
          Draw {dr}%
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-sm bg-signal-red" />
          {awayLabel} {aw}%
        </span>
      </div>
    </div>
  )
}
