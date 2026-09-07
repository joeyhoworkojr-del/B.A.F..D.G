import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { FootballLeague, NewsFeedOut } from '../types'

const REFRESH_MS = 120_000

export interface NewsState {
  feed: NewsFeedOut | null
  loading: boolean
  error: string | null
  refresh: () => void
}

/**
 * League news, refreshed on a timer.
 *
 * Freshness comes from the payload's own `fetched_at` and `ok`, never from the
 * fact that a timer ran: a refresh that fails leaves the last good feed on
 * screen with its original timestamp, so the UI reports "stale" rather than
 * quietly implying the data is current.
 */
export function useNews(league: 'all' | FootballLeague = 'all', limit = 30): NewsState {
  const [feed, setFeed] = useState<NewsFeedOut | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const nonce = useRef(0)

  const fetchNews = useCallback(() => {
    const mine = ++nonce.current
    api.news(league, limit)
      .then(next => {
        if (mine !== nonce.current) return
        setFeed(next)
        setError(null)
      })
      .catch((e: Error) => {
        if (mine !== nonce.current) return
        // Keep the last good feed; its own timestamp will age visibly.
        setError(e.message)
      })
      .finally(() => { if (mine === nonce.current) setLoading(false) })
  }, [league, limit])

  useEffect(() => {
    setLoading(true)
    setFeed(null)
    fetchNews()
    const id = setInterval(fetchNews, REFRESH_MS)
    return () => clearInterval(id)
  }, [fetchNews])

  return { feed, loading, error, refresh: fetchNews }
}
