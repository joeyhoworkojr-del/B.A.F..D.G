import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Home' },
  { to: '/today', label: 'Markets', live: true },
  { to: '/nfl', label: 'NFL' },
  { to: '/cfl', label: 'CFL' },
  { to: '/mlb', label: 'MLB' },
  { to: '/soccer', label: 'Soccer' },
  { to: '/best-bets', label: 'Best Bets' },
  { to: '/rankings', label: 'Rankings' },
  { to: '/track', label: 'Track Record' },
]

export function NavBar() {
  return (
    <nav className="sticky top-0 z-50 border-b border-terminal-border bg-white/95">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-5 gap-y-1 px-4 py-3">
        {/* Brand: STAT EDGE — better data, sharper edge */}
        <NavLink to="/" className="flex items-center gap-1.5 mr-4">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-signal-amber text-white text-sm font-bold">⚡</span>
          <span className="font-display text-lg font-bold tracking-tight text-zinc-100">STAT</span>
          <span className="font-display text-lg font-bold tracking-tight text-signal-amber">EDGE</span>
        </NavLink>

        {links.map(l => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.to === '/'}
            className={({ isActive }) =>
              `text-sm font-display font-medium whitespace-nowrap ${
                isActive
                  ? 'text-signal-amber border-b-2 border-signal-amber pb-0.5'
                  : 'text-zinc-400 hover:text-zinc-100'
              }`
            }
          >
            {l.label}
            {l.live && (
              <span className="ml-1 inline-block h-1.5 w-1.5 rounded-full bg-signal-green animate-pulse align-middle" />
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
