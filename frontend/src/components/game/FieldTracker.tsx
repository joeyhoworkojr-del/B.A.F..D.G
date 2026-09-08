import { useEffect, useRef, useState } from 'react'
import type { LiveGameOut } from '../../types'

/**
 * Where the ball is, and which way the offence is going.
 *
 * The field is always drawn with the team in possession attacking to the
 * right, so "forward" means the same thing on every drive and the marker's
 * direction of travel reads as progress rather than as a change of ends. The
 * ball and the first-down marker are positioned as percentages and animated
 * with a CSS transition, so a gain slides instead of jumping — the movement is
 * the point.
 *
 * When the feed does not publish a position, this renders the situation text
 * and no field. Drawing a marker at a guessed spot would look exactly like a
 * real one.
 */
export function FieldTracker({ game }: { game: LiveGameOut }) {
  const yardLine = game.yard_line
  const hasPosition = typeof yardLine === 'number' && yardLine >= 0 && yardLine <= 100

  const offence = game.possession_abbr || ''
  const defence = offence === game.home_abbr ? game.away_abbr : game.home_abbr

  // First-down marker, clamped: inside the ten it is the goal line, not the
  // yard line arithmetic would produce.
  const toGain = game.distance ?? null
  const firstDown =
    hasPosition && toGain != null ? Math.min(100, (yardLine as number) + toGain) : null

  const prev = useRef<number | null>(null)
  const [gained, setGained] = useState<number | null>(null)

  useEffect(() => {
    if (!hasPosition) return
    const line = yardLine as number
    if (prev.current != null && prev.current !== line) {
      setGained(line - prev.current)
      const t = setTimeout(() => setGained(null), 2600)
      prev.current = line
      return () => clearTimeout(t)
    }
    prev.current = line
  }, [yardLine, hasPosition])

  if (!hasPosition) {
    return (
      <div className="rounded-lg border border-terminal-border bg-terminal-muted px-3 py-4 text-center">
        <p className="font-display text-base font-black text-zinc-100">
          {game.down_distance || `Q${game.period ?? ''} ${game.clock ?? ''}`.trim() || 'In progress'}
        </p>
        <p className="mt-1 text-xs text-zinc-500">
          {offence ? `${offence} has the ball · ` : ''}field position not published for this game
        </p>
      </div>
    )
  }

  const ball = yardLine as number
  const inRedZone = game.is_red_zone || ball >= 80

  return (
    <figure className="m-0">
      <div
        className="relative overflow-hidden rounded-lg border border-terminal-border bg-[#0f7a3d]"
        role="img"
        aria-label={
          `${offence || 'The offence'} on the ${ball <= 50 ? 'own' : "opponent's"} ` +
          `${ball <= 50 ? ball : 100 - ball} yard line, attacking the ${defence || 'opposing'} end zone` +
          (toGain != null ? `, ${toGain} to go` : '')
        }
      >
        {/* Five-yard stripes. Alternating shade rather than lines keeps the
            marker legible at phone width. */}
        <div className="absolute inset-0 flex" aria-hidden="true">
          {Array.from({ length: 20 }, (_, i) => (
            <div
              key={i}
              className={`h-full flex-1 ${i % 2 === 0 ? 'bg-white/[0.06]' : 'bg-transparent'}`}
            />
          ))}
        </div>

        {/* End zones. The one being attacked is on the right, always. */}
        <div className="absolute inset-y-0 left-0 w-[9%] bg-black/25" aria-hidden="true" />
        <div
          className={`absolute inset-y-0 right-0 w-[9%] transition-colors duration-500 ${
            inRedZone ? 'bg-signal-red/70' : 'bg-black/25'
          }`}
          aria-hidden="true"
        />

        <div className="relative flex h-28 items-stretch px-[9%] sm:h-32">
          {/* Midfield */}
          <div className="absolute inset-y-0 left-1/2 w-px bg-white/40" aria-hidden="true" />

          {/* First-down marker */}
          {firstDown != null && (
            <div
              className="absolute inset-y-0 w-0.5 bg-signal-amber transition-[left] duration-700 ease-out"
              style={{ left: `calc(9% + ${firstDown * 0.82}%)` }}
              aria-hidden="true"
            />
          )}

          {/* The ball */}
          <div
            className="absolute top-1/2 z-10 -translate-x-1/2 -translate-y-1/2 transition-[left] duration-700 ease-out"
            style={{ left: `calc(9% + ${ball * 0.82}%)` }}
          >
            <div className="grid place-items-center rounded-full bg-white px-2 py-1 shadow-lg">
              <span className="font-mono text-[11px] font-black leading-none text-zinc-900">
                {offence || '●'}
              </span>
            </div>
          </div>

          {/* Gain or loss on the last play, shown briefly where it happened. */}
          {gained != null && gained !== 0 && (
            <div
              className="absolute top-2 z-10 -translate-x-1/2 transition-[left] duration-700 ease-out"
              style={{ left: `calc(9% + ${ball * 0.82}%)` }}
            >
              <span
                className={`rounded-full px-2 py-0.5 text-[11px] font-black tabular-nums ${
                  gained > 0 ? 'bg-white text-signal-green' : 'bg-white text-signal-red'
                }`}
              >
                {gained > 0 ? `+${gained}` : gained}
              </span>
            </div>
          )}
        </div>

        {/* End-zone labels */}
        <span className="pointer-events-none absolute inset-y-0 left-0 grid w-[9%] place-items-center text-[10px] font-black uppercase tracking-wider text-white/70">
          {offence || ''}
        </span>
        <span className="pointer-events-none absolute inset-y-0 right-0 grid w-[9%] place-items-center text-[10px] font-black uppercase tracking-wider text-white/70">
          {defence || ''}
        </span>
      </div>

      <figcaption className="mt-2 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <span className="font-display text-sm font-black text-zinc-100">
          {game.down_distance || (offence ? `${offence} ball` : 'In progress')}
        </span>
        <span className="text-xs text-zinc-500">
          {ball >= 100
            ? 'Goal line'
            : `${100 - ball} yards from the ${defence || 'opposing'} end zone`}
          {firstDown != null && firstDown >= 100 ? ' · goal to go' : ''}
        </span>
      </figcaption>
    </figure>
  )
}
