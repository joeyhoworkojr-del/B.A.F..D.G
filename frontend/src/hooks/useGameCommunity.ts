import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { GameCommunityOut } from '../types'

/**
 * Community picks for one game.
 *
 * Refetched on demand after the viewer publishes, so their own pick appears
 * immediately without waiting for a poll.
 */
export function useGameCommunity(league: string, eventId?: string) {
  const [data, setData] = useState<GameCommunityOut | null>(null)

  const refresh = useCallback(() => {
    if (!eventId) return
    api.gameCommunity(league, eventId)
      .then(setData)
      .catch(() => { /* community is additive; its absence must not break the page */ })
  }, [league, eventId])

  useEffect(() => { refresh() }, [refresh])

  return { community: data, refreshCommunity: refresh }
}
