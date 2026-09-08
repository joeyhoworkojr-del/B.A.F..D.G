import { MiniChart, type Point } from './MiniChart'
import type { WinHistoryOut } from '../../types'

/**
 * Win probability across the whole game.
 *
 * The series comes from the server, which records a reading each time the
 * live model runs, so the chart survives a reload and shows the game rather
 * than only what this tab happened to witness. Scoring plays are called out
 * separately from the drift between them — the interesting part of a
 * predictive model is the movement that happens *before* a score.
 */
export function LiveWinProbabilityChart({
  history, teamLabel, fallback,
}: { history: WinHistoryOut | null; teamLabel: string; fallback?: Point[] }) {
  const recorded: Point[] = (history?.points ?? []).map(p => ({
    t: new Date(p.at).getTime(), v: p.home_win,
  }))
  const points = recorded.length >= 2 ? recorded : (fallback ?? [])
  const swing = history?.swing ?? null

  if (points.length < 2) {
    return (
      <p className="text-sm text-zinc-400">
        Tracking {teamLabel} win probability — the chart appears once a second reading
        arrives.
      </p>
    )
  }

  const moves = (history?.points ?? []).filter(p => p.scored).length

  return (
    <div className="space-y-2">
      <MiniChart points={points} ariaLabel={`${teamLabel} live win probability`}
                 yMin={0} yMax={1} formatY={v => `${Math.round(v * 100)}%`} />
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <p className="text-xs text-zinc-400">
          {teamLabel} win probability
          {recorded.length >= 2
            ? ` · ${points.length} readings`
            : ' · sampled while this page has been open'}
        </p>
        {swing && (
          <p className="font-mono text-xs tabular-nums text-zinc-500">
            {Math.round(swing.low * 100)}%–{Math.round(swing.high * 100)}% range
            {moves > 0 && ` · ${moves} scoring ${moves === 1 ? 'play' : 'plays'}`}
          </p>
        )}
      </div>
    </div>
  )
}
