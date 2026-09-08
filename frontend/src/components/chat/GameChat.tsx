import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import { Avatar } from '../Avatar'
import { useGameChat } from '../../hooks/useGameChat'
import { useSession } from '../../session/SessionProvider'
import type { ChatMessage } from '../../types'

const MAX_LENGTH = 500

function timeOf(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime())
    ? ''
    : d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

/**
 * One message.
 *
 * Text goes into a text node — never `dangerouslySetInnerHTML` — and URLs are
 * left as plain text rather than turned into links. The reliable way to stop a
 * malicious link is not to build a clickable thing out of someone else's input;
 * a reader who wants to visit one can copy it, having read it first.
 */
function Line({
  message, reactions, onReact, onReply, onDelete, onReport,
}: {
  message: ChatMessage
  reactions: string[]
  onReact: (id: string, emoji: string) => void
  onReply: (m: ChatMessage) => void
  onDelete: (id: string) => void
  onReport: (id: string) => void
}) {
  const [open, setOpen] = useState(false)

  if (message.deleted || message.hidden) {
    return (
      <li className="px-1 py-1 text-xs italic text-zinc-500">
        {message.hidden
          ? 'Message hidden pending review.'
          : 'Message deleted.'}
      </li>
    )
  }

  if (message.system) {
    return (
      <li className="rounded-lg border border-brand/30 bg-brand-soft px-3 py-2">
        <p className="text-xs font-bold uppercase tracking-wide text-brand">Stat Edge</p>
        <p className="mt-0.5 text-sm leading-snug text-zinc-300">{message.text}</p>
      </li>
    )
  }

  return (
    <li
      className="group flex gap-2 px-1 py-1.5"
      onMouseLeave={() => setOpen(false)}
    >
      <Link to={`/@${message.username}`} className="shrink-0 pt-0.5">
        <Avatar user={message} size={28} />
      </Link>
      <div className="min-w-0 flex-1">
        <p className="flex flex-wrap items-baseline gap-x-2">
          <Link
            to={`/@${message.username}`}
            className="text-sm font-bold text-zinc-100 hover:text-brand hover:underline"
          >
            {message.display_name}
          </Link>
          <span className="font-mono text-xs text-zinc-500">{timeOf(message.created_at)}</span>
        </p>

        {message.reply_preview && (
          <p className="mt-0.5 border-l-2 border-terminal-border pl-2 text-xs text-zinc-500">
            {message.reply_preview}
          </p>
        )}

        {/* Whitespace preserved so a deliberate line break survives; still a
            text node, so nothing here can become markup. */}
        <p className="whitespace-pre-wrap break-words text-sm leading-snug text-zinc-300">
          {message.text}
        </p>

        <div className="mt-1 flex flex-wrap items-center gap-1">
          {Object.entries(message.reactions).map(([emoji, count]) => (
            <button
              key={emoji}
              type="button"
              onClick={() => onReact(message.id, emoji)}
              className="tap rounded-full border border-terminal-border bg-terminal-surface px-1.5 text-xs text-zinc-400 hover:border-brand"
            >
              {emoji} {count}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setOpen(v => !v)}
            aria-label="Message actions"
            className="tap rounded px-1 text-xs text-zinc-600 opacity-0 transition group-hover:opacity-100 focus:opacity-100"
          >
            ···
          </button>
        </div>

        {open && (
          <div className="mt-1 flex flex-wrap items-center gap-1 rounded-lg border border-terminal-border bg-terminal-surface p-1">
            {reactions.map(emoji => (
              <button
                key={emoji}
                type="button"
                onClick={() => { onReact(message.id, emoji); setOpen(false) }}
                className="tap rounded px-1.5 text-sm hover:bg-terminal-muted"
              >
                {emoji}
              </button>
            ))}
            <button
              type="button"
              onClick={() => { onReply(message); setOpen(false) }}
              className="tap rounded px-2 text-xs font-semibold text-zinc-400 hover:text-zinc-100"
            >
              Reply
            </button>
            {message.mine ? (
              <button
                type="button"
                onClick={() => { onDelete(message.id); setOpen(false) }}
                className="tap rounded px-2 text-xs font-semibold text-signal-red hover:underline"
              >
                Delete
              </button>
            ) : (
              <button
                type="button"
                onClick={() => { onReport(message.id); setOpen(false) }}
                className="tap rounded px-2 text-xs font-semibold text-zinc-500 hover:text-signal-red"
              >
                Report
              </button>
            )}
          </div>
        )}
      </div>
    </li>
  )
}

/**
 * The room for one game.
 *
 * Readable signed out — chat is part of the game page, and hiding it from the
 * people most likely to join would be backwards. Posting needs an account, and
 * whether this particular account may post is the server's answer, echoed here.
 */
export function GameChat({
  league, eventId, live = false,
}: { league: string; eventId: string; live?: boolean }) {
  const { user } = useSession()
  const { page, messages, error, transport, refresh, absorb } =
    useGameChat(league, eventId, true)
  const [text, setText] = useState('')
  const [replyTo, setReplyTo] = useState<ChatMessage | null>(null)
  const [sending, setSending] = useState(false)
  const [notice, setNotice] = useState('')
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (messages.length === 0) return
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [messages.length])

  const send = async (e: React.FormEvent) => {
    e.preventDefault()
    const body = text.trim()
    if (!body || sending) return
    setSending(true)
    setNotice('')
    try {
      const { message } = await api.postChat(league, eventId, body, replyTo?.id)
      absorb([message])
      setText('')
      setReplyTo(null)
    } catch (err) {
      // A mute or a rate limit comes back with its reason; show it verbatim
      // rather than a generic failure, so the person knows what happened.
      setNotice(err instanceof Error ? err.message : 'That message could not be sent.')
    } finally {
      setSending(false)
    }
  }

  const react = async (id: string, emoji: string) => {
    try {
      absorb([(await api.reactChat(league, eventId, id, emoji)).message])
    } catch { /* a failed reaction is not worth interrupting anyone for */ }
  }

  const remove = async (id: string) => {
    try {
      absorb([(await api.deleteChat(league, eventId, id)).message])
    } catch (err) {
      setNotice(err instanceof Error ? err.message : 'That could not be deleted.')
    }
  }

  const report = async (id: string) => {
    try {
      const result = await api.reportChat(league, eventId, id)
      setNotice(result.note)
      refresh()
    } catch (err) {
      setNotice(err instanceof Error ? err.message : 'That could not be reported.')
    }
  }

  const reactions = page?.reactions_available ?? []

  return (
    <section
      aria-labelledby="game-chat"
      className="flex flex-col rounded-card border border-terminal-border bg-terminal-surface"
    >
      <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-terminal-border px-4 py-3">
        <h2 id="game-chat" className="text-sm font-bold text-zinc-100">
          {live ? 'Live chat' : 'Game chat'}
        </h2>
        <span className="text-xs text-zinc-500">
          {messages.length > 0 ? `${page?.count ?? messages.length} messages` : 'Be first'}
          {transport === 'poll' && ' · refreshing'}
        </span>
      </header>

      <div className="max-h-96 min-h-0 flex-1 overflow-y-auto px-3 py-2">
        {error && <p role="alert" className="p-2 text-sm text-signal-red">{error}</p>}
        {!error && messages.length === 0 && (
          <p className="p-2 text-sm text-zinc-500">
            No messages yet. Say something about the game — Stat Edge will chime in when
            the projection moves.
          </p>
        )}
        <ul>
          {messages.map(m => (
            <Line
              key={m.id}
              message={m}
              reactions={reactions}
              onReact={react}
              onReply={setReplyTo}
              onDelete={remove}
              onReport={report}
            />
          ))}
        </ul>
        <div ref={endRef} />
      </div>

      {replyTo && (
        <div className="flex items-center gap-2 border-t border-terminal-border px-3 py-1.5 text-xs">
          <span className="min-w-0 flex-1 truncate text-zinc-500">
            Replying to {replyTo.display_name}: {replyTo.text.slice(0, 60)}
          </span>
          <button
            type="button"
            onClick={() => setReplyTo(null)}
            className="tap shrink-0 font-semibold text-zinc-400 hover:text-zinc-100"
          >
            Cancel
          </button>
        </div>
      )}

      {notice && (
        <p role="status" className="border-t border-terminal-border px-3 py-2 text-xs text-signal-amber">
          {notice}
        </p>
      )}

      {!user ? (
        <p className="border-t border-terminal-border px-4 py-3 text-sm text-zinc-400">
          <Link to="/login" className="font-semibold text-brand hover:underline">Log in</Link>
          {' '}to join the conversation.
        </p>
      ) : page && !page.may_post ? (
        <p className="border-t border-terminal-border px-4 py-3 text-sm text-signal-amber">
          {page.blocked_reason}
        </p>
      ) : (
        <form onSubmit={send} className="flex gap-2 border-t border-terminal-border p-3">
          <label htmlFor="chat-input" className="sr-only">Message</label>
          <input
            id="chat-input"
            value={text}
            onChange={e => setText(e.target.value)}
            maxLength={MAX_LENGTH}
            placeholder="Say something…"
            className="min-w-0 flex-1 rounded-lg border border-terminal-border bg-terminal-bg px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600"
          />
          <button
            type="submit"
            disabled={sending || !text.trim()}
            className="tap shrink-0 rounded-lg bg-brand px-4 text-sm font-semibold text-white hover:bg-brand-strong disabled:opacity-50"
          >
            Send
          </button>
        </form>
      )}
    </section>
  )
}
