import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import type { NewsFeedOut } from '../../types'

/** Headlines on the homepage before it stops being a strip. */
const SHOWN = 4

const CATEGORY_LABEL: Record<string, string> = {
  injury: 'Injury', preview: 'Preview', recap: 'Recap', news: 'News',
}

/**
 * Attributed headlines, linking out to the publisher.
 *
 * Headline and source only — never the article body, which belongs to whoever
 * wrote it. The line about the model not reading these is not a disclaimer for
 * its own sake: a news item beside a projection implies the projection
 * accounts for it, and it does not.
 */
export function NewsStrip() {
  const [feed, setFeed] = useState<NewsFeedOut | null>(null)

  useEffect(() => {
    let alive = true
    api.news('all', SHOWN * 2)
      .then(d => { if (alive) setFeed(d) })
      .catch(() => { if (alive) setFeed(null) })
    return () => { alive = false }
  }, [])

  const items = (feed?.items ?? []).slice(0, SHOWN)
  if (items.length === 0) return null

  return (
    <section aria-labelledby="news-strip" className="space-y-2.5">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 id="news-strip" className="text-xs font-bold uppercase tracking-widest text-zinc-500">
            Around the leagues
          </h2>
          <p className="mt-0.5 text-xs text-zinc-500">
            Headlines from {feed?.source || 'the wire'}. The model does not read these —
            nothing here is reflected in a projection.
          </p>
        </div>
        <Link to="/news" className="whitespace-nowrap text-sm font-semibold text-brand hover:underline">
          All news ›
        </Link>
      </div>
      <ul className="grid gap-2 sm:grid-cols-2">
        {items.map(item => (
          <li key={item.id}>
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex h-full flex-col rounded-xl border border-terminal-border bg-terminal-surface px-3.5 py-3 hover:border-zinc-500"
            >
              <span className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-zinc-500">
                {item.league && item.league !== 'all' && <span>{item.league.toUpperCase()}</span>}
                <span>{CATEGORY_LABEL[item.category] ?? item.category}</span>
              </span>
              <span className="mt-1 text-sm font-bold leading-snug text-zinc-100">
                {item.headline}
              </span>
              <span className="mt-auto pt-2 text-xs text-zinc-500">{item.source}</span>
            </a>
          </li>
        ))}
      </ul>
    </section>
  )
}
