import type { LiveGameOut, TodayModelOut } from '../../types'

const one = (v?: number | null) => (v == null ? '—' : v.toFixed(1))
const pct = (v?: number | null) => (v == null ? '—' : `${(v * 100).toFixed(1)}%`)

/**
 * Where the model expects a game in progress to finish.
 *
 * Distinct from the pre-game projection and labelled as such: this number moves
 * with the score and the clock, and presenting it as though it were the
 * original call would quietly rewrite what the model actually said beforehand.
 * Both are shown, with the movement between them, because the interesting part
 * is how far the game has dragged the projection.
 */
export function LiveScoreProjection({
  game, model,
}: { game: LiveGameOut; model: TodayModelOut }) {
  const projHome = model.live_proj_home ?? model.proj_home_score ?? model.home_expected
  const projAway = model.live_proj_away ?? model.proj_away_score ?? model.away_expected
  const preHome = model.proj_home_score ?? model.home_expected
  const preAway = model.proj_away_score ?? model.away_expected

  const homeWin = model.live_home_win ?? model.calibrated_home_win ?? model.home_win_prob
  const preWin = model.calibrated_home_win ?? model.home_win_prob
  const swing = homeWin != null && preWin != null ? homeWin - preWin : null

  const remaining = model.time_remaining_pct
  const scoredHome = game.home_score ?? 0
  const scoredAway = game.away_score ?? 0

  // How many more points the model expects each side to add from here.
  const toComeHome = projHome == null ? null : Math.max(0, projHome - scoredHome)
  const toComeAway = projAway == null ? null : Math.max(0, projAway - scoredAway)

  return (
    <section
      aria-labelledby="live-projection"
      className="rounded-card border border-signal-green/40 bg-terminal-surface"
    >
      <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-terminal-border px-4 py-3">
        <h2 id="live-projection" className="text-sm font-bold text-zinc-100">
          Projected final
        </h2>
        <span className="inline-flex items-center gap-1.5 text-xs font-bold text-signal-green">
          <span className="h-1.5 w-1.5 rounded-full bg-signal-green" />
          Updating live
        </span>
      </header>

      <div className="space-y-4 p-4">
        <div>
          <p className="font-mono text-3xl font-black tabular-nums text-zinc-100">
            {one(projAway)} – {one(projHome)}
          </p>
          <p className="mt-1 text-xs text-zinc-500">
            {game.away_abbr} at {game.home_abbr} · currently {scoredAway}–{scoredHome}
            {remaining != null && ` · ${Math.round(remaining)}% of the game left`}
          </p>
        </div>

        <dl className="grid grid-cols-2 gap-3 border-t border-terminal-border pt-3 text-sm">
          <div>
            <dt className="text-xs text-zinc-400">Still to score ({game.away_abbr})</dt>
            <dd className="font-mono font-bold tabular-nums text-zinc-100">{one(toComeAway)}</dd>
          </div>
          <div>
            <dt className="text-xs text-zinc-400">Still to score ({game.home_abbr})</dt>
            <dd className="font-mono font-bold tabular-nums text-zinc-100">{one(toComeHome)}</dd>
          </div>
          <div>
            <dt className="text-xs text-zinc-400">Live win probability ({game.home_abbr})</dt>
            <dd className="font-mono font-bold tabular-nums text-zinc-100">{pct(homeWin)}</dd>
          </div>
          <div>
            <dt className="text-xs text-zinc-400">Win prob. move since kickoff</dt>
            <dd className={`font-mono font-bold tabular-nums ${
              swing == null ? 'text-zinc-500'
              : swing > 0 ? 'text-signal-green' : swing < 0 ? 'text-signal-red' : 'text-zinc-100'
            }`}>
              {swing == null ? '—' : `${swing >= 0 ? '+' : ''}${(swing * 100).toFixed(1)} pts`}
            </dd>
          </div>
        </dl>

        <div className="border-t border-terminal-border pt-3">
          <p className="text-xs text-zinc-500">
            Before kickoff the model projected{' '}
            <span className="font-mono font-semibold text-zinc-400">
              {one(preAway)}–{one(preHome)}
            </span>
            {preWin != null && <> with {game.home_abbr} at {pct(preWin)}</>}. That call is
            frozen and is what the record grades — this line moves with the game and is
            never graded.
          </p>
        </div>
      </div>
    </section>
  )
}
