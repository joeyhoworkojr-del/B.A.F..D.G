import type { WhyOut } from '../../types'

const signed = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(1)}`

const SOURCE_LABEL: Record<string, string> = {
  ratings: 'Ratings',
  weather: 'Weather',
  lineup: 'Availability',
  line: 'Line move',
  anchor: 'Market anchor',
  missing: 'Missing input',
}

const SOURCE_TONE: Record<string, string> = {
  missing: 'text-signal-amber',
  line: 'text-zinc-300',
}

const STATE_LABEL: Record<WhyOut['line']['state'], string> = {
  value: 'Still value',
  gone: 'Edge gone',
  unknown: 'No line yet',
}

const STATE_TONE: Record<WhyOut['line']['state'], string> = {
  value: 'border-brand/50 bg-brand/10 text-brand',
  gone: 'border-terminal-border bg-terminal-muted/60 text-zinc-400',
  unknown: 'border-terminal-border bg-terminal-muted/60 text-zinc-500',
}

/**
 * Why StatEdge has the number it has.
 *
 * Every row is an input the model actually read, with the points it moved
 * where it moved any. Nothing is written because it sounds like analysis: a
 * missing input is listed as missing, in amber, rather than quietly left out —
 * a short honest list is worth more than a plausible fabrication, and a
 * fabrication would defeat the entire purpose of the section.
 *
 * The line history sits at the top because by kick-off it is the live
 * question: the model said one thing on Thursday, the market has moved since,
 * and a reader needs to know whether anything is left in it.
 */
export function WhyThisEdge({ why, boxed = true }: { why: WhyOut; boxed?: boolean }) {
  if (why.reasons.length === 0) return null
  const { line } = why
  const subject = why.side_abbr || 'this number'

  return (
    <section
      id="why"
      aria-labelledby="why-heading"
      className={boxed ? 'rounded-card border border-terminal-border bg-terminal-surface p-4' : ''}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h2 id="why-heading" className="text-base font-bold text-zinc-100">
          Why StatEdge has {subject}
          {why.points != null && (
            <span className="text-brand"> by {why.points.toFixed(1)} pts</span>
          )}
        </h2>
        <span className={`rounded-full border px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide ${STATE_TONE[line.state]}`}>
          {STATE_LABEL[line.state]}
        </span>
      </div>

      {line.opening != null && line.current != null && (
        <p className="mt-1 font-mono text-xs tabular-nums text-zinc-400">
          Opened {signed(line.opening)} · now {signed(line.current)}
          {why.fair_label && <> · StatEdge {why.fair_label}</>}
        </p>
      )}
      {line.note && <p className="mt-1 text-xs text-zinc-500">{line.note}</p>}

      <ul className="mt-3 space-y-2">
        {why.reasons.map((r, i) => (
          <li key={`${r.source}-${i}`} className="border-t border-terminal-border/60 pt-2 first:border-t-0 first:pt-0">
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
              <span className={`text-[10px] font-bold uppercase tracking-widest ${SOURCE_TONE[r.source] ?? 'text-zinc-500'}`}>
                {SOURCE_LABEL[r.source] ?? r.source}
              </span>
              <span className="text-sm font-semibold text-zinc-100">{r.label}</span>
              {r.impact_points != null && (
                <span className="font-mono text-xs font-bold tabular-nums text-brand">
                  {signed(r.impact_points)} pts
                </span>
              )}
            </div>
            <p className="mt-0.5 text-xs leading-relaxed text-zinc-500">{r.detail}</p>
          </li>
        ))}
      </ul>

      <p className="mt-3 border-t border-terminal-border/60 pt-2 text-xs leading-relaxed text-zinc-500">
        {why.basis}
      </p>
    </section>
  )
}
