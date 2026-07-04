import type { EdgeOut } from '../types'

const RATING_STYLE: Record<string, string> = {
  A: 'bg-signal-green/20 text-signal-green border-signal-green/40',
  B: 'bg-signal-amber/20 text-signal-amber border-signal-amber/40',
  C: 'bg-signal-blue/20 text-signal-blue border-signal-blue/40',
  '-': 'bg-terminal-muted text-zinc-500 border-terminal-muted',
}

export function RatingChip({ rating }: { rating: string }) {
  return (
    <span className={`rounded border px-1.5 py-0.5 font-mono text-[10px] font-bold ${RATING_STYLE[rating] ?? RATING_STYLE['-']}`}>
      {rating === '-' ? 'PASS' : rating}
    </span>
  )
}

export function EdgesTable({ edges }: { edges: EdgeOut[] }) {
  if (edges.length === 0) return null
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-body">
        <thead>
          <tr className="text-[10px] font-display uppercase tracking-widest text-zinc-600 border-b border-terminal-border">
            <th className="text-left py-1.5 pr-2">Bet</th>
            <th className="text-right py-1.5 px-2">Model</th>
            <th className="text-right py-1.5 px-2">Market*</th>
            <th className="text-right py-1.5 px-2">Edge</th>
            <th className="text-right py-1.5 px-2">EV/unit</th>
            <th className="text-right py-1.5 px-2">Kelly</th>
            <th className="text-right py-1.5 pl-2">Grade</th>
          </tr>
        </thead>
        <tbody>
          {edges.map((e, i) => (
            <tr key={i} className="border-b border-terminal-muted/30">
              <td className="py-1.5 pr-2">
                <span className="text-zinc-200">{e.selection}</span>
                <span className="ml-1.5 text-zinc-600 font-mono text-[10px]">{e.market} @ {e.decimal_odds.toFixed(2)}</span>
              </td>
              <td className="text-right px-2 font-mono text-zinc-300">{(e.model_prob * 100).toFixed(1)}%</td>
              <td className="text-right px-2 font-mono text-zinc-500">{(e.market_prob * 100).toFixed(1)}%</td>
              <td className={`text-right px-2 font-mono font-medium ${e.edge_pp >= 1.5 ? 'text-signal-green' : e.edge_pp <= -1.5 ? 'text-signal-red' : 'text-zinc-500'}`}>
                {e.edge_pp >= 0 ? '+' : ''}{e.edge_pp.toFixed(1)}pp
              </td>
              <td className={`text-right px-2 font-mono ${e.ev_per_unit > 0 ? 'text-signal-green' : 'text-zinc-500'}`}>
                {e.ev_per_unit >= 0 ? '+' : ''}{(e.ev_per_unit * 100).toFixed(1)}%
              </td>
              <td className="text-right px-2 font-mono text-zinc-400">
                {e.kelly_stake > 0 ? `${(e.kelly_stake * 100).toFixed(1)}%` : '—'}
              </td>
              <td className="text-right pl-2"><RatingChip rating={e.rating} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-[10px] text-zinc-600 italic mt-2">
        *Market = no-vig implied probability. Kelly = quarter-Kelly share of bankroll. Grades: A ≥ 6pp, B ≥ 3.5pp, C ≥ 1.5pp edge.
      </p>
    </div>
  )
}
