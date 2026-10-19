import { Link } from 'react-router-dom'
import type { BoardEntry } from '../../types'

const LEAGUE_LABEL: Record<string, string> = { ncaaf: 'NCAAF', nfl: 'NFL' }

function kickoff(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

function Team({ name, record, logo, abbr }: {
  name: string; record?: string; logo?: string; abbr: string
}) {
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      {logo
        ? <img src={logo} alt="" className="h-7 w-7 shrink-0 object-contain" loading="lazy" />
        : <span className="grid h-7 w-7 shrink-0 place-items-center rounded bg-terminal-muted text-[10px] font-bold text-zinc-500">{abbr.slice(0, 3)}</span>}
      {/* `min-w-0` is what makes `truncate` do anything here: without it the
          name's own minimum is the full string, the row cannot shrink, and on
          a 390px phone "Kansas City Chiefs" widens the whole page instead of
          ending in an ellipsis. */}
      <span className="min-w-0 truncate text-[15px] font-bold text-zinc-100">{name}</span>
      {record && <span className="shrink-0 text-xs text-zinc-500">{record}</span>}
    </div>
  )
}

/**
 * One game: what the book is offering, what StatEdge makes it, and the gap.
 *
 * The gap is the reason the row exists, and it is also the number most likely
 * to be oversold. It is shown only when it clears the threshold the backtest
 * supports — a disagreement smaller than that is inside the half-point a
 * spread is quoted in, and labelling it "STRONG EDGE" because the design has
 * a slot for a chip is how a tipping site is built. When there is nothing, the
 * row says the two agree, which is a real and useful thing to know.
 */
export function GameRow({ entry }: { entry: BoardEntry }) {
  const { game: g, league, value } = entry
  const spread = value?.spread
  const points = spread?.points ?? null
  const hasEdge = points != null && spread?.side_abbr

  // `min-w-0` on the grid item too. A grid track sizes to its item's minimum
  // content width by default, so one long team name on a narrow phone widens
  // the column and with it the document.
  return (
    <div className="min-w-0">
      <Link
        to={`/game/${league}/${g.event_id}`}
        state={{ game: g }}
        className="tap block rounded-panel border border-terminal-border bg-terminal-surface p-3.5 hover:border-brand/40"
      >
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <span className="font-bold text-zinc-400">{LEAGUE_LABEL[league] ?? league.toUpperCase()}</span>
          <span aria-hidden="true">·</span>
          <span>{g.state === 'post' ? g.detail : kickoff(g.kickoff)}</span>
          {g.market_provider && (
            <span className="ml-auto truncate text-[10px] font-semibold uppercase tracking-wide">
              {g.market_provider}
            </span>
          )}
        </div>

        <div className="mt-2.5 flex items-center gap-3">
          <div className="min-w-0 flex-1 space-y-2">
            <Team name={g.away} record={g.away_record} logo={g.away_logo} abbr={g.away_abbr} />
            <Team name={g.home} record={g.home_record} logo={g.home_logo} abbr={g.home_abbr} />
          </div>

          {/* The two numbers, stacked. Side by side with a chip beside them
              they needed 217px, which no 390px phone has to spare once two
              team names are on the left — so the gap moved to the caption
              below, where it is said in words rather than twice over. */}
          <dl className="w-[104px] shrink-0 space-y-1 border-l border-terminal-border pl-3 text-right">
            <div>
              <dt className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">Market</dt>
              <dd className="font-mono text-sm font-black tabular-nums text-zinc-100">
                {spread?.market_label || '—'}
              </dd>
            </div>
            <div>
              <dt className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">StatEdge</dt>
              <dd className="font-mono text-sm font-black tabular-nums text-brand">
                {spread?.fair_label || '—'}
              </dd>
            </div>
          </dl>
        </div>

        {/* The honest caption, and it has three states rather than two.
            "No edge" is the usual answer on an NFL game line and the row is
            not ashamed of it — but a game the model has not been run on is a
            different thing entirely, and a dash in the StatEdge column means
            the same in both cases. Saying "model and market agree" about a
            game with no model behind it would be inventing agreement. */}
        {!entry.projected ? (
          <p className="mt-2.5 text-[11px] font-semibold uppercase tracking-wide text-zinc-500">
            Not projected yet
          </p>
        ) : spread?.market == null ? (
          <p className="mt-2.5 text-[11px] font-semibold uppercase tracking-wide text-zinc-500">
            No line posted
          </p>
        ) : hasEdge ? (
          <p className="mt-2.5 inline-flex items-center rounded-full bg-brand-soft px-2.5 py-1 text-[11px] font-black uppercase tracking-wide text-brand">
            {points.toFixed(1)} pts on {spread.side_abbr}
          </p>
        ) : (
          <p className="mt-2.5 text-[11px] font-semibold uppercase tracking-wide text-zinc-500">
            Model and market agree
          </p>
        )}
      </Link>
    </div>
  )
}
