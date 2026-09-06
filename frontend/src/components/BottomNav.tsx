import { NavLink } from 'react-router-dom'

type IconProps = { className?: string }

const Football = ({ className }: IconProps) => (
  <svg className={className} width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 21c4-.5 14-2.5 18-18C8 3.5 3.5 8 3 21Z" />
    <path d="M8.5 15.5 15.5 8.5M10 12l2 2M12 10l2 2" />
  </svg>
)
const Bars = ({ className }: IconProps) => (
  <svg className={className} width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="6" y1="20" x2="6" y2="12" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="18" y1="20" x2="18" y2="9" />
  </svg>
)
const Trend = ({ className }: IconProps) => (
  <svg className={className} width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 17 9 11 13 15 21 7" /><polyline points="15 7 21 7 21 13" />
  </svg>
)
const Person = ({ className }: IconProps) => (
  <svg className={className} width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
  </svg>
)

const items = [
  { to: '/', label: 'Games', Icon: Football, end: true },
  { to: '/best-bets', label: 'Edges', Icon: Bars, end: false },
  { to: '/track', label: 'Track', Icon: Trend, end: false },
  { to: '/about', label: 'Account', Icon: Person, end: false },
]

export function BottomNav() {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-terminal-border bg-terminal-surface/95 backdrop-blur">
      <div className="mx-auto flex max-w-3xl items-stretch">
        {items.map(({ to, label, Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex flex-1 flex-col items-center gap-1 py-2.5 text-[10px] font-semibold ${
                isActive ? 'text-signal-green' : 'text-zinc-500'
              }`
            }
          >
            <Icon />
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
