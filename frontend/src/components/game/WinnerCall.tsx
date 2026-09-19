import type { WinnerOut } from '../../types'

const pct = (v: number) => `${Math.round(v * 100)}%`

const price = (v: number | null) =>
  v == null ? null : v > 0 ? `+${Math.round(v)}` : `${Math.round(v)}`

/** Wording for the band, not a second opinion — it sits on the same number. */
const BAND_WORD: Record<WinnerOut['band'], string> = {
  'toss-up': 'Too close to call',
  lean: 'Slight edge',
  clear: 'Clear favourite',
  strong: 'Strong favourite',
}

const BAND_TONE: Record<WinnerOut['band'], string> = {
  'toss-up': 'text-zinc-400',
  lean: 'text-zinc-300',
  clear: 'text-brand',
  strong: 'text-brand',
}

/**
 * Who wins the game, spread aside.
 *
 * The board already answered "who covers" and "over or under". It did not
 * answer the plainest question a reader arrives with, and the two are
 * genuinely different: a nine-point favourite the model makes seven still
 * wins the game, while the spread pick is the underdog.
 *
 * What this is not: a bet. It shows a probability, the price the book is
 * offering on that side where one is published, and whether the market names
 * the same team. It never renders for a finished game — the winner is a fact
 * by then, and presenting a result as a projection would be manufacturing a
 * track record.
 *
 * Deliberately two lines tall. It sits above the primary edge on the game
 * page, and a taller card pushed that edge off a 390×844 screen — measured,
 * not guessed: y=838 became y=974 the first time this was a padded panel.
 */
export function WinnerCall({ winner, boxed = false }: { winner: WinnerOut; boxed?: boolean }) {
  const american = price(winner.price_american)

  return (
    <div className={boxed ? 'rounded-card border border-terminal-border bg-terminal-surface px-4 py-2.5' : ''}>
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <span className="text-xs font-bold uppercase tracking-widest text-zinc-500">
          {winner.live ? 'Wins from here' : 'Wins outright'}
        </span>
        <span className={`text-xs font-semibold ${BAND_TONE[winner.band]}`}>
          {BAND_WORD[winner.band]}
        </span>
        {winner.live && (
          <span className="text-xs text-zinc-500">· live, not graded</span>
        )}
      </div>

      <div className="mt-0.5 flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <span className="text-[15px] font-bold text-zinc-100">{winner.team}</span>
        <span className="font-mono text-[15px] font-black tabular-nums text-zinc-100">
          {pct(winner.win_prob)}
        </span>
        {american && (
          <span className="font-mono text-xs tabular-nums text-zinc-500">{american}</span>
        )}
        {/* Only the disagreement earns words. When the market names the same
            team there is nothing a reader needs to act on. */}
        {winner.market_agrees === false ? (
          <span className="text-xs font-semibold text-signal-amber">
            · market has {winner.opponent}
          </span>
        ) : winner.market_agrees === true && winner.market_prob != null ? (
          <span className="text-xs text-zinc-500">
            · market {pct(winner.market_prob)}{winner.market_prob_is_implied ? ' (from the spread)' : ''}
          </span>
        ) : (
          <span className="text-xs text-zinc-500">· no market price</span>
        )}
      </div>
    </div>
  )
}
