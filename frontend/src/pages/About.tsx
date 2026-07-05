import { Link } from 'react-router-dom'

export function About() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-8 space-y-8 font-body text-sm text-zinc-300 leading-relaxed">
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-100">About StatEdge</h1>
        <p className="text-zinc-500 mt-1">A stock market for sports analytics — model, book, and crowd, priced side by side.</p>
      </div>

      {/* How it works */}
      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-signal-amber uppercase tracking-widest">How it works</h2>
        <p>
          StatEdge runs its own probability models for every game on today's slate — MLB, NFL, CFL and
          international soccer — then compares three prices for the same event:
        </p>
        <ul className="list-disc list-inside space-y-1.5 text-zinc-400">
          <li><strong className="text-signal-blue">The model</strong> — our in-house projection from team strength, park/venue, weather and lineups.</li>
          <li><strong className="text-zinc-100">The book</strong> — live sportsbook lines (spread, total, moneylines) with the vig stripped out.</li>
          <li><strong className="text-signal-purple">The crowd</strong> — real-money Polymarket prediction-market prices and volume.</li>
        </ul>
        <p>
          When the model's probability is meaningfully higher than the market's, that's an edge — rated A/B/C by size,
          with expected value and quarter-Kelly stake sizing shown for every rated market.
        </p>
      </section>

      {/* Models */}
      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-signal-amber uppercase tracking-widest">The models</h2>
        <p>
          <strong className="text-zinc-100">Soccer</strong> uses a Dixon-Coles-corrected Poisson: Elo-derived expected goals,
          team attack/defense styles, and a low-score correlation adjustment (ρ = −0.13). The full scoreline grid is computed
          exactly, so win/draw/loss, totals at any line, and BTTS all come from one consistent distribution.
        </p>
        <p>
          <strong className="text-zinc-100">NFL &amp; CFL</strong> use an expected-points engine: team ratings plus league-calibrated
          home-field advantage produce a projected margin and total, each modeled as a Normal distribution with historically
          fitted volatility (NFL σ ≈ 13.4 on margin; CFL runs higher-variance). Cover and over probabilities are read off
          those distributions at the live market line.
        </p>
        <p>
          <strong className="text-zinc-100">MLB</strong> is a Poisson run-scoring grid: team run rates adjusted for starting
          pitchers, park factors (Coors at 1.24), and home-field, with extra innings resolved from the tie mass.
        </p>
      </section>

      {/* Live data */}
      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-signal-amber uppercase tracking-widest">Live data</h2>
        <ul className="list-disc list-inside space-y-1.5 text-zinc-400">
          <li>Scores, schedules and sportsbook odds refresh from ESPN roughly every minute.</li>
          <li>Stadium weather (wind, temperature, precipitation) comes from Open-Meteo and feeds directly into totals for outdoor venues.</li>
          <li>Polymarket prices and volume refresh every two minutes and are matched to each game.</li>
          <li>Lineup and injury toggles re-run the model instantly with players in or out.</li>
        </ul>
        <p className="text-xs text-zinc-500">
          Every feed is fail-safe: if a source is briefly unreachable, the last good snapshot is served with its timestamp
          rather than stale data pretending to be fresh.
        </p>
      </section>

      {/* Verified results */}
      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-signal-amber uppercase tracking-widest">Verified results</h2>
        <p>
          Every prediction on the Markets page is snapshotted <em>before</em> the game starts — model probability, the book's
          no-vig price, and the Polymarket crowd price. When the game ends it grades itself against the final score, and the
          snapshot is frozen. The <Link to="/track" className="text-signal-amber underline underline-offset-2">Track Record</Link> page
          scores all three forecasters head-to-head (Brier score) and shows the model's profit/loss betting one unit per pick
          at fair book odds. Nothing is edited after the fact.
        </p>
      </section>

      {/* Honest limits */}
      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-signal-amber uppercase tracking-widest">Honest limits</h2>
        <ul className="list-disc list-inside space-y-2 text-zinc-400">
          <li>Single games are the highest-variance event in sport. A 65% favourite still loses one time in three.</li>
          <li>Team ratings update slower than news. Always check injuries — the lineup toggles exist for exactly that reason.</li>
          <li>Sportsbook closing lines are extremely efficient. Persistent, large edges against them should be treated with suspicion, not excitement.</li>
          <li>The track record is the only honest measure of the model — and it needs a real sample size before it means anything.</li>
        </ul>
      </section>

      {/* Data */}
      <section className="space-y-2">
        <h2 className="font-display text-base font-semibold text-signal-amber uppercase tracking-widest">Data sources</h2>
        <ul className="list-disc list-inside space-y-1 text-zinc-400 text-xs">
          <li>ESPN public scoreboards — live scores, schedules, and sportsbook consensus lines</li>
          <li>Open-Meteo — stadium weather forecasts</li>
          <li>Polymarket Gamma API — prediction-market prices and volume</li>
          <li>Elo ratings — eloratings.net scale (soccer); league-calibrated power ratings (NFL/CFL/MLB)</li>
        </ul>
      </section>

      <p className="text-xs text-zinc-600 italic border-t border-terminal-border pt-4">
        StatEdge · Analytics for information and entertainment only. Not betting advice. If you gamble, set limits and stick to them.
      </p>
    </div>
  )
}
