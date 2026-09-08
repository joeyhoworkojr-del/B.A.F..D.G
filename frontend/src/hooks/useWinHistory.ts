import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { WinHistoryOut } from '../types'

const POLL_MS = 15_000

/**
 * The server-recorded win-probability timeline for a game.
 *
 * The server keeps this now, so the chart shows the whole game rather than
 * only the readings observed since the tab was opened. A failed refresh keeps
 * the last good series on screen instead of blanking the chart.
 */
export function useWinHistory(league?: string, eventId?: string, live = false) {
  const [history, setHistory] = useState<WinHistoryOut | null>(null)
  const [loading, setLoading] = useState(true)
  const nonce = useRef(0)

  useEffect(() => {
    if (!league || !eventId) return
    let alive = true
    const load = () => {
      const mine = ++nonce.current
      api.winHistory(league, eventId)
        .then(h => { if (alive && mine === nonce.current) { setHistory(h); setLoading(false) } })
        .catch(() => { if (alive) setLoading(false) })
    }
    load()
    if (!live) return () => { alive = false }
    const id = setInterval(load, POLL_MS)
    return () => { alive = false; clearInterval(id) }
  }, [league, eventId, live])

  return { history, loading }
}
