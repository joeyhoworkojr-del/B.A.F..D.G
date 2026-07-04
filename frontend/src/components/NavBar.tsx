import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Predict' },
  { to: '/nfl', label: 'NFL' },
  { to: '/best-bets', label: 'Best Bets' },
  { to: '/rankings', label: 'Rankings' },
  { to: '/history', label: 'History' },
  { to: '/about', label: 'About' },
]

export function NavBar() {
  return (
    <nav className="sticky top-0 z-50 border-b border-terminal-border bg-terminal-bg/95 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
        {/* Logo */}
        <div className="flex items-center gap-2 mr-4">
          <span className="text-signal-amber font-mono text-lg font-bold tracking-tighter">STAT</span>
          <span className="text-zinc-300 font-display text-lg font-semibold">EDGE</span>
          <span className="ml-2 rounded-full bg-signal-amber/20 px-2 py-0.5 text-[10px] font-mono text-signal-amber">
            2026 WC
          </span>
        </div>

        {links.map(l => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.to === '/'}
            className={({ isActive }) =>
              `text-sm font-display font-medium transition-colors ${
                isActive
                  ? 'text-signal-amber border-b-2 border-signal-amber pb-0.5'
                  : 'text-zinc-400 hover:text-zinc-100'
              }`
            }
          >
            {l.label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
