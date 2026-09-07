import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useNotifications } from '../../hooks/useNotifications'

/**
 * In-app notification centre.
 *
 * Everything listed is a graded edge the model is currently publishing, so the
 * panel can never show an alert that isn't backed by a real projection. There
 * is no per-user storage, so nothing is delivered off-site; read state stays on
 * this device.
 */
export function NotificationCentre() {
  const { notices, unreadCount, markAllRead, error } = useNotifications()
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
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={unreadCount ? `Notifications, ${unreadCount} unread` : 'Notifications'}
        onClick={() => { setOpen(o => !o); if (!open) markAllRead() }}
        className="tap relative grid place-items-center rounded-lg px-2 text-zinc-400 hover:bg-terminal-muted hover:text-zinc-100"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute right-0.5 top-1 grid h-4 min-w-4 place-items-center rounded-full bg-brand px-1 text-xs font-bold leading-none text-white">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Notifications"
          className="absolute right-0 z-50 mt-2 w-[min(22rem,calc(100vw-2rem))] rounded-card border border-terminal-border bg-terminal-surface shadow-pop"
        >
          <div className="border-b border-terminal-border px-4 py-3">
            <h2 className="text-sm font-bold text-zinc-100">Notifications</h2>
            <p className="mt-0.5 text-xs text-zinc-500">
              Graded edges the model is publishing right now.
            </p>
          </div>

          <div className="max-h-80 overflow-y-auto">
            {error && (
              <p role="alert" className="px-4 py-3 text-sm text-signal-red">
                Couldn’t load notifications: {error}
              </p>
            )}
            {!error && notices.length === 0 && (
              <p className="px-4 py-6 text-sm text-zinc-400">
                No graded edges on the board right now. When the model disagrees with a
                posted line by enough to earn a grade, it shows up here.
              </p>
            )}
            <ul>
              {notices.map(n => (
                <li key={n.id} className="border-b border-terminal-border/70 last:border-0">
                  <Link
                    to={n.href}
                    onClick={() => setOpen(false)}
                    className="block px-4 py-3 hover:bg-terminal-muted"
                  >
                    <p className="text-sm font-bold text-zinc-100">{n.title}</p>
                    <p className="mt-0.5 text-xs leading-relaxed text-zinc-400">{n.body}</p>
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <p className="border-t border-terminal-border px-4 py-2.5 text-xs text-zinc-500">
            Push and email alerts need a signed-in account, which isn’t available yet.
          </p>
        </div>
      )}
    </div>
  )
}
