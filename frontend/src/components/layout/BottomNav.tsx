import { NavLink } from 'react-router-dom'
import { useSession } from '../../session/SessionProvider'

const Football = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M3 21c4-.5 14-2.5 18-18C8 3.5 3.5 8 3 21Z" /><path d="M8.5 15.5 15.5 8.5M10 12l2 2M12 10l2 2" />
  </svg>
)
const Live = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <circle cx="12" cy="12" r="3" /><path d="M6.3 6.3a8 8 0 0 0 0 11.4M17.7 17.7a8 8 0 0 0 0-11.4" />
  </svg>
)
const Person = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
  </svg>
)
const Bars = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <line x1="6" y1="20" x2="6" y2="12" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="18" y1="20" x2="18" y2="9" />
  </svg>
)
const Whistle = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M4 7h11a5 5 0 1 1 0 10H9l-5 4V7Z" /><circle cx="15" cy="12" r="2" />
  </svg>
)

const baseItems = [
  { to: '/', label: 'Games', Icon: Football, end: true },
  { to: '/live', label: 'Live', Icon: Live, end: false },
  { to: '/props', label: 'Props', Icon: Whistle, end: false },
  { to: '/best-bets', label: 'Edges', Icon: Bars, end: false },
]

/**
 * Primary navigation below `lg`. The full header nav needs more room than a
 * 768px tablet has — squeezing it in there pushed the page 8px wide — so the
 * bottom bar covers everything up to that width and the top bar takes over
 * above it. The page reserves matching bottom padding so it never covers
 * content. News, Results, Parlay and FAQ sit in the row under the header.
 */
export function BottomNav() {
  const { user } = useSession()
  // The fifth slot is the user's own record once they have one, and the way in
  // before that — the most useful destination in both states.
  const items = [
    ...baseItems,
    user
      ? { to: '/my-edge', label: 'My Edge', Icon: Person, end: false }
      : { to: '/register', label: 'Join', Icon: Person, end: false },
  ]

  return (
    <nav
      aria-label="Primary"
      data-nav="bottom"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-terminal-border bg-terminal-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden"
    >
      <ul className="mx-auto flex max-w-3xl items-stretch">
        {items.map(({ to, label, Icon, end }) => (
          <li key={to} className="flex-1">
            <NavLink
              to={to}
              end={end}
              className={({ isActive }) =>
                `tap flex flex-col items-center justify-center gap-0.5 py-2 text-xs font-semibold ${
                  isActive ? 'text-brand' : 'text-zinc-400'
                }`
              }
            >
              <Icon />
              {label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
