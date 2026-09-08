import { useEffect, useRef, useState } from 'react'
import { NavLink, Link, useNavigate, useSearchParams } from 'react-router-dom'
import { NotificationCentre } from './NotificationCentre'
import { useSession } from '../../session/SessionProvider'

/** Primary destinations, in the order they appear on desktop. */
export const NAV_ITEMS = [
  { to: '/', label: 'Games', end: true },
  { to: '/live', label: 'Live', end: false },
  { to: '/props', label: 'Props', end: false },
  { to: '/best-bets', label: 'Edges', end: false },
  { to: '/leaderboard', label: 'Leaderboard', end: false },
  { to: '/news', label: 'News', end: false },
  { to: '/results', label: 'Results', end: false },
]

/** Secondary destinations — the "More" menu on both breakpoints. */
export const MORE_ITEMS = [
  // Kept out of the primary bar deliberately: an eighth item wraps the header
  // at 1440px, and the week-ahead board is a destination people seek out
  // rather than one they need in front of them at all times.
  { to: '/upcoming', label: 'Upcoming' },
  { to: '/parlay', label: 'Parlay' },
  { to: '/faq', label: 'FAQ' },
  { to: '/about', label: 'About & methodology' },
]

const linkCls = ({ isActive }: { isActive: boolean }) =>
  `tap inline-flex items-center whitespace-nowrap rounded-lg px-2.5 text-sm font-semibold transition ${
    isActive ? 'bg-brand-soft text-brand' : 'text-zinc-400 hover:bg-terminal-muted hover:text-zinc-100'
  }`

function SearchBox({ className = '' }: { className?: string }) {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [q, setQ] = useState(params.get('q') ?? '')

  return (
    <form
      role="search"
      className={className}
      onSubmit={e => {
        e.preventDefault()
        // Search filters the slate, so it always lands on the games board.
        navigate(q.trim() ? `/?q=${encodeURIComponent(q.trim())}` : '/')
      }}
    >
      <label htmlFor="site-search" className="sr-only">Search teams and games</label>
      <div className="relative">
        <svg
          className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-500"
          width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="2" strokeLinecap="round" aria-hidden="true"
        >
          <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" />
        </svg>
        <input
          id="site-search"
          type="search"
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder="Search teams"
          className="h-9 w-full rounded-lg border border-terminal-border bg-terminal-muted pl-8 pr-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-brand focus:bg-terminal-surface"
        />
      </div>
    </form>
  )
}

function MoreMenu() {
  const [open, setOpen] = useState(false)
  const wrap = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div ref={wrap} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen(o => !o)}
        className="tap inline-flex items-center gap-1 rounded-lg px-3 text-sm font-semibold text-zinc-400 hover:bg-terminal-muted hover:text-zinc-100"
      >
        More
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
      {open && (
        <ul
          role="menu"
          className="absolute right-0 z-50 mt-2 w-56 rounded-card border border-terminal-border bg-terminal-surface py-1 shadow-pop"
        >
          {MORE_ITEMS.map(item => (
            <li key={item.to} role="none">
              <Link
                role="menuitem"
                to={item.to}
                onClick={() => setOpen(false)}
                className="block px-4 py-2.5 text-sm font-semibold text-zinc-300 hover:bg-terminal-muted hover:text-zinc-100"
              >
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function AccountArea() {
  const { user, ready } = useSession()

  // Nothing is rendered until the session resolves, so the header never flashes
  // "Sign in" at someone who is already signed in.
  if (!ready) return <span className="h-9 w-24" aria-hidden="true" />

  if (!user) {
    return (
      <div className="flex items-center gap-1">
        <Link
          to="/login"
          className="tap hidden items-center whitespace-nowrap rounded-lg px-3 text-sm font-semibold text-zinc-400 hover:bg-terminal-muted hover:text-zinc-100 sm:inline-flex"
        >
          Log in
        </Link>
        <Link
          to="/register"
          className="tap inline-flex items-center whitespace-nowrap rounded-lg bg-brand px-3 text-sm font-semibold text-white hover:bg-brand-strong"
        >
          Create account
        </Link>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-1">
      <NavLink
        to="/my-edge"
        className={({ isActive }) =>
          `tap hidden items-center rounded-lg px-3 text-sm font-semibold transition lg:inline-flex ${
            isActive ? 'bg-brand-soft text-brand' : 'text-zinc-400 hover:bg-terminal-muted hover:text-zinc-100'
          }`
        }
      >
        My Edge
      </NavLink>
      {user.level === 'admin' && (
        <NavLink
          to="/staff"
          className={({ isActive }) =>
            `tap hidden items-center rounded-lg px-3 text-sm font-semibold transition lg:inline-flex ${
              isActive ? 'bg-brand-soft text-brand' : 'text-zinc-400 hover:bg-terminal-muted hover:text-zinc-100'
            }`
          }
        >
          Staff
        </NavLink>
      )}
      <NavLink
        to={`/@${user.username}`}
        aria-label={`Your profile, @${user.username}`}
        className="tap grid place-items-center rounded-full border border-terminal-border px-2 text-xs font-bold text-zinc-400 transition hover:text-zinc-100"
      >
        {(user.display_name || user.username).slice(0, 2).toUpperCase()}
      </NavLink>
    </div>
  )
}

export function TopBar() {
  return (
    <header className="sticky top-0 z-40 border-b border-terminal-border bg-terminal-bg/95 backdrop-blur">
      <div className="mx-auto flex w-full max-w-app items-center gap-3 px-4 py-2.5">
        <Link to="/" className="shrink-0 whitespace-nowrap font-display text-2xl font-black leading-none tracking-tight">
          <span className="text-zinc-100">Stat</span>
          <span className="text-brand"> Edge</span>
        </Link>

        {/* Desktop navigation. Below `lg` the bottom bar takes over: six links
            plus a More menu do not fit beside the logo on a 768px tablet. */}
        <nav aria-label="Primary" data-nav="top" className="hidden lg:block">
          <ul className="flex items-center gap-0.5">
            {NAV_ITEMS.map(item => (
              <li key={item.to}>
                <NavLink to={item.to} end={item.end} className={linkCls}>{item.label}</NavLink>
              </li>
            ))}
            <li><MoreMenu /></li>
          </ul>
        </nav>

        <div className="ml-auto flex items-center gap-1">
          <SearchBox className="hidden w-52 xl:block" />
          <NotificationCentre />
          <AccountArea />
        </div>
      </div>

      {/* Mobile search sits on its own row so the header stays compact. */}
      <div className="border-t border-terminal-border/60 px-4 py-2 xl:hidden">
        <SearchBox />
      </div>
    </header>
  )
}
