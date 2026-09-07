import { useMemo, useState } from 'react'
import { useNews } from '../hooks/useNews'
import { NewsCard } from '../components/news/NewsCard'
import { DataFreshnessBadge } from '../components/game/DataFreshnessBadge'
import type { FootballLeague, NewsCategory } from '../types'

const LEAGUES: { id: 'all' | FootballLeague; label: string }[] = [
  { id: 'all', label: 'All football' },
  { id: 'ncaaf', label: 'NCAAF' },
  { id: 'nfl', label: 'NFL' },
]

const CATEGORIES: { id: 'all' | NewsCategory; label: string }[] = [
  { id: 'all', label: 'Everything' },
  { id: 'injury', label: 'Injuries' },
  { id: 'preview', label: 'Previews' },
  { id: 'recap', label: 'Recaps' },
]

const pill = (active: boolean) =>
  `tap inline-flex items-center rounded-full px-4 text-sm font-bold transition ${
    active
      ? 'bg-brand text-white shadow-card'
      : 'bg-terminal-muted text-zinc-400 hover:text-zinc-100'
  }`

export function News() {
  const [league, setLeague] = useState<'all' | FootballLeague>('all')
  const [category, setCategory] = useState<'all' | NewsCategory>('all')
  const { feed, loading, error } = useNews(league)

  const items = useMemo(
    () => (feed?.items ?? []).filter(i => category === 'all' || i.category === category),
    [feed, category],
  )

  return (
    <div className="mx-auto w-full max-w-app px-4 py-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-black text-zinc-100">News</h1>
          <p className="mt-1 text-sm text-zinc-400">
            Football headlines from ESPN. Summaries are the publisher’s own — follow a link
            to read the full story at the source.
          </p>
        </div>
        <DataFreshnessBadge
          fetchedAt={feed?.fetched_at}
          source={feed?.source ?? 'ESPN'}
          ok={feed?.ok !== false}
          staleAfterSeconds={600}
        />
      </header>

      <div className="mt-4 flex flex-wrap gap-2">
        {LEAGUES.map(l => (
          <button key={l.id} type="button" onClick={() => setLeague(l.id)}
            aria-pressed={league === l.id} className={pill(league === l.id)}>
            {l.label}
          </button>
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {CATEGORIES.map(c => (
          <button key={c.id} type="button" onClick={() => setCategory(c.id)}
            aria-pressed={category === c.id} className={pill(category === c.id)}>
            {c.label}
          </button>
        ))}
      </div>

      <p className="mt-4 rounded-lg border border-terminal-border bg-terminal-muted px-3 py-2 text-sm text-zinc-500">
        The model does not read these stories. A projection changes only when the inputs it
        actually consumes change, so every item below is marked{' '}
        <span className="font-semibold text-zinc-400">Not yet reflected in projection</span>.
      </p>

      {error && !feed && (
        <p role="alert" className="mt-6 text-sm text-signal-red">
          Couldn’t load the news feed: {error}
        </p>
      )}

      {loading && !feed && (
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          {[0, 1, 2, 3].map(i => <div key={i} className="skeleton h-40 rounded-xl" />)}
        </div>
      )}

      {feed && items.length === 0 && (
        <p className="mt-6 text-sm text-zinc-400">
          {feed.ok
            ? 'No stories match this filter right now.'
            : 'The news feed is unreachable, so there is nothing to show. This is a source problem, not an empty news day.'}
        </p>
      )}

      {items.length > 0 && (
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          {items.map(item => <NewsCard key={item.id} item={item} />)}
        </div>
      )}

      {feed && (
        <p className="mt-6 text-xs text-zinc-500">{feed.attribution}</p>
      )}
    </div>
  )
}
