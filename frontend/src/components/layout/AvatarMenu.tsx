import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useSession } from '../../session/SessionProvider'
import { can } from '../../session/powers'
import { Avatar } from '../Avatar'

/**
 * The account menu behind the avatar.
 *
 * Log out lives here, one click from every page, rather than being buried in a
 * settings sub-page. Signing out of a product should never be a puzzle.
 */
export function AvatarMenu() {
  const { user, entitlements, logout } = useSession()
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const wrap = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

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

  if (!user) return null

  const signOut = async () => {
    setBusy(true)
    try {
      await logout()
      setOpen(false)
      navigate('/')
    } finally {
      setBusy(false)
    }
  }

  const items = [
    { to: `/@${user.username}`, label: 'Public profile' },
    { to: '/my-edge', label: 'My Edge' },
    { to: '/account', label: 'Account settings' },
    ...(can(entitlements, 'view_staff') ? [{ to: '/staff', label: 'Staff' }] : []),
  ]

  return (
    <div className="relative" ref={wrap}>
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label={`Account menu for @${user.username}`}
        className="tap flex items-center gap-1.5 rounded-full border border-terminal-border px-1 pr-2 transition hover:border-zinc-600"
      >
        <Avatar user={user} size={26} />
        <svg viewBox="0 0 20 20" className="h-3 w-3 text-zinc-500" aria-hidden="true">
          <path d="M5 8l5 5 5-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-50 mt-2 w-60 overflow-hidden rounded-card border border-terminal-border bg-terminal-surface py-1 shadow-pop"
        >
          <div className="flex items-center gap-2.5 border-b border-terminal-border px-4 py-3">
            <Avatar user={user} size={36} />
            <div className="min-w-0">
              <p className="truncate text-sm font-bold text-zinc-100">
                {user.display_name || user.username}
              </p>
              <p className="truncate text-xs text-zinc-500">@{user.username}</p>
            </div>
          </div>

          {items.map(item => (
            <Link
              key={item.to}
              role="menuitem"
              to={item.to}
              onClick={() => setOpen(false)}
              className="block px-4 py-2.5 text-sm font-semibold text-zinc-300 hover:bg-terminal-muted hover:text-zinc-100"
            >
              {item.label}
            </Link>
          ))}

          <div className="mt-1 border-t border-terminal-border pt-1">
            <button
              type="button"
              role="menuitem"
              onClick={signOut}
              disabled={busy}
              className="block w-full px-4 py-2.5 text-left text-sm font-semibold text-signal-red hover:bg-signal-red-dim disabled:opacity-60"
            >
              {busy ? 'Logging out…' : 'Log out'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
