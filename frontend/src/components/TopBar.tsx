import { NavLink, Link } from 'react-router-dom'

/** Primary destinations. Shown inline on desktop, in the bottom bar on mobile. */
export const NAV_ITEMS = [
  { to: '/', label: 'Games', end: true },
  { to: '/best-bets', label: 'Edges', end: false },
  { to: '/parlay', label: 'Parlay', end: false },
  { to: '/track', label: 'Track record', end: false },
]

export function TopBar() {
  return (
    <header className="sticky top-0 z-40 border-b border-terminal-border/70 bg-terminal-bg/95 backdrop-blur">
      <div className="mx-auto flex w-full max-w-[1200px] items-center gap-6 px-4 py-3">
        <Link to="/" className="font-display text-2xl font-black leading-none tracking-tight">
          <span className="text-zinc-100">Stat</span>
          <span className="text-signal-green"> Edge</span>
        </Link>

        {/* Desktop navigation — the mobile bar is hidden at this width. */}
        <nav aria-label="Primary" className="hidden md:block">
          <ul className="flex items-center gap-1">
            {NAV_ITEMS.map(item => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `rounded-lg px-3 py-2 text-sm font-semibold transition ${
                      isActive
                        ? 'bg-terminal-muted text-signal-green'
                        : 'text-zinc-300 hover:bg-terminal-muted/60 hover:text-zinc-100'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div className="ml-auto flex items-center gap-1">
          <NavLink
            to="/about"
            className={({ isActive }) =>
              `hidden rounded-lg px-3 py-2 text-sm font-semibold transition md:block ${
                isActive ? 'bg-terminal-muted text-signal-green' : 'text-zinc-300 hover:text-zinc-100'
              }`
            }
          >
            About
          </NavLink>
          <NavLink
            to="/account"
            aria-label="Account"
            className={({ isActive }) =>
              `grid h-9 w-9 place-items-center rounded-full border transition ${
                isActive ? 'border-signal-green text-signal-green' : 'border-terminal-border text-zinc-300 hover:text-zinc-100'
              }`
            }
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </NavLink>
        </div>
      </div>
    </header>
  )
}
