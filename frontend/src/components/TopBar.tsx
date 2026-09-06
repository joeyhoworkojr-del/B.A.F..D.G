import { Link } from 'react-router-dom'

export function TopBar() {
  return (
    <header className="sticky top-0 z-40 flex items-center justify-between border-b border-terminal-border/60 bg-terminal-bg/90 px-4 py-3 backdrop-blur">
      <Link to="/" className="font-display text-2xl font-black tracking-tight leading-none">
        <span className="text-zinc-100">Stat</span>
        <span className="text-signal-green"> Edge</span>
      </Link>
      <Link
        to="/about"
        aria-label="Account"
        className="grid h-9 w-9 place-items-center rounded-full border border-terminal-border text-zinc-300 hover:text-zinc-100"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
      </Link>
    </header>
  )
}
