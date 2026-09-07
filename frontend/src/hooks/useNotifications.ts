import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { BestBetsResponse } from '../types'

const POLL_MS = 120_000

export interface Notice {
  id: string
  title: string
  body: string
  href: string
  at: string
  tone: 'edge' | 'info'
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
 *
 * Nothing is stored, anywhere. Read-state lives in memory for the current tab
 * only: StatEdge writes nothing to your browser and keeps nothing about you on
 * the server, so there is no record of what you looked at to keep or to leak.
 */
export function useNotifications() {
  const [notices, setNotices] = useState<Notice[]>([])
  // In-memory only — deliberately resets with the tab.
  const [read, setRead] = useState<Set<string>>(() => new Set())
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
      return next
    })
  }, [notices])

  const unread = notices.filter(n => !read.has(n.id))
  return { notices, unreadCount: unread.length, markAllRead, error, refresh }
}
