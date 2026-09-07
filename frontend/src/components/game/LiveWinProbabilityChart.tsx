import { MiniChart, type Point } from './MiniChart'

/**
 * Win probability over the course of the game.
 *
 * The backend does not persist a probability history yet, so this plots the
 * readings observed while this page has been open — labelled as such rather
 * than presented as the full game history.
 */
export function LiveWinProbabilityChart({
  points, teamLabel,
}: { points: Point[]; teamLabel: string }) {
  if (points.length < 2) {
    return (
      <p className="text-sm text-zinc-400">
        Tracking {teamLabel} win probability from now on — the chart appears once a
        second reading arrives. Historical probability isn’t stored server-side yet.
      </p>
    )
  }
  return (
    <div className="space-y-2">
      <p className="text-xs text-zinc-400">
        {teamLabel} win probability, sampled while this page has been open.
      </p>
      <MiniChart points={points} ariaLabel={`${teamLabel} live win probability`}
                 yMin={0} yMax={1} formatY={v => `${Math.round(v * 100)}%`} />
    </div>
  )
}
