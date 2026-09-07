import { NavLink } from 'react-router-dom'

type IconProps = { className?: string }

const Football = (_: IconProps) => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M3 21c4-.5 14-2.5 18-18C8 3.5 3.5 8 3 21Z" /><path d="M8.5 15.5 15.5 8.5M10 12l2 2M12 10l2 2" />
  </svg>
)
const Bars = (_: IconProps) => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <line x1="6" y1="20" x2="6" y2="12" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="18" y1="20" x2="18" y2="9" />
  </svg>
)
const Ticket = (_: IconProps) => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M3 9V7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2a2 2 0 0 0 0 6v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2a2 2 0 0 0 0-6Z" /><path d="M13 5v14" />
  </svg>
)
const Trend = (_: IconProps) => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <polyline points="3 17 9 11 13 15 21 7" /><polyline points="15 7 21 7 21 13" />
  </svg>
)

const items = [
  { to: '/', label: 'Games', Icon: Football, end: true },
  { to: '/best-bets', label: 'Edges', Icon: Bars, end: false },
  { to: '/parlay', label: 'Parlay', Icon: Ticket, end: false },
  { to: '/track', label: 'Track', Icon: Trend, end: false },
]

/**
 * Mobile-only primary navigation. Hidden from `md` up, where the top bar takes
 * over — the page reserves matching bottom padding so it never covers content.
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
                `flex flex-col items-center gap-1 py-2.5 text-xs font-semibold ${
                  isActive ? 'text-signal-green' : 'text-zinc-400'
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
