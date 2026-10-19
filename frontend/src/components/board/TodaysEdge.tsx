import { Link } from 'react-router-dom'
import type { AccuracyResponse } from '../../types'

const pct1 = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`

/**
 * One headline figure, with the thing it is measured over underneath it.
 *
 * The caption is not decoration. A record of 88-15 and a record of 8-1 are
 * very different claims, and so is "+12% over four hundred picks" against the
 * same number over twelve. Every tile here carries its own denominator.
 */
function Tile({ label, value, caption, tone = 'plain', Icon }: {
  label: string
  value: string
  caption: string
  tone?: 'plain' | 'good' | 'bad'
  Icon: () => JSX.Element
}) {
  const valueTone =
    tone === 'good' ? 'text-brand' : tone === 'bad' ? 'text-signal-red' : 'text-white'
  return (
    <div className="min-w-0 rounded-panel bg-ink-soft px-3 py-3 ring-1 ring-ink-line">
      <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-ink-muted">
        <Icon />
        <span className="truncate">{label}</span>
      </p>
      <p className={`mt-1 font-mono text-2xl font-black leading-none tabular-nums ${valueTone}`}>
        {value}
      </p>
      <p className="mt-1 truncate text-[11px] text-ink-muted">{caption}</p>
    </div>
  )
}

const Trophy = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M7 4h10v5a5 5 0 0 1-10 0V4Z" /><path d="M7 6H4v2a3 3 0 0 0 3 3M17 6h3v2a3 3 0 0 1-3 3M9 20h6M12 14v6" />
  </svg>
)
const Chart = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <polyline points="3 17 9 11 13 15 21 7" /><polyline points="15 7 21 7 21 13" />
  </svg>
)
const Target = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="4" /><path d="M12 3v3M12 18v3M3 12h3M18 12h3" />
  </svg>
)

/**
 * The board's headline card.
 *
 * Three figures, and all three are things the ledger can prove: what the
 * graded record is, what following it returned, and whether the number we
 * recommended at beat the closing line.
 *
 * Notably absent is a hit rate against the market. The obvious third tile for
 * a product like this is "we beat the closing line N% of the time" — and the
 * backtest puts that number at about fifty, so the tile would be either false
 * or embarrassing and there is no version of it worth printing. Closing line
 * value answers the same question honestly, and where there is not enough of
 * it on file the tile says so instead of filling in.
 */
export function TodaysEdge({ acc, liveCount }: {
  acc: AccuracyResponse | null
  liveCount: number
}) {
  const perf = acc?.performance
  const graded = perf?.total_picks ?? 0
  const wins = perf?.wins ?? 0
  const losses = perf?.losses ?? Math.max(0, graded - wins)
  const roi = perf?.roi_pct
  const priced = perf?.priced_picks ?? 0
  const clv = perf?.avg_clv_points
  const clvTracked = perf?.clv_tracked ?? 0

  return (
    <section
      aria-labelledby="todays-edge"
      className="relative overflow-hidden rounded-hero bg-ink px-4 py-5 text-white"
    >
      {/* A field pattern rather than a photograph: it carries the same weight
          at a fraction of the bytes, and nothing on the page waits for it. */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-y-0 right-0 w-1/2 opacity-[0.07]">
        <svg viewBox="0 0 200 200" className="h-full w-full" fill="none" stroke="white" strokeWidth="1.5">
          {Array.from({ length: 9 }, (_, i) => (
            <line key={i} x1={20 + i * 20} y1="0" x2={20 + i * 20} y2="200" />
          ))}
          <ellipse cx="140" cy="100" rx="52" ry="30" transform="rotate(-20 140 100)" strokeWidth="2.5" />
          <path d="M112 112 168 88M126 96l10 10M136 86l10 10" strokeWidth="2.5" />
        </svg>
      </div>

      <div className="relative">
        <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-brand">
          Game Center
        </p>
        <h1 id="todays-edge" className="mt-1 font-display text-[34px] font-black leading-[1.05] tracking-tight">
          Today&rsquo;s <span className="text-brand">Edge</span>
        </h1>
        <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-ink-muted">
          NFL and college football, with the model&rsquo;s number beside the market&rsquo;s.
        </p>

        {liveCount > 0 && (
          <p className="mt-3 inline-flex items-center gap-2 rounded-full bg-brand/15 px-3 py-1.5 text-xs font-bold text-brand">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-brand" />
            {liveCount} LIVE {liveCount === 1 ? 'GAME' : 'GAMES'}
          </p>
        )}

        <div className="mt-4 grid grid-cols-3 gap-2">
          <Tile
            Icon={Trophy}
            label="Record"
            value={`${wins}–${losses}`}
            caption={graded > 0 ? `${graded} graded picks` : 'nothing graded yet'}
          />
          <Tile
            Icon={Chart}
            label="ROI"
            value={roi == null ? '—' : pct1(roi)}
            tone={roi == null ? 'plain' : roi >= 0 ? 'good' : 'bad'}
            caption={
              roi == null
                ? 'no price on file'
                : `${priced} priced pick${priced === 1 ? '' : 's'}`
            }
          />
          <Tile
            Icon={Target}
            label="Closing value"
            value={clv == null ? '—' : `${clv >= 0 ? '+' : ''}${clv.toFixed(2)}`}
            tone={clv == null ? 'plain' : clv >= 0 ? 'good' : 'bad'}
            caption={
              clv == null
                ? 'not tracked yet'
                : `pts vs close, ${clvTracked} tracked`
            }
          />
        </div>

        {/* What the three numbers above are, in the words that make them
            checkable. "Record" beside "ROI" reads as a betting record unless
            it says otherwise, and it is not one: it counts how often the side
            the model favoured won. The link is the point — a headline figure
            nobody can audit is a billboard. */}
        {graded > 0 && (
          <p className="mt-3 text-[11px] leading-relaxed text-ink-muted">
            Record is how often the side the model favoured won, over {graded} graded
            pre-game {graded === 1 ? 'pick' : 'picks'} — not a betting return.
            {roi == null && ' ROI needs a published price on the side we took; with none on file it stays blank rather than estimated.'}
            {' '}
            <Link to="/results" className="font-bold text-brand hover:underline">
              Full record &rsaquo;
            </Link>
          </p>
        )}
      </div>
    </section>
  )
}
