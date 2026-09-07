import { useState, useEffect } from 'react'
import { api } from '../api/client'
import { Sparkline } from '../components/Sparkline'
import type { AccuracyResponse, SignalScore } from '../types'

const LEAGUE_LABEL: Record<string, string> = { nfl: 'NFL', cfl: 'CFL', mlb: 'MLB', wc: 'Soccer' }

const pct = (v?: number | null) => (v == null ? '—' : `${(v * 100).toFixed(1)}%`)
const num = (v?: number | null, d = 2) => (v == null ? '—' : v.toFixed(d))

function SignalCard({ label, score, best, accent }: { label: string; score?: SignalScore | null; best: boolean; accent: string }) {
  return (
    <div className={`rounded-xl border bg-terminal-surface p-4 ${best ? 'border-signal-amber shadow-sm' : 'border-terminal-border'}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-body font-semibold uppercase tracking-widest" style={{ color: accent }}>{label}</span>
        {best && <span className="rounded-full bg-signal-amber-dim px-2 py-0.5 text-xs font-body font-semibold text-signal-amber">Most accurate</span>}
      </div>
      {score ? (
        <div className="mt-3 space-y-1.5">
          <div className="flex items-baseline justify-between">
            <span className="text-xs font-body text-zinc-500">Brier score</span>
            <span className="font-mono text-xl font-bold text-zinc-100">{num(score.brier, 4)}</span>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-xs font-body text-zinc-500">Winner hit rate</span>
            <span className="font-mono text-sm text-zinc-200">{pct(score.winner_hit_rate)}</span>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-xs font-body text-zinc-500">Games scored</span>
            <span className="font-mono text-sm text-zinc-300">{score.n}</span>
          </div>
        </div>
      ) : (
        <p className="mt-3 text-xs font-body text-zinc-500">No graded games yet for this signal.</p>
      )}
    </div>
  )
}

/** Verified results: every pre-game prediction is snapshotted, frozen, and graded
 *  against the final score. Model vs book vs Polymarket crowd, head to head. */
export function TrackRecord() {
  const [data, setData] = useState<AccuracyResponse | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.accuracy().then(setData).catch(e => setError(e.message))
  }, [])

  if (error) {
    return <div className="mx-auto max-w-4xl px-4 py-12 text-sm font-body text-signal-red">Couldn't load track record: {error}</div>
  }
  if (!data) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8 space-y-4">
        <div className="skeleton h-8 w-64 rounded" />
        <div className="grid gap-4 sm:grid-cols-3">{[0, 1, 2].map(i => <div key={i} className="skeleton h-40 rounded-xl" />)}</div>
      </div>
    )
  }

  const { overall, by_league, performance, recent, pending } = data
  const versions = data.model_versions ?? []
  const briers = [overall.model?.brier, overall.book?.brier, overall.crowd?.brier].filter((b): b is number => b != null)
  const bestBrier = briers.length ? Math.min(...briers) : null
  const isBest = (s?: SignalScore | null) => s != null && bestBrier != null && s.brier <= bestBrier + 1e-9
  const profit = performance.profit_units ?? 0

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 space-y-8">
      <div>
        <h1 className="font-display text-3xl font-bold text-zinc-100">Results</h1>
        <p className="mt-1 max-w-2xl text-sm font-body text-zinc-400">
          Every prediction is snapshotted before kickoff, frozen, and graded automatically against the final score.
          Nothing is edited after the fact. {pending > 0 && <span className="text-zinc-300">{pending} pick{pending === 1 ? '' : 's'} pending grading.</span>}
        </p>
      </div>

      {/* Two different things get called "the model's accuracy". They are kept
          apart here on purpose: only the pre-game record is graded. */}
      <div className="grid gap-3 md:grid-cols-2">
        <section className="rounded-xl border border-terminal-border bg-terminal-surface p-4">
          <h2 className="text-sm font-bold text-zinc-100">Pre-game predictions — graded</h2>
          <p className="mt-1.5 text-sm leading-relaxed text-zinc-400">
            {performance.total_picks > 0
              ? `${performance.total_picks} graded pick${performance.total_picks === 1 ? '' : 's'} settled against the final score. This is the record on this page.`
              : 'Nothing has graded yet. The numbers below fill in as games finish.'}
          </p>
          {data.storage_durable === false && (
            <p className="mt-3 rounded-lg border border-signal-amber/40 bg-signal-amber-dim px-3 py-2 text-xs leading-relaxed text-signal-amber">
              <span className="font-bold">This record is not yet permanent.</span> It is
              stored on the server’s own disk, which is replaced when the site is
              redeployed, so the history below can reset. Attaching a database makes it
              durable.
            </p>
          )}
          {versions.length > 0 && (
            <p className="mt-2 text-xs text-zinc-500">
              Model version{versions.length === 1 ? '' : 's'} in this record:{' '}
              <span className="font-mono text-zinc-400">{versions.join(', ')}</span>. A newer
              model can’t rewrite a prediction that is already open.
            </p>
          )}
        </section>

        <section className="rounded-xl border border-dashed border-terminal-border bg-terminal-muted p-4">
          <h2 className="text-sm font-bold text-zinc-100">Live in-game updates — not graded</h2>
          <p className="mt-1.5 text-sm leading-relaxed text-zinc-400">
            {data.live_note ??
              'Live in-game win probabilities are recalculated from the score and clock while a game is running. They are not snapshotted or graded, so they are not part of the record on this page.'}
          </p>
          <p className="mt-2 text-xs text-zinc-500">
            Grading a probability after the score is already known would flatter the record,
            so it isn’t counted.
          </p>
        </section>
      </div>

      {/* P/L chart — the "stock" view. Only shown once picks have actually
          graded; before that a zeroed chart would read as a real result. */}
      {performance.total_picks > 0 ? (
        <div className="rounded-xl border border-terminal-border bg-terminal-surface p-5 card-lift">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-xs font-body font-semibold uppercase tracking-widest text-zinc-500">Model P/L — 1 unit per pick at fair book odds</p>
              <p className={`mt-1 font-mono text-3xl font-bold ${profit >= 0 ? 'text-signal-green' : 'text-signal-red'}`}>
                {profit >= 0 ? '+' : ''}{num(profit)}u
              </p>
            </div>
            <div className="flex gap-6 text-right">
              {[
                ['Graded picks', String(performance.total_picks)],
                ['Historical hit rate', pct(performance.win_rate)],
                ['Avg edge', performance.avg_edge_pp == null ? '—' : `${performance.avg_edge_pp.toFixed(1)}pp`],
                ['ROI', performance.roi_pct == null ? '—' : `${performance.roi_pct >= 0 ? '+' : ''}${performance.roi_pct.toFixed(1)}%`],
              ].map(([l, v]) => (
                <div key={l}>
                  <p className="text-xs font-body uppercase tracking-wider text-zinc-500">{l}</p>
                  <p className="font-mono text-sm font-semibold text-zinc-100">{v}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="mt-4">
            <Sparkline data={performance.series} id="track-pl" height={120} />
          </div>
          <p className="mt-3 border-t border-terminal-border pt-3 text-xs leading-relaxed text-zinc-500">
            Historical hit rate is the share of past graded picks that came in. It is a
            backward-looking average, not a probability for any upcoming game — the model’s
            projection for a specific game is shown on that game’s page.
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-terminal-border bg-terminal-surface p-8 text-center">
          <p className="font-display text-lg font-semibold text-zinc-100">Profit/loss starts here</p>
          <p className="mx-auto mt-1 max-w-md text-sm font-body text-zinc-500">
            The P/L curve appears once graded games exist. Every prediction is snapshotted before kickoff
            and settled automatically at the final whistle — no results have graded yet.
            {pending > 0 && <span className="text-zinc-300"> {pending} pick{pending === 1 ? '' : 's'} are snapshotted and pending.</span>}
          </p>
        </div>
      )}

      {/* Head-to-head Brier */}
      <section className="space-y-3">
        <h2 className="font-display text-lg font-semibold text-zinc-100">Model vs. book vs. crowd</h2>
        <p className="text-xs font-body text-zinc-500 max-w-2xl">
          Brier score measures probability accuracy — lower is better. A coin flip scores 0.25.
          The same games, three forecasters: our model, the sportsbook's no-vig line, and Polymarket traders.
        </p>
        <div className="grid gap-4 sm:grid-cols-3">
          <SignalCard label="StatEdge model" score={overall.model} best={isBest(overall.model)} accent="#2563eb" />
          <SignalCard label="Sportsbook" score={overall.book} best={isBest(overall.book)} accent="#b45309" />
          <SignalCard label="Polymarket crowd" score={overall.crowd} best={isBest(overall.crowd)} accent="#7c3aed" />
        </div>
        {overall.model?.brier != null && overall.book?.brier != null && (
          <div className={`rounded-lg border px-4 py-3 text-sm font-body ${
            overall.model.brier <= overall.book.brier
              ? 'border-signal-green/40 bg-green-50 text-signal-green'
              : 'border-terminal-border bg-terminal-muted text-zinc-500'
          }`}>
            {overall.model.brier <= overall.book.brier
              ? `Model is beating the sportsbook by ${((overall.book.brier - overall.model.brier)).toFixed(4)} Brier over ${overall.model.n} graded games — that's the number that actually matters.`
              : `Model is trailing the sportsbook by ${((overall.model.brier - overall.book.brier)).toFixed(4)} Brier over ${overall.model.n} games. Nothing public reliably beats the closing line; the market-anchored "consensus" pick keeps our recommendations close to it while the ratings keep learning.`}
          </div>
        )}
      </section>

      {/* Per-league */}
      {Object.keys(by_league).length > 0 && (
        <section className="space-y-3">
          <h2 className="font-display text-lg font-semibold text-zinc-100">By league</h2>
          <div className="overflow-x-auto rounded-xl border border-terminal-border bg-terminal-surface">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="border-b border-terminal-border text-xs font-body uppercase tracking-wider text-zinc-500">
                  <th className="px-4 py-2.5">League</th>
                  <th className="px-4 py-2.5 text-right">Graded</th>
                  <th className="px-4 py-2.5 text-right">Model Brier</th>
                  <th className="px-4 py-2.5 text-right">Book Brier</th>
                  <th className="px-4 py-2.5 text-right">Model hit rate</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(by_league).map(([lg, b]) => (
                  <tr key={lg} className="border-b border-terminal-border/60 last:border-0">
                    <td className="px-4 py-2.5 font-body font-semibold text-zinc-200">{LEAGUE_LABEL[lg] ?? lg.toUpperCase()}</td>
                    <td className="px-4 py-2.5 text-right text-zinc-300">{b.games_graded}</td>
                    <td className="px-4 py-2.5 text-right text-signal-blue">{num(b.model?.brier, 4)}</td>
                    <td className="px-4 py-2.5 text-right text-zinc-400">{num(b.book?.brier, 4)}</td>
                    <td className="px-4 py-2.5 text-right text-zinc-200">{pct(b.model?.winner_hit_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Recent graded games */}
      <section className="space-y-3">
        <h2 className="font-display text-lg font-semibold text-zinc-100">Recent graded games</h2>
        {recent.length === 0 ? (
          <div className="rounded-xl border border-dashed border-terminal-border bg-terminal-surface p-8 text-center">
            <p className="text-sm font-body text-zinc-400">No games graded yet.</p>
            <p className="mt-1 text-xs font-body text-zinc-500">
              Predictions are snapshotted automatically whenever the Markets page loads a slate; results grade themselves when games finish.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-terminal-border bg-terminal-surface">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="border-b border-terminal-border text-xs font-body uppercase tracking-wider text-zinc-500">
                  <th className="px-4 py-2.5">Game</th>
                  <th className="px-4 py-2.5">League</th>
                  <th className="px-4 py-2.5 text-right">Final</th>
                  <th className="px-4 py-2.5 text-right">Model home %</th>
                  <th className="px-4 py-2.5 text-right">Book home %</th>
                  <th className="px-4 py-2.5 text-center">Model call</th>
                </tr>
              </thead>
              <tbody>
                {recent.map(g => {
                  const modelPickedHome = g.model_home_prob >= 0.5
                  const correct = (modelPickedHome && g.home_won === 1) || (!modelPickedHome && g.home_won === 0)
                  return (
                    <tr key={g.event_id} className="border-b border-terminal-border/60 last:border-0">
                      <td className="px-4 py-2.5 font-body text-zinc-200">{g.away} @ {g.home}</td>
                      <td className="px-4 py-2.5 text-zinc-500">{LEAGUE_LABEL[g.league] ?? g.league.toUpperCase()}</td>
                      <td className="px-4 py-2.5 text-right font-semibold text-zinc-100">{g.away_score}–{g.home_score}</td>
                      <td className="px-4 py-2.5 text-right text-signal-blue">{pct(g.model_home_prob)}</td>
                      <td className="px-4 py-2.5 text-right text-zinc-400">{pct(g.book_home_prob)}</td>
                      <td className="px-4 py-2.5 text-center">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-body font-semibold ${correct ? 'bg-green-100 text-signal-green' : 'bg-red-100 text-signal-red'}`}>
                          {correct ? 'HIT' : 'MISS'}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <p className="border-t border-terminal-border pt-4 text-xs font-body italic text-zinc-500">
        {data.note}
      </p>
    </div>
  )
}
