import { Link } from 'react-router-dom'
import type { BoardEntry } from '../../types'

const pct = (v: number) => `${Math.round(v * 100)}%`

/** Live games the model reads differently from a book that is actually pricing them. */
export function livePicks(entries: BoardEntry[]): BoardEntry[] {
  return entries
    .filter(e => e.game.state === 'in' && e.model?.live_read?.actionable)
    .sort((a, b) => b.model!.live_read!.edge_pp - a.model!.live_read!.edge_pp)
}

/** Live games where the book has not repriced, so no edge is claimed. */
export function liveReadsOnly(entries: BoardEntry[]): BoardEntry[] {
  return entries.filter(
    e => e.game.state === 'in' && e.model?.live_read && !e.model.live_read.actionable,
  )
}

/**
 * Best live picks.
 *
 * Only games where the sportsbook has demonstrably repriced since kickoff. A
 * feed that is still publishing the pre-game line while a team is three scores
 * down would otherwise show as the biggest edge on the board, and it would be
 * entirely fictional — so those games are counted below the list rather than
 * ranked inside it.
 *
 * These carry no track record. In-game probabilities are recalculated from the
 * score and clock; they are never frozen and never graded, unlike the pre-game
 * picks on the Results page. The footnote says so, because a section headed
 * "best picks" invites exactly the assumption it would be wrong to allow.
 */
export function BestLivePicks({ entries, limit = 3 }: { entries: BoardEntry[]; limit?: number }) {
  const picks = livePicks(entries).slice(0, limit)
  const watching = liveReadsOnly(entries).length
  if (picks.length === 0 && watching === 0) return null

  return (
    <section aria-labelledby="live-picks" className="space-y-2.5">
      <div>
        <h2 id="live-picks" className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-zinc-500">
          <span className="h-1.5 w-1.5 rounded-full bg-signal-green animate-pulse" />
          Best live picks
        </h2>
        <p className="mt-0.5 text-xs text-zinc-500">
          Games in progress where the model and a repricing sportsbook disagree.
        </p>
      </div>

      {picks.length > 0 && (
        <ul className="grid gap-2 sm:grid-cols-3">
          {picks.map(entry => {
            const r = entry.model!.live_read!
            const g = entry.game
            return (
              <li key={`${entry.league}-${g.event_id}`}>
                <Link
                  to={`/game/${entry.league}/${g.event_id}`}
                  state={{ game: g }}
                  className="flex h-full flex-col rounded-xl border border-signal-green/40 bg-signal-green-dim px-3.5 py-3 hover:border-signal-green"
                >
                  <span className="flex items-center justify-between gap-2 text-[10px] font-bold uppercase tracking-wider text-signal-green">
                    <span>{g.away_abbr} {g.away_score ?? 0}–{g.home_score ?? 0} {g.home_abbr}</span>
                    <span>{g.period ? `Q${g.period}` : 'Live'}</span>
                  </span>
                  <span className="mt-1 text-sm font-bold text-zinc-100">{r.team}</span>
                  <div className="mt-2 flex items-baseline justify-between gap-2 text-xs">
                    <span className="text-zinc-500">Model</span>
                    <span className="font-mono text-base font-black tabular-nums text-zinc-100">
                      {pct(r.model_prob)}
                    </span>
                  </div>
                  <div className="flex items-baseline justify-between gap-2 text-xs">
                    <span className="text-zinc-500">Live price</span>
                    <span className="font-mono tabular-nums text-zinc-400">{pct(r.market_prob)}</span>
                  </div>
                </Link>
              </li>
            )
          })}
        </ul>
      )}

      {picks.length === 0 && (
        <p className="rounded-xl border border-dashed border-terminal-border px-3.5 py-3 text-sm text-zinc-500">
          No live pick right now — the model and the live prices agree on the games
          in progress.
        </p>
      )}

      {watching > 0 && (
        <p className="text-xs leading-relaxed text-zinc-500">
          {watching} other live {watching === 1 ? 'game is' : 'games are'} not listed:
          the posted price has not moved since kickoff, so there is no live market to
          disagree with and no edge to claim.
        </p>
      )}

      <p className="text-xs leading-relaxed text-zinc-500">
        Live reads are recalculated from the score and clock. They are not frozen and
        not graded, so they are no part of the{' '}
        <Link to="/results" className="font-semibold text-brand hover:underline">
          track record
        </Link>
        , which covers pre-game picks only.
      </p>
    </section>
  )
}
