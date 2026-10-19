import { Link } from 'react-router-dom'
import type { BoardEntry, ValidationOut } from '../../types'

const LEAGUE_LABEL: Record<string, string> = { ncaaf: 'NCAAF', nfl: 'NFL' }

/**
 * What the backtest found about the lines on this board, said once.
 *
 * Every row shows a StatEdge number beside the market's, which invites the
 * reader to assume the first one is better. For the NFL it is not: on 750
 * walk-forward games the model alone was less accurate than the closing line,
 * which is why the published line is mostly the market's and why the rows
 * usually say the two agree.
 *
 * It sits above the games rather than on each card. Repeated under two hundred
 * rows the same sentence becomes wallpaper nobody reads; stated once, before
 * the first number, it is the frame the rest of the board is read in.
 *
 * The note only covers leagues that are actually on the board, so a Sunday
 * with no college games does not carry a claim about college football.
 */
export function ValidationNote({ entries }: { entries: BoardEntry[] }) {
  const byLeague = new Map<string, ValidationOut>()
  for (const e of entries) {
    const v = e.value?.validation
    if (v && !byLeague.has(e.league)) byLeague.set(e.league, v)
  }
  if (byLeague.size === 0) return null

  return (
    <aside
      aria-labelledby="board-validation"
      className="rounded-panel border border-signal-amber/30 bg-signal-amber-dim px-3.5 py-3"
    >
      <h2
        id="board-validation"
        className="text-[11px] font-bold uppercase tracking-widest text-signal-amber"
      >
        How well these lines have done
      </h2>
      <ul className="mt-1.5 space-y-1">
        {[...byLeague].map(([league, v]) => (
          <li key={league} className="text-xs leading-relaxed text-zinc-400">
            <span className="font-bold text-zinc-300">
              {LEAGUE_LABEL[league] ?? league.toUpperCase()}
            </span>
            {' — '}
            {v.measured && v.beats_market === false && (
              <span className="font-semibold text-signal-amber">
                no demonstrated edge on this league&rsquo;s game lines.{' '}
              </span>
            )}
            {!v.measured && (
              <span className="font-semibold text-signal-amber">not yet measured. </span>
            )}
            {v.note}
          </li>
        ))}
      </ul>
      <p className="mt-1.5 text-xs text-zinc-500">
        <Link to="/about" className="font-semibold text-brand hover:underline">
          How the lines are made &rsaquo;
        </Link>
      </p>
    </aside>
  )
}
