import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { BestBetsResponse } from '../types'

const STORAGE_KEY = 'statedge.notifications.read'
const POLL_MS = 120_000

export interface Notice {
  id: string
  title: string
  body: string
  href: string
  at: string
  tone: 'edge' | 'info'
}

/** Read-state is a per-device convenience, never an identity or an entitlement. */
function loadRead(): Set<string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return new Set<string>(raw ? JSON.parse(raw) : [])
  } catch {
    return new Set()
  }
}

function saveRead(ids: Set<string>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...ids].slice(-200)))
  } catch { /* private mode — read state simply doesn't persist */ }
}

function noticesFrom(bets: BestBetsResponse): Notice[] {
  return bets.bets
    .filter(b => b.rating === 'A' || b.rating === 'B')
    .slice(0, 12)
    .map(b => ({
      id: `${b.fixture_id}:${b.market}:${b.selection}:${b.rating}`,
      title: `${b.rating}-grade edge · ${b.selection}`,
      body: `${b.away} at ${b.home} — model ${(b.model_prob * 100).toFixed(0)}% vs market ${
        b.market_prob == null ? '—' : `${(b.market_prob * 100).toFixed(0)}%`
      }.`,
      href: `/game/${b.league}/${b.event_id}`,
      at: b.kickoff,
      tone: 'edge' as const,
    }))
}

/**
 * In-app notification centre.
 *
 * Every notice is derived from something the model actually produced — a graded
 * edge currently on the board — rather than being invented to fill the panel.
 * Nothing is pushed to a device: there is no per-user storage to subscribe
 * against, so this is a view of the current slate, with read-state kept locally.
 */
export function useNotifications() {
  const [notices, setNotices] = useState<Notice[]>([])
  const [read, setRead] = useState<Set<string>>(loadRead)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(() => {
    api.bestBets()
      .then(b => { setNotices(noticesFrom(b)); setError(null) })
      .catch((e: Error) => setError(e.message))
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, POLL_MS)
    return () => clearInterval(id)
  }, [refresh])

  const markAllRead = useCallback(() => {
    setRead(prev => {
      const next = new Set(prev)
      notices.forEach(n => next.add(n.id))
      saveRead(next)
      return next
    })
  }, [notices])

  const unread = notices.filter(n => !read.has(n.id))
  return { notices, unreadCount: unread.length, markAllRead, error, refresh }
}
