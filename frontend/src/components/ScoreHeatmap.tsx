/** Scoreline probability heatmap */
interface Props {
  grid: number[][]    // grid[home][away] = probability
  homeLabel: string
  awayLabel: string
  maxGoals?: number
}

function probToOpacity(p: number, maxP: number): number {
  return Math.min(1, p / maxP + 0.05)
}

export function ScoreHeatmap({ grid, homeLabel, awayLabel, maxGoals = 6 }: Props) {
  const displayGrid = grid.slice(0, maxGoals + 1).map(row => row.slice(0, maxGoals + 1))
  const maxP = Math.max(...displayGrid.flat())

  return (
    <div className="space-y-2">
      <p className="text-xs font-display uppercase tracking-widest text-zinc-500">
        Scoreline grid (P%)
      </p>
      <div className="overflow-x-auto">
        <table className="border-collapse text-center font-mono text-xs">
          <thead>
            <tr>
              <th className="p-1 text-zinc-500 font-normal">↓{homeLabel} / {awayLabel}→</th>
              {displayGrid[0].map((_, j) => (
                <th key={j} className="p-1 text-zinc-500 font-normal w-10">{j}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayGrid.map((row, i) => (
              <tr key={i}>
                <td className="p-1 text-zinc-500 w-10">{i}</td>
                {row.map((p, j) => {
                  const opacity = probToOpacity(p, maxP)
                  const isHighest = p === maxP
                  return (
                    <td
                      key={j}
                      className={`p-1 w-10 rounded transition-colors ${isHighest ? 'ring-1 ring-signal-amber' : ''}`}
                      style={{
                        backgroundColor: `rgba(245,158,11,${opacity * 0.7})`,
                        color: opacity > 0.6 ? '#0a0a0f' : '#a1a1aa',
                      }}
                      title={`${i}–${j}: ${(p * 100).toFixed(1)}%`}
                    >
                      {(p * 100).toFixed(1)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
