import { Link } from 'react-router-dom'
import { useSession } from '../../session/SessionProvider'
import { can } from '../../session/powers'

/**
 * Leaderboard, News, Parlay and FAQ don't fit in the five-slot bottom bar, so below
 * `lg` they get an explicit row rather than being unreachable.
 */
export function MobileMoreLinks() {
  const { user, entitlements } = useSession()
  const canStaff = can(entitlements, 'view_staff')
  // Props and the week ahead are not listed here any more: both are on the
  // homepage — player projections under the featured game, the week in the day
  // chips — so a link to each was a second route to the same content.
  const links = [
    // Settings — and with it Log out — must be reachable on a phone without
    // hunting. The top-bar avatar menu is desktop-only.
    ...(user ? [{ to: '/account', label: 'Settings' }] : []),
    { to: '/leaderboard', label: 'Leaderboard' },
    { to: '/news', label: 'News' },
    { to: '/parlay', label: 'Parlay' },
    { to: '/faq', label: 'FAQ' },
    // The top bar only shows Staff from `lg` up, which left an admin on a
    // phone or a narrow window with no way to reach the portal at all.
    ...(canStaff ? [{ to: '/staff', label: 'Staff' }] : []),
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
