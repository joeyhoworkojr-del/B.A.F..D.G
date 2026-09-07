import { NavLink } from 'react-router-dom'

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

const items = [
  { to: '/', label: 'Games', Icon: Football, end: true },
  { to: '/live', label: 'Live', Icon: Live, end: false },
  { to: '/props', label: 'Props', Icon: Whistle, end: false },
  { to: '/best-bets', label: 'Edges', Icon: Bars, end: false },
  { to: '/account', label: 'Account', Icon: Person, end: false },
]

/**
 * Mobile-only primary navigation. Hidden from `md` up, where the top bar takes
 * over — the page reserves matching bottom padding so it never covers content.
 * News and Results live in the header's More menu at this width.
 */
export function BottomNav() {
  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-terminal-border bg-terminal-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
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
