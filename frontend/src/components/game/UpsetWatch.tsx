import { Link } from 'react-router-dom'
import type { BoardEntry } from '../../types'

const pct = (v: number) => `${Math.round(v * 100)}%`

/** Games the model reads differently from the market, biggest gap first. */
export function upsetPicks(entries: BoardEntry[]): BoardEntry[] {
  return entries
    .filter(e => e.game.state === 'pre' && e.model?.upset)
    .sort((a, b) => (b.model!.upset!.model_prob - b.model!.upset!.market_prob)
                  - (a.model!.upset!.model_prob - a.model!.upset!.market_prob))
}

/**
 * Where the model and the market disagree about who wins.
 *
 * Deliberately a short list. The rule fires on about one game in ten; flagging
 * every disagreement would cover a fifth of the slate and mean nothing.
 *
 * Two numbers appear here and they are not the same kind of thing. One is what
 * the model gives this underdog in this game. The other is how often the rule
 * has been right across many games — a record, not a forecast — and it is
 * labelled as such rather than left to be read as this game's chance.
 */
export function UpsetWatch({ entries, limit = 3 }: { entries: BoardEntry[]; limit?: number }) {
  const picks = upsetPicks(entries).slice(0, limit)
  if (picks.length === 0) return null

  const rule = picks[0].model!.upset!

  return (
    <section aria-labelledby="upset-watch" className="space-y-2.5">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 id="upset-watch" className="text-xs font-bold uppercase tracking-widest text-zinc-500">
            Upset watch
          </h2>
          <p className="mt-0.5 text-xs text-zinc-500">
            The model takes the underdog here. It disagrees with the market this
            way in about one game in ten.
          </p>
        </div>
      </div>

      <ul className="grid gap-2 sm:grid-cols-3">
        {picks.map(entry => {
          const u = entry.model!.upset!
          const g = entry.game
          const other = u.side === 'home' ? g.away_abbr : g.home_abbr
          return (
            <li key={`${entry.league}-${g.event_id}`}>
              <Link
                to={`/game/${entry.league}/${g.event_id}`}
                state={{ game: g }}
                className="flex h-full flex-col rounded-xl border border-signal-amber/40 bg-signal-amber-dim px-3.5 py-3 hover:border-signal-amber"
              >
                <span className="text-[10px] font-bold uppercase tracking-wider text-signal-amber">
                  Model takes the underdog
                </span>
                <span className="mt-1 text-sm font-bold text-zinc-100">
                  {u.team} <span className="font-normal text-zinc-500">over {other}</span>
                </span>
                <div className="mt-2 flex items-baseline justify-between gap-2 text-xs">
                  <span className="text-zinc-500">Model</span>
                  <span className="font-mono text-base font-black tabular-nums text-zinc-100">
                    {pct(u.model_prob)}
                  </span>
                </div>
                <div className="flex items-baseline justify-between gap-2 text-xs">
                  <span className="text-zinc-500">Market</span>
                  <span className="font-mono tabular-nums text-zinc-400">{pct(u.market_prob)}</span>
                </div>
              </Link>
            </li>
          )
        })}
      </ul>

      <p className="text-xs leading-relaxed text-zinc-500">
        Across past seasons these picks won {pct(rule.rule_hit_rate)} of the time,
        against {pct(rule.rule_base_rate)} for market underdogs generally. That is
        the rule’s record over many games, not the chance of any one of these.
      </p>
    </section>
  )
}
