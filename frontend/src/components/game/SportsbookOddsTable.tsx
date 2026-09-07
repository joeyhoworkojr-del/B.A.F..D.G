import type { MarketOut, ProbabilityKind } from '../../types'

const KIND_HEADER: Record<ProbabilityKind, string> = {
  win: 'Model win %',
  cover: 'Model cover %',
  total: 'Model O/U %',
}

const pct1 = (v?: number | null) => (v == null ? '—' : `${(v * 100).toFixed(1)}%`)
const am = (v?: number | null) => (v == null ? '—' : v > 0 ? `+${v}` : `${v}`)

/** Priced view of a market: what you'd pay, what the model thinks it's worth. */
export function SportsbookOddsTable({ market }: { market: MarketOut }) {
  return (
    <div className="w-full max-w-full overflow-x-auto">
      <table className="w-full min-w-[34rem] text-left text-sm">
        <caption className="sr-only">
          {market.label} prices and model comparison from {market.source}
        </caption>
        <thead>
          <tr className="border-b border-terminal-border text-xs font-semibold uppercase tracking-wide text-zinc-400">
            <th scope="col" className="py-2 pr-3">Selection</th>
            <th scope="col" className="py-2 px-3 text-right">Price</th>
            <th scope="col" className="py-2 px-3 text-right">{KIND_HEADER[market.probability_kind]}</th>
            <th scope="col" className="py-2 px-3 text-right">Book (no vig)</th>
            <th scope="col" className="py-2 px-3 text-right">Fair price</th>
            <th scope="col" className="py-2 pl-3 text-right">Edge</th>
          </tr>
        </thead>
        <tbody>
          {market.selections.map(sel => {
            const positive = (sel.edge_pp ?? 0) > 0
            return (
              <tr key={sel.side} className="border-b border-terminal-border/60 last:border-0">
                <th scope="row" className="py-2.5 pr-3 font-semibold text-zinc-100">{sel.label}</th>
                <td className="py-2.5 px-3 text-right font-mono tabular-nums text-zinc-100">{am(sel.price_american)}</td>
                <td className="py-2.5 px-3 text-right font-mono tabular-nums text-signal-green">{pct1(sel.model_prob)}</td>
                <td className="py-2.5 px-3 text-right font-mono tabular-nums text-zinc-300">{pct1(sel.book_prob)}</td>
                <td className="py-2.5 px-3 text-right font-mono tabular-nums text-zinc-300">{am(sel.fair_price_american)}</td>
                <td className={`py-2.5 pl-3 text-right font-mono font-semibold tabular-nums ${positive ? 'text-signal-green' : 'text-zinc-400'}`}>
                  {sel.edge_pp == null ? '—' : `${sel.edge_pp > 0 ? '+' : ''}${sel.edge_pp.toFixed(1)}`}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-zinc-500">
        Edge is in percentage points of probability, not a price difference.
        {market.assumed_price && ' Spread and total prices are assumed at −110 — this feed publishes the line but not the price.'}
      </p>
    </div>
  )
}
