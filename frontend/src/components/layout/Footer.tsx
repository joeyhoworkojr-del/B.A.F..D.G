import { Link } from 'react-router-dom'

const COLUMNS: { heading: string; links: { label: string; to: string; external?: boolean }[] }[] = [
  {
    heading: 'StatEdge',
    links: [
      { label: 'About', to: '/about' },
      { label: 'Methodology', to: '/about#methodology' },
      { label: 'Data sources', to: '/about#data-sources' },
    ],
  },
  {
    heading: 'Product',
    links: [
      { label: 'Games', to: '/' },
      { label: 'Live', to: '/live' },
      { label: 'Edges', to: '/best-bets' },
      { label: 'Results', to: '/results' },
    ],
  },
  {
    heading: 'Support',
    links: [
      { label: 'FAQ', to: '/faq' },
      { label: 'Contact', to: '/faq#contact' },
    ],
  },
  {
    heading: 'Legal',
    links: [
      { label: 'Privacy', to: '/about#privacy' },
      { label: 'Terms', to: '/about#terms' },
    ],
  },
]

export function Footer() {
  return (
    <footer className="mt-12 border-t border-terminal-border bg-terminal-muted/50">
      <div className="mx-auto w-full max-w-app px-4 py-8">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {COLUMNS.map(col => (
            <nav key={col.heading} aria-label={col.heading}>
              <h2 className="text-xs font-bold uppercase tracking-wide text-zinc-500">{col.heading}</h2>
              <ul className="mt-2 space-y-1.5">
                {col.links.map(l => (
                  <li key={l.label}>
                    <Link to={l.to} className="text-sm text-zinc-400 hover:text-brand hover:underline">
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>

        <div className="mt-8 border-t border-terminal-border pt-5 text-xs leading-relaxed text-zinc-500">
          <p>
            <span className="font-bold text-zinc-400">Stat Edge</span> publishes model
            projections for NFL and college football. Scores, schedules, lines and headlines
            come from ESPN’s public feeds; headlines link back to the publisher.
          </p>
          <p className="mt-2">
            Projections are estimates, not predictions of certainty, and nothing here is
            betting advice. Saving or following a game on StatEdge records your interest —
            it does not place a wager, and StatEdge does not accept or process wagers.
          </p>
          <p className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span>© {new Date().getFullYear()} StatEdge</span>
            {/* Discreet on purpose, but not a security measure: every staff
                route checks the caller's role server-side, so a normal user
                following this link gets a 404 rather than a portal. */}
            <Link
              to="/staff"
              className="text-zinc-600 transition hover:text-zinc-400 hover:underline"
            >
              Staff
            </Link>
          </p>
        </div>
      </div>
    </footer>
  )
}
