import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { GameDetailOut, PlayByPlayOut } from '../types'

/** Poll cadence: fast while the ball is in play, relaxed otherwise. */
export const POLL_LIVE_MS = 10_000
export const POLL_IDLE_MS = 30_000

export interface GameDetailState {
  data: GameDetailOut | null
  pbp: PlayByPlayOut | null
  /** Only true before the first successful load — refreshes never blank the UI. */
  loading: boolean
  /** A refresh is in flight while last-good data stays on screen. */
  refreshing: boolean
  /** Set when the most recent refresh failed; `data` is then the last good copy. */
  error: string
  refresh: () => void
}

/**
 * Loads one game and keeps it fresh.
 *
 * Failures never clear the screen: the last good snapshot stays visible and the
 * error surfaces alongside it, so a blip in the feed can't make a live game
 * look like it vanished.
 */
export function useGameDetail(league: string, eventId?: string): GameDetailState {
  const [data, setData] = useState<GameDetailOut | null>(null)
  const [pbp, setPbp] = useState<PlayByPlayOut | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const loadedOnce = useRef(false)

  const refresh = useCallback(() => {
    if (!eventId) return
    setRefreshing(true)
    api.gameDetail(league, eventId)
      .then(d => {
        setData(d)          // fresh good data replaces last-good
        setError('')
        loadedOnce.current = true
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => { setRefreshing(false); setLoading(false) })

    api.playByPlay(league, eventId).then(setPbp).catch(() => { /* pbp is optional */ })
  }, [league, eventId])

  useEffect(() => {
    loadedOnce.current = false
    setLoading(true)
    setData(null)
    refresh()
  }, [refresh])

  // Re-poll at a cadence matched to the game state.
  const live = data?.status === 'in'
  useEffect(() => {
    const id = setInterval(refresh, live ? POLL_LIVE_MS : POLL_IDLE_MS)
    return () => clearInterval(id)
  }, [refresh, live])

  return { data, pbp, loading, refreshing, error, refresh }
}
