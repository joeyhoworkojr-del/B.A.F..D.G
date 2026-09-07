import type { NewsItemOut } from '../../types'

const CATEGORY_LABEL: Record<string, string> = {
  injury: 'Injury',
  preview: 'Preview',
  recap: 'Recap',
  news: 'News',
}

const CATEGORY_TONE: Record<string, string> = {
  // Amber, not red: an injury report is notable, not a failure state.
  injury: 'border-signal-amber/40 bg-signal-amber-dim text-signal-amber',
  preview: 'border-signal-blue/30 bg-blue-50 text-signal-blue',
  recap: 'border-terminal-border bg-terminal-muted text-zinc-400',
  news: 'border-terminal-border bg-terminal-muted text-zinc-400',
}

function published(iso: string): string {
  if (!iso) return ''
  const t = new Date(iso).getTime()
  if (isNaN(t)) return ''
  const mins = Math.round((Date.now() - t) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs} hr ago`
  return new Date(t).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

/**
 * One story, attributed.
 *
 * Shows the headline and the publisher's own summary line only — the full
 * article stays at the source, behind the link. The projection note is
 * deliberate: the model does not read these stories, so the card says so
 * rather than letting a reader assume a headline moved a number.
 */
export function NewsCard({ item }: { item: NewsItemOut }) {
  const when = published(item.published)
  const tone = CATEGORY_TONE[item.category] ?? CATEGORY_TONE.news

  return (
    <article className="min-w-0 rounded-xl border border-terminal-border bg-terminal-surface p-4 card-lift">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-full border px-2 py-0.5 text-xs font-bold ${tone}`}>
          {CATEGORY_LABEL[item.category] ?? 'News'}
        </span>
        <span className="text-xs font-bold uppercase tracking-wide text-zinc-500">
          {item.league === 'ncaaf' ? 'NCAAF' : item.league.toUpperCase()}
        </span>
        {item.teams.slice(0, 3).map(t => (
          <span key={t} className="rounded bg-terminal-muted px-1.5 py-0.5 text-xs font-semibold text-zinc-400">
            {t}
          </span>
        ))}
        {when && <span className="ml-auto text-xs text-zinc-500">{when}</span>}
      </div>

      <h3 className="mt-2 text-base font-bold leading-snug text-zinc-100">
        {item.url ? (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-brand hover:underline"
          >
            {item.headline}
          </a>
        ) : item.headline}
      </h3>

      {item.description && (
        <p className="mt-1.5 text-sm leading-relaxed text-zinc-400">{item.description}</p>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-zinc-500">
        <span>
          {item.source}
          {item.byline ? ` · ${item.byline}` : ''}
        </span>
        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold text-brand hover:underline"
          >
            Read at {item.source} ↗
          </a>
        )}
        {/* Honest by default: the projection has not consumed this story. */}
        <span className="ml-auto rounded bg-terminal-muted px-2 py-0.5 font-medium text-zinc-500">
          {item.reflected_in_projection
            ? 'Reflected in projection'
            : 'Not yet reflected in projection'}
        </span>
      </div>
    </article>
  )
}
