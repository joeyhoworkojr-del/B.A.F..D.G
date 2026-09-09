import type { GameCommunityOut, LiveGameOut, MarketKey, MarketOut } from '../../types'

const fmtAmerican = (v?: number | null) =>
  v == null ? '—' : v > 0 ? `+${Math.round(v)}` : `${Math.round(v)}`

/** Logo for a side, where the side is a team. Totals have no logo. */
function sideLogo(game: LiveGameOut, side: string): string | undefined {
  if (side === 'home') return game.home_logo
  if (side === 'away') return game.away_logo
  return undefined
}

/**
 * What to put in the crest's place when there is no crest.
 *
 * The side of a fixture is an implementation detail — "HOM" and "AWA" mean
 * nothing to a reader. A team gets its code; over and under get theirs.
 */
function sideBadge(game: LiveGameOut, side: string): string {
  if (side === 'home') return (game.home_abbr || 'HOME').slice(0, 4)
  if (side === 'away') return (game.away_abbr || 'AWAY').slice(0, 4)
  return side.slice(0, 1).toUpperCase()
}

/**
 * The headline question for a market, and both answers side by side.
 *
 * This is a comparison, not a bet slip. Each side shows the price the book is
 * offering and, beside it, what the model thinks — which is the entire reason
 * to read StatEdge rather than an odds screen. The side the model prefers is
 * marked, and nothing here places, accepts or records a wager.
 */
export function WhoWins({
  game, markets, active, onChange, community, onMakePick,
}: {
  game: LiveGameOut
  markets: MarketOut[]
  active: MarketKey
  onChange: (key: MarketKey) => void
  community?: GameCommunityOut | null
  onMakePick?: () => void
}) {
  const market = markets.find(m => m.key === active) ?? markets[0]
  if (!market) return null

  const best = market.selections.reduce<number>(
    (m, s) => Math.max(m, s.model_prob), 0)
  const picks = community?.total_picks ?? 0

  return (
    <section
      aria-labelledby="who-wins"
      className="rounded-card border border-terminal-border bg-terminal-surface"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 px-4 pt-4">
        <h2 id="who-wins" className="text-base font-bold text-zinc-100">{market.question}</h2>
        {/* Real published picks by real accounts — not a vote widget. */}
        {picks > 0 && (
          <span className="text-sm text-zinc-500">
            {picks.toLocaleString()} published pick{picks === 1 ? '' : 's'}
          </span>
        )}
      </div>

      {markets.length > 1 && (
        <div className="flex gap-1.5 overflow-x-auto px-4 pt-3 no-scrollbar" role="tablist" aria-label="Market">
          {markets.map(m => (
            <button
              key={m.key}
              role="tab"
              type="button"
              aria-selected={m.key === active}
              onClick={() => onChange(m.key)}
              className={`tap shrink-0 rounded-full px-3.5 text-xs font-bold uppercase tracking-wide transition ${
                m.key === active
                  ? 'bg-brand text-white'
                  : 'bg-terminal-muted text-zinc-500 hover:text-zinc-300'
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-2.5 p-4">
        {market.selections.map(s => {
          const favoured = s.model_prob >= best && market.selections.length > 1
          const logo = sideLogo(game, s.side)
          return (
            <div
              key={s.side}
              className={`rounded-xl border p-3 ${
                favoured
                  ? 'border-brand/50 bg-brand-soft'
                  : 'border-terminal-border bg-terminal-surface'
              }`}
            >
              <div className="flex items-center gap-2">
                {logo
                  ? <img src={logo} alt="" className="h-7 w-7 shrink-0 object-contain" loading="lazy" />
                  : <span aria-hidden="true"
                          className="grid h-7 w-7 shrink-0 place-items-center rounded bg-terminal-muted text-[10px] font-bold text-zinc-400">
                      {sideBadge(game, s.side)}
                    </span>}
                <span className="min-w-0 flex-1 text-sm font-bold leading-tight text-zinc-100">
                  {s.label}
                </span>
              </div>

              <div className="mt-2 flex items-baseline justify-between gap-2">
                <span className="font-mono text-base font-bold tabular-nums text-zinc-100">
                  {fmtAmerican(s.price_american)}
                </span>
                <span className={`font-mono text-lg font-black tabular-nums ${
                  favoured ? 'text-brand' : 'text-zinc-300'
                }`}>
                  {Math.round(s.model_prob * 100)}%
                </span>
              </div>
              <div className="flex items-baseline justify-between gap-2 text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
                <span>Price</span>
                <span>Model</span>
              </div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-terminal-muted">
                <div
                  className={`h-full rounded-full ${favoured ? 'bg-brand' : 'bg-zinc-700'}`}
                  style={{ width: `${Math.round(s.model_prob * 100)}%` }}
                />
              </div>
              {favoured && (
                <p className="mt-1.5 text-xs font-semibold text-brand">Model’s side</p>
              )}
            </div>
          )
        })}
      </div>

      {onMakePick && (
        <div className="px-4 pb-2 text-right">
          <button
            type="button"
            onClick={onMakePick}
            className="text-sm font-semibold text-brand hover:underline"
          >
            Publish your own pick ›
          </button>
        </div>
      )}

      <p className="border-t border-terminal-border px-4 py-2.5 text-xs leading-relaxed text-zinc-500">
        {market.assumed_price
          ? 'Priced at −110 where the feed publishes no price. '
          : `Prices from ${market.source || 'the public feed'}. `}
        Lines move. StatEdge does not accept or process wagers, and publishing a
        pick here does not place one.
      </p>
    </section>
  )
}
