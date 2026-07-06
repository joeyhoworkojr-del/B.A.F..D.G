import type { Sport } from './SportArt'
import { fieldBackdrop, SportGlyph } from './SportArt'

/** Consistent art-forward page header used across every sport page: the sport's
 *  field motif behind a glyph badge, title and subtitle. */
export function PageHero({
  sport, title, accent, subtitle,
}: { sport: Sport; title: string; accent?: string; subtitle?: string }) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-terminal-border bg-terminal-surface">
      {fieldBackdrop(sport, 'pointer-events-none absolute inset-0 h-full w-full')}
      <div className="relative flex items-center gap-4 px-5 py-6">
        <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-signal-amber-dim text-signal-blue shadow-sm">
          <SportGlyph sport={sport} className="h-8 w-8" />
        </span>
        <div className="min-w-0">
          <h1 className="font-display text-2xl font-bold text-zinc-100">
            {title}
            {accent && <> — <span className="text-signal-amber">{accent}</span></>}
          </h1>
          {subtitle && <p className="mt-1 font-body text-sm text-zinc-500">{subtitle}</p>}
        </div>
      </div>
    </div>
  )
}
