import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { ChatMessage, ChatPage } from '../types'

// How often the fallback asks for anything new. Each poll carries the cursor
// the client already has, so a quiet room returns an empty list.
const POLL_MS = 4000

// The API base, so the EventSource points at the same origin the rest of the
// client does.
const BASE = import.meta.env.VITE_API_BASE ?? ''

/**
 * One game's chat.
 *
 * Tries Server-Sent Events first and falls back to cursor polling. The
 * fallback is not belt-and-braces: statedge.ca serves the SPA from Vercel and
 * proxies /api to Fly, and a proxy that buffers a streaming response turns a
 * live chat into a dead one with no error to catch. Rather than bet the
 * feature on that behaviour, this notices when the stream produces nothing and
 * quietly switches.
 */
export function useGameChat(league?: string, eventId?: string, enabled = true) {
  const [page, setPage] = useState<ChatPage | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [error, setError] = useState('')
  const [transport, setTransport] = useState<'connecting' | 'stream' | 'poll'>('connecting')
  const cursor = useRef(0)

  /** Merge by id so a message posted optimistically is not duplicated. */
  const absorb = useCallback((incoming: ChatMessage[]) => {
    if (incoming.length === 0) return
    setMessages(prev => {
      const byId = new Map(prev.map(m => [m.id, m]))
      for (const m of incoming) byId.set(m.id, m)
      return [...byId.values()].sort((a, b) => a.seq - b.seq)
    })
    cursor.current = Math.max(cursor.current, ...incoming.map(m => m.seq))
  }, [])

  const load = useCallback(async () => {
    if (!league || !eventId) return
    try {
      const next = await api.chat(league, eventId, cursor.current)
      setPage(next)
      absorb(next.messages)
      setError('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Chat is unavailable.')
    }
  }, [league, eventId, absorb])

  // First load always goes over plain HTTP, so the room renders even if the
  // stream never connects.
  useEffect(() => {
    if (!enabled) return
    cursor.current = 0
    setMessages([])
    load()
  }, [enabled, load])

  useEffect(() => {
    if (!enabled || !league || !eventId) return
    let source: EventSource | null = null
    let poll: ReturnType<typeof setInterval> | null = null
    let cancelled = false

    const startPolling = () => {
      if (poll || cancelled) return
      setTransport('poll')
      poll = setInterval(load, POLL_MS)
    }

    try {
      source = new EventSource(
        `${BASE}/api/v1/chat/${league}/${encodeURIComponent(eventId)}/stream?after=${cursor.current}`,
        { withCredentials: true },
      )
      source.onmessage = event => {
        if (cancelled) return
        setTransport('stream')
        try {
          absorb(JSON.parse(event.data).messages ?? [])
        } catch {
          /* a malformed frame is not worth tearing the room down for */
        }
      }
      source.onerror = () => {
        source?.close()
        source = null
        startPolling()
      }
    } catch {
      startPolling()
    }

    // The stream sends a comment as soon as it connects. If nothing has arrived
    // by now, something between here and the server is buffering it.
    const giveUp = setTimeout(() => {
      if (!cancelled && source && source.readyState !== EventSource.OPEN) {
        source.close()
        source = null
        startPolling()
      }
    }, 6000)

    return () => {
      cancelled = true
      clearTimeout(giveUp)
      source?.close()
      if (poll) clearInterval(poll)
    }
  }, [enabled, league, eventId, load, absorb])

  return { page, messages, error, transport, refresh: load, absorb }
}
