import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Home' },
  { to: '/today', label: 'Today', live: true },
  { to: '/soccer', label: '⚽ Soccer' },
  { to: '/nfl', label: '🏈 NFL' },
  { to: '/cfl', label: '🍁 CFL' },
  { to: '/mlb', label: '⚾ MLB' },
  { to: '/best-bets', label: 'Best Bets' },
  { to: '/rankings', label: 'Rankings' },
]

export function NavBar() {
  return (
    <nav className="sticky top-0 z-50 border-b border-terminal-border bg-terminal-bg/95 backdrop-blur">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-5 gap-y-1 px-4 py-3">
        {/* Logo */}
        <NavLink to="/" className="flex items-center gap-1 mr-3">
          <span className="text-signal-amber font-mono text-lg font-bold tracking-tighter">STAT</span>
          <span className="text-zinc-300 font-display text-lg font-semibold">EDGE</span>
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
