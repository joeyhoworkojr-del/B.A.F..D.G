import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import type { SimOut } from '../types'

interface Props {
  sim: SimOut
  homeLabel: string
  awayLabel: string
  knockout?: boolean
}

export function MonteCarloChart({ sim, homeLabel, awayLabel, knockout = false }: Props) {
  // Build total score distribution chart
  const dist = sim.total_score_dist
  const data = Object.entries(dist)
    .map(([k, v]) => ({ goals: Number(k), prob: v * 100 }))
    .filter(d => d.goals <= 9)
    .sort((a, b) => a.goals - b.goals)

  const peakGoals = data.reduce((best, d) => (d.prob > (dist[best] ?? 0) * 100 ? d.goals : best), 0)

  return (
    <div className="space-y-4">
      {/* Advance probabilities for knockout */}
      {knockout && (
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-lg border border-signal-blue/30 bg-terminal-surface p-3 text-center">
            <p className="text-xs text-zinc-500 font-display uppercase tracking-widest">{homeLabel} advances</p>
            <p className="text-2xl font-mono text-signal-blue mt-1">
              {Math.round(sim.home_advance * 100)}%
            </p>
          </div>
          <div className="rounded-lg border border-signal-red/30 bg-terminal-surface p-3 text-center">
            <p className="text-xs text-zinc-500 font-display uppercase tracking-widest">{awayLabel} advances</p>
            <p className="text-2xl font-mono text-signal-red mt-1">
              {Math.round(sim.away_advance * 100)}%
            </p>
          </div>
        </div>
      )}

      {/* Total goals distribution */}
      <div>
        <p className="text-xs font-display uppercase tracking-widest text-zinc-500 mb-2">
          Total goals distribution — 50k simulations (±{sim.std_error.toFixed(2)}%)
        </p>
        <ResponsiveContainer width="100%" height={140}>
          <BarChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
            <XAxis
              dataKey="goals"
              tick={{ fill: '#71717a', fontSize: 11, fontFamily: 'JetBrains Mono' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: '#71717a', fontSize: 10, fontFamily: 'JetBrains Mono' }}
              tickFormatter={v => `${v.toFixed(0)}%`}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                background: '#ffffff',
                border: '1px solid #e2e8f0',
                borderRadius: 6,
                fontFamily: 'JetBrains Mono',
                fontSize: 11,
                color: '#0f172a',
                boxShadow: '0 4px 12px rgba(15,23,42,0.08)',
              }}
              formatter={(v: number) => [`${v.toFixed(1)}%`, 'P']}
              labelFormatter={l => `${l} goals`}
            />
            <Bar dataKey="prob" radius={[3, 3, 0, 0]}>
              {data.map(d => (
                <Cell
                  key={d.goals}
                  fill={d.goals === peakGoals ? '#2563eb' : '#93c5fd'}
                  opacity={d.goals === peakGoals ? 1 : 0.85}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Win/draw/loss from simulation */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="rounded-lg bg-terminal-surface p-2">
          <p className="text-[10px] text-zinc-500">{homeLabel} wins</p>
          <p className="font-mono text-signal-blue text-sm">{Math.round(sim.home_wins * 100)}%</p>
        </div>
        <div className="rounded-lg bg-terminal-surface p-2">
          <p className="text-[10px] text-zinc-500">Draw</p>
          <p className="font-mono text-zinc-400 text-sm">{Math.round(sim.draws * 100)}%</p>
        </div>
        <div className="rounded-lg bg-terminal-surface p-2">
          <p className="text-[10px] text-zinc-500">{awayLabel} wins</p>
          <p className="font-mono text-signal-red text-sm">{Math.round(sim.away_wins * 100)}%</p>
        </div>
      </div>
    </div>
  )
}
