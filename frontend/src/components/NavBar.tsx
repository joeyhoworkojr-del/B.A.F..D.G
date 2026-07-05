import { useState } from 'react'
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

function Links({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <>
      {links.map(l => (
        <NavLink
          key={l.to}
          to={l.to}
          end={l.to === '/'}
          onClick={onNavigate}
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
    </>
  )
}

export function NavBar() {
  const [open, setOpen] = useState(false)

  return (
    <nav className="sticky top-0 z-50 border-b border-terminal-border bg-white/95 shadow-[0_1px_3px_rgba(15,23,42,0.05)] backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-x-5 px-4 py-3">
        {/* Brand: STAT EDGE — better data, sharper edge */}
        <NavLink to="/" onClick={() => setOpen(false)} className="flex items-center gap-1.5 mr-auto md:mr-4">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-signal-amber text-white text-sm font-bold">⚡</span>
          <span className="font-display text-lg font-bold tracking-tight text-zinc-100">STAT</span>
          <span className="font-display text-lg font-bold tracking-tight text-signal-amber">EDGE</span>
        </NavLink>

        {/* Desktop links */}
        <div className="hidden md:flex flex-wrap items-center gap-x-5 gap-y-1">
          <Links />
        </div>

        {/* Mobile hamburger */}
        <button
          type="button"
          aria-label="Toggle navigation menu"
          aria-expanded={open}
          onClick={() => setOpen(o => !o)}
          className="md:hidden grid h-9 w-9 place-items-center rounded-lg border border-terminal-border text-zinc-100"
        >
          <span className="text-lg leading-none">{open ? '✕' : '☰'}</span>
        </button>
      </div>

      {/* Mobile dropdown */}
      {open && (
        <div className="md:hidden border-t border-terminal-border bg-white/95">
          <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4">
            <Links onNavigate={() => setOpen(false)} />
          </div>
        </div>
      )}
    </nav>
  )
}
