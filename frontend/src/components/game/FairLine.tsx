import type { ValueOut } from '../../types'

const signed = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(1)}`

/**
 * StatEdge's line, the market's line, and the gap — in that order.
 *
 * This is the sentence the whole product is built to say: "we think this line
 * is wrong, by this much, in this direction". Before this row the board showed
 * a cover probability and left a reader to work backwards to the number, which
 * is the wrong way round.
 *
 * Two deliberate restraints. Nothing here is called a lock, a guarantee or a
 * confidence percentage; and a gap smaller than the half-point a spread is
 * quoted in is shown as agreement rather than dressed up as an edge.
 */
export function FairLine({ value, compact = false }: { value: ValueOut; compact?: boolean }) {
  const { spread, total, confidence, validation } = value
  const hasSpread = spread.market != null && spread.points != null
  const hasTotal = total.market != null && total.points != null

  if (!hasSpread && !hasTotal) return null

  return (
    <div className={compact ? '' : 'rounded-card border border-terminal-border bg-terminal-surface p-4'}>
      {hasSpread && (
        <dl className="grid grid-cols-3 gap-x-3 font-mono text-xs tabular-nums">
          <div>
            <dt className="font-sans text-[10px] font-bold uppercase tracking-widest text-zinc-500">
              StatEdge
            </dt>
            <dd className="mt-0.5 text-[15px] font-black text-zinc-100">{spread.fair_label}</dd>
          </div>
          <div>
            <dt className="font-sans text-[10px] font-bold uppercase tracking-widest text-zinc-500">
              Market
            </dt>
            <dd className="mt-0.5 text-[15px] font-black text-zinc-100">{spread.market_label}</dd>
          </div>
          <div>
            <dt className="font-sans text-[10px] font-bold uppercase tracking-widest text-zinc-500">
              Edge
            </dt>
            <dd className="mt-0.5 text-[15px] font-black text-brand">
              {signed(spread.points!)} <span className="text-xs font-bold">pts {spread.side_abbr}</span>
            </dd>
          </div>
        </dl>
      )}

      {hasTotal && (
        <p className={`${hasSpread ? 'mt-2 ' : ''}font-mono text-xs tabular-nums text-zinc-400`}>
          Total — StatEdge {total.fair.toFixed(1)} · market {total.market!.toFixed(1)}
          <span className="text-brand"> · {signed(total.edge_points!)} {total.side}</span>
        </p>
      )}

      <p className="mt-1.5 text-xs text-zinc-500">
        <span className="capitalize">{confidence.level}</span> model confidence
        {' '}({confidence.inputs_present}/{confidence.inputs_total} inputs) — how much of
        the model's input this game had, not the chance a bet wins.
      </p>

      {/* What the backtest found, said on the page that shows the number.
          For the NFL it found that the model alone is less accurate than the
          closing line, which is why the line above is mostly the market's.
          Leaving that out while showing an "edge" would be the dishonest
          version of this component. */}
      {validation && (
        <p className="mt-1 text-xs leading-relaxed text-zinc-500">
          {validation.measured && validation.beats_market === false && (
            <span className="font-semibold text-signal-amber">No demonstrated edge on this league's game lines. </span>
          )}
          {!validation.measured && (
            <span className="font-semibold text-signal-amber">Unvalidated league. </span>
          )}
          {validation.note}
          {spread.model_line != null && spread.model_weight != null && (
            <span className="font-mono tabular-nums">
              {' '}Model alone {spread.model_line.toFixed(1)}, weighted{' '}
              {Math.round(spread.model_weight * 100)}%.
            </span>
          )}
        </p>
      )}
    </div>
  )
}
