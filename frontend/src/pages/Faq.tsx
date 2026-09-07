import { useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { FaqList } from '../components/faq/FaqList'
import { FAQ, FAQ_CATEGORIES, type FaqCategory } from '../content/faq'

const pill = (active: boolean) =>
  `tap inline-flex items-center rounded-full px-4 text-sm font-bold transition ${
    active
      ? 'bg-brand text-white shadow-card'
      : 'bg-terminal-muted text-zinc-400 hover:text-zinc-100'
  }`

export function Faq() {
  const location = useLocation()
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<FaqCategory | 'all'>('all')

  // A deep link like /faq#grades opens that answer.
  const anchored = location.hash.replace('#', '')
  const openIds = useMemo(() => (anchored ? [anchored] : []), [anchored])

  const entries = useMemo(() => {
    const q = query.trim().toLowerCase()
    return FAQ.filter(e => {
      if (category !== 'all' && e.category !== category) return false
      if (!q) return true
      return (e.q + ' ' + e.a.join(' ')).toLowerCase().includes(q)
    })
  }, [query, category])

  return (
    <div className="mx-auto w-full max-w-app px-4 py-6">
      <h1 className="font-display text-2xl font-black text-zinc-100">Frequently asked questions</h1>
      <p className="mt-1 max-w-2xl text-sm leading-relaxed text-zinc-400">
        What the model does, what the numbers mean, and what StatEdge cannot do yet.
        Where a feature is missing, the answer says so.
      </p>

      <div className="mt-5 max-w-md">
        <label htmlFor="faq-search" className="sr-only">Search the FAQ</label>
        <input
          id="faq-search"
          type="search"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search questions and answers"
          className="h-10 w-full rounded-lg border border-terminal-border bg-terminal-muted px-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-brand focus:bg-terminal-surface"
        />
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" onClick={() => setCategory('all')}
          aria-pressed={category === 'all'} className={pill(category === 'all')}>
          All
        </button>
        {FAQ_CATEGORIES.map(c => (
          <button key={c} type="button" onClick={() => setCategory(c)}
            aria-pressed={category === c} className={pill(category === c)}>
            {c}
          </button>
        ))}
      </div>

      <p aria-live="polite" className="mt-4 text-sm text-zinc-500">
        {entries.length} {entries.length === 1 ? 'question' : 'questions'}
        {query.trim() ? ` matching “${query.trim()}”` : ''}
      </p>

      {entries.length === 0 ? (
        <p className="mt-3 rounded-card border border-terminal-border bg-terminal-muted p-5 text-sm text-zinc-400">
          Nothing here matches that. Try a shorter search, or clear the category filter.
        </p>
      ) : (
        <div className="mt-3 space-y-6">
          {(category === 'all' ? FAQ_CATEGORIES : [category]).map(cat => {
            const inCat = entries.filter(e => e.category === cat)
            if (!inCat.length) return null
            return (
              <section key={cat} aria-labelledby={`faq-cat-${cat.replace(/\W+/g, '-')}`}>
                <h2
                  id={`faq-cat-${cat.replace(/\W+/g, '-')}`}
                  className="mb-2 text-xs font-bold uppercase tracking-wide text-zinc-500"
                >
                  {cat}
                </h2>
                <FaqList entries={inCat} openIds={openIds} />
              </section>
            )
          })}
        </div>
      )}
    </div>
  )
}
