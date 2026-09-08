import { Link } from 'react-router-dom'
import { useSession } from '../../session/SessionProvider'

/**
 * News, Results, Parlay and FAQ don't fit in the five-slot bottom bar, so below
 * `lg` they get an explicit row rather than being unreachable.
 */
export function MobileMoreLinks() {
  const { user } = useSession()
  const links = [
    { to: '/upcoming', label: 'Upcoming' },
    { to: '/leaderboard', label: 'Leaderboard' },
    { to: '/news', label: 'News' },
    { to: '/results', label: 'Results' },
    { to: '/parlay', label: 'Parlay' },
    { to: '/faq', label: 'FAQ' },
    // The top bar only shows Staff from `lg` up, which left an admin on a
    // phone or a narrow window with no way to reach the portal at all.
    ...(user?.level === 'admin' ? [{ to: '/staff', label: 'Staff' }] : []),
  ]
  return (
    <nav
      aria-label="More sections"
      data-nav="more"
      className="border-b border-terminal-border bg-terminal-muted/50 lg:hidden"
    >
      <ul className="mx-auto flex max-w-app gap-1 overflow-x-auto px-4 py-1.5 no-scrollbar">
        {links.map(l => (
          <li key={l.to}>
            <Link
              to={l.to}
              className="tap inline-flex items-center whitespace-nowrap rounded-full border border-terminal-border bg-terminal-surface px-3 text-sm font-semibold text-zinc-400"
            >
              {l.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  )
}
