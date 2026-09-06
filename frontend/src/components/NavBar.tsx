import { useState } from 'react'
import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Scores', live: true },
  { to: '/best-bets', label: 'Best Bets' },
  { to: '/parlay', label: 'Parlay' },
  { to: '/track', label: 'Model P/L' },
  { to: '/about', label: 'About' },
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
            `text-sm font-display font-semibold whitespace-nowrap ${
              isActive
                ? 'text-signal-green border-b-2 border-signal-green pb-0.5'
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
    <nav className="sticky top-0 z-50 border-b border-terminal-border bg-terminal-surface/95 shadow-[0_1px_0_rgba(0,0,0,0.4)] backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-x-5 px-4 py-3">
        {/* Brand */}
        <NavLink to="/" onClick={() => setOpen(false)} className="flex items-center gap-1.5 mr-auto md:mr-6">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-signal-green text-terminal-bg text-sm font-black">SE</span>
          <span className="font-display text-lg font-black tracking-tight text-zinc-100">Stat</span>
          <span className="font-display text-lg font-black tracking-tight text-signal-green">Edge</span>
          <span className="ml-1 rounded bg-terminal-muted px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-widest text-zinc-400">Gridiron</span>
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
        <div className="md:hidden border-t border-terminal-border bg-terminal-surface/98">
          <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4">
            <Links onNavigate={() => setOpen(false)} />
          </div>
        </div>
      )}
    </nav>
  )
}
