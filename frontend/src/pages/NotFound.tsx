import { Link, useLocation } from 'react-router-dom'

/**
 * Catch-all for unknown URLs.
 *
 * The SPA fallback serves index.html for every path, so without this route an
 * unknown URL rendered the header and footer around an empty page — which
 * reads as a broken site rather than a wrong address.
 */
export function NotFound() {
  const { pathname } = useLocation()

  const suggestions = [
    { to: '/', label: 'Games', hint: 'Today’s NFL and college football slate' },
    { to: '/live', label: 'Live', hint: 'Games in progress right now' },
    { to: '/best-bets', label: 'Edges', hint: 'Where the model disagrees with the market' },
    { to: '/results', label: 'Results', hint: 'The model’s graded record' },
    { to: '/faq', label: 'FAQ', hint: 'How the numbers are built' },
  ]

  return (
    <div className="mx-auto w-full max-w-app px-4 py-16">
      <p className="font-mono text-sm font-bold text-brand">404</p>
      <h1 className="mt-2 font-display text-2xl font-black text-zinc-100">
        That page doesn’t exist
      </h1>
      <p className="mt-2 max-w-xl text-sm leading-relaxed text-zinc-400">
        Nothing is served at <span className="font-mono text-zinc-300">{pathname}</span>.
        If you followed a link to a game, it may have been for a past week — game pages
        are keyed to a specific event.
      </p>

      <ul className="mt-6 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {suggestions.map(s => (
          <li key={s.to}>
            <Link
              to={s.to}
              className="block rounded-card border border-terminal-border bg-terminal-surface p-4 card-lift"
            >
              <span className="text-sm font-bold text-zinc-100">{s.label}</span>
              <span className="mt-0.5 block text-xs text-zinc-500">{s.hint}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
