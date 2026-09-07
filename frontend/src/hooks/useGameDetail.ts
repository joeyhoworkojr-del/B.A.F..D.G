import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { GameDetailOut, PlayByPlayOut } from '../types'

/**
 * Poll cadence.
 *
 * Play-by-play and the model are separated on purpose. Plays land every few
 * seconds; win probability, market lines and edges do not move nearly that
 * fast, and refetching the whole game model at play speed would be pure load
 * for no visible gain.
 */
export const POLL_PBP_LIVE_MS = 3_000
export const POLL_LIVE_MS = 12_000
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

  const refreshPbp = useCallback(() => {
    if (!eventId) return
    // A failed poll keeps the last good feed on screen; its own timestamp ages.
    api.playByPlay(league, eventId).then(setPbp).catch(() => { /* pbp is optional */ })
  }, [league, eventId])

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

    refreshPbp()
  }, [league, eventId, refreshPbp])

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

  // Plays get their own fast loop while the game is live. It pauses when the
  // tab is hidden — nobody is reading it, and a backgrounded tab polling every
  // three seconds is load with no viewer — and fires immediately on return so
  // coming back to the tab shows the current drive, not a stale one.
  useEffect(() => {
    if (!live) return
    let id: ReturnType<typeof setInterval> | undefined

    const start = () => {
      if (id !== undefined) return
      id = setInterval(refreshPbp, POLL_PBP_LIVE_MS)
    }
    const stop = () => {
      if (id === undefined) return
      clearInterval(id)
      id = undefined
    }
    const onVisibility = () => {
      if (document.visibilityState === 'visible') { refreshPbp(); start() } else stop()
    }

    onVisibility()
    document.addEventListener('visibilitychange', onVisibility)
    return () => {
      stop()
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [live, refreshPbp])

  return { data, pbp, loading, refreshing, error, refresh }
}
