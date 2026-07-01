export function About() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-8 space-y-8 font-body text-sm text-zinc-300 leading-relaxed">
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-100">About StatEdge</h1>
        <p className="text-zinc-500 mt-1">Sports analytics platform — 2026 FIFA World Cup edition.</p>
      </div>

      {/* Model */}
      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-signal-amber uppercase tracking-widest">The Model</h2>
        <p>
          Soccer predictions use an <strong className="text-zinc-100">Elo → Poisson</strong> pipeline. Each team's Elo rating is
          converted to expected goals via an exponential goal-ratio formula (μ=1.06, Q=1540), then a scoreline
          probability grid is computed exactly from the Poisson distribution — no simulation noise in the headline numbers.
        </p>
        <p>
          On live Round-of-16 fixtures, the model is <strong className="text-zinc-100">blended 40/60</strong> with SportRadar's
          published win probabilities. SportRadar sees today's injuries and lineup that Elo cannot; blending two decent
          estimators consistently outperforms either alone.
        </p>
        <p>
          Over/unders and BTTS come from the same Poisson distribution and are as reliable as the match result. Player
          props are derived from each scorer's real tournament goal-share × team xG against the specific opponent — they
          shift by matchup, but can't see today's starting XI.
        </p>
        <p>
          Monte Carlo runs 50,000 simulations. In knockout mode it adds 30-minute extra time (λ × ⅓) and a 50/50
          penalty tiebreak. Standard error: ±0.22% at 50k sims.
        </p>
      </section>

      {/* NFL */}
      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-signal-amber uppercase tracking-widest">NFL Model</h2>
        <p>
          NFL predictions use a calibrated Elo win-probability formula with a home-field advantage of +48 Elo points
          (≈3 points on the spread). The spread is derived from the logit of the win probability; ATS cover probability
          regresses toward 50/50 as the spread shrinks.
        </p>
      </section>

      {/* Calibration */}
      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-signal-amber uppercase tracking-widest">Validation</h2>
        <div className="rounded-lg border border-terminal-border bg-terminal-surface p-4 font-mono text-xs space-y-1">
          <div className="grid grid-cols-3 gap-2 text-zinc-500 border-b border-terminal-border pb-1">
            <span>Fixture</span><span className="text-right">StatEdge</span><span className="text-right">SportRadar</span>
          </div>
          {[
            ['ARG – CPV', '80.8%', '82.3%'],
            ['SUI – DZA', '49.6%', '46.5%'],
            ['MEX – ECU (host)', '39.3%', '43.6%'],
            ['FRA – ENG', '41.2%', '42.0%'],
            ['AUS – EGY', '44.7%', '38.0% ⚠'],
          ].map(([fix, se, sr]) => (
            <div key={fix} className="grid grid-cols-3 gap-2 text-zinc-300">
              <span>{fix}</span>
              <span className="text-right text-signal-amber">{se}</span>
              <span className="text-right text-zinc-500">{sr}</span>
            </div>
          ))}
        </div>
        <p className="text-xs text-zinc-500">
          AUS–EGY diverges because SportRadar has squad/form data the Elo rating can't see. Both numbers are shown
          in the UI so nothing is hidden.
        </p>
      </section>

      {/* Honest limits */}
      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-signal-amber uppercase tracking-widest">Honest limits</h2>
        <ul className="list-disc list-inside space-y-2 text-zinc-400">
          <li>Single knockout games are the highest-variance event in sport. A 65% favourite loses 1-in-3.</li>
          <li>Elo is blind to injuries and today's lineup — always check team news.</li>
          <li>Good international soccer models top out ~66–70% straight-up accuracy. Anything higher is overfitting.</li>
          <li>Over/unders are the most trustworthy output. Player props are the softest.</li>
          <li>Penalties are near coin-flips — the model correctly treats them as 50/50.</li>
        </ul>
      </section>

      {/* Data */}
      <section className="space-y-2">
        <h2 className="font-display text-base font-semibold text-signal-amber uppercase tracking-widest">Data sources</h2>
        <ul className="list-disc list-inside space-y-1 text-zinc-400 text-xs">
          <li>Elo ratings — eloratings.net scale (June 2026)</li>
          <li>SportRadar win probabilities — used as calibration reference and blend component</li>
          <li>Top scorer data — official FIFA tournament records</li>
          <li>NFL Elo — end-of-2025 season calibration</li>
        </ul>
      </section>

      <p className="text-xs text-zinc-600 italic border-t border-terminal-border pt-4">
        StatEdge v1.0 · For information purposes only. No guarantees of accuracy.
      </p>
    </div>
  )
}
