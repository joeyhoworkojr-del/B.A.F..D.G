import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import type { EdgeAiStatus, EdgeAiTurn } from '../../types'

const SOURCE_LABEL: Record<string, string> = {
  get_game_context: 'game data',
  get_live_game_state: 'live game state',
  get_prediction: 'model projection',
  get_todays_games: "today's board",
  get_player_props: 'player projections',
  get_news: 'news',
  get_community_consensus: 'community picks',
  get_leaderboard: 'leaderboard',
  get_user_performance: 'your record',
  get_analyst_profile: 'analyst profile',
}

/** Openers that change with what the person is looking at. */
function suggestions(gameContext: boolean, live: boolean): string[] {
  if (live) {
    return ['What changed?', 'Why did the probability move?', 'Is the score misleading?']
  }
  if (gameContext) {
    return ['Break down this game.', 'What am I missing?', "What's the biggest mismatch?"]
  }
  return ['What should I be watching tonight?', 'Find me an edge.', 'How am I doing?']
}

/**
 * The Edge AI conversation.
 *
 * Answers name the StatEdge lookups they rest on, so a reader can see what an
 * answer is built from rather than taking it on trust. When the assistant is
 * not configured on this deployment the panel says so plainly instead of
 * offering a button that fails.
 */
export function AskEdge({
  league, eventId, live = false, compact = false,
}: { league?: string; eventId?: string; live?: boolean; compact?: boolean }) {
  const [status, setStatus] = useState<EdgeAiStatus | null>(null)
  const [turns, setTurns] = useState<(EdgeAiTurn & { sources?: string[] })[]>([])
  const [question, setQuestion] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let alive = true
    api.aiStatus()
      .then(s => { if (alive) setStatus(s) })
      .catch(() => { if (alive) setStatus(null) })
    return () => { alive = false }
  }, [])

  // Only once there is a conversation to follow, and scoped to the panel.
  // Scrolling the whole page the moment someone opens Ask Edge yanks them away
  // from whatever they were reading — and an animation running on an otherwise
  // idle page is enough to stall a full-page screenshot indefinitely.
  useEffect(() => {
    if (turns.length === 0) return
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [turns, busy])

  const send = async (text: string) => {
    const q = text.trim()
    if (!q || busy) return
    setError('')
    setQuestion('')
    const history = turns.map(({ role, content }) => ({ role, content }))
    setTurns(prev => [...prev, { role: 'user', content: q }])
    setBusy(true)
    try {
      const reply = await api.askEdge(
        q,
        league && eventId ? { league, event_id: eventId } : undefined,
        history,
      )
      setTurns(prev => [
        ...prev,
        { role: 'assistant', content: reply.answer, sources: reply.sources_used },
      ])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Edge AI could not answer that.')
      // Re-read status after a failure: the server records the provider's own
      // last error there, scrubbed of credentials. Without it the only thing
      // anyone can report is "it says unreachable", which is not diagnosable.
      api.aiStatus().then(setStatus).catch(() => {})
    } finally {
      setBusy(false)
    }
  }

  if (status && !status.may_ask) {
    return (
      <div className="rounded-card border border-terminal-border bg-terminal-surface p-4">
        <h2 className="text-sm font-bold text-zinc-100">Ask Edge</h2>
        <p className="mt-1.5 text-sm text-zinc-400">{status.reason}</p>
        {!status.signed_in && status.available && (
          <Link
            to="/login"
            className="tap mt-3 inline-flex items-center rounded-lg bg-brand px-3 text-sm font-semibold text-white hover:bg-brand-strong"
          >
            Log in
          </Link>
        )}
      </div>
    )
  }

  return (
    <section
      aria-labelledby="ask-edge"
      className="flex min-h-0 flex-col rounded-card border border-terminal-border bg-terminal-surface"
    >
      <header className="flex items-baseline justify-between gap-2 border-b border-terminal-border px-4 py-3">
        <h2 id="ask-edge" className="text-sm font-bold text-zinc-100">Ask Edge</h2>
        <span className="text-xs text-zinc-500">
          {league && eventId ? 'Knows this game' : 'Sports intelligence'}
        </span>
      </header>

      <div className={`min-h-0 flex-1 space-y-3 overflow-y-auto p-4 ${compact ? 'max-h-80' : 'max-h-[28rem]'}`}>
        {turns.length === 0 && (
          <div>
            <p className="text-sm leading-relaxed text-zinc-400">
              Edge AI answers from StatEdge's own data — the model's projections, the live
              game state, published picks and the leaderboard. If it doesn't have something,
              it says so rather than guessing.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {suggestions(!!(league && eventId), live).map(s => (
                <button
                  key={s}
                  type="button"
                  onClick={() => send(s)}
                  className="tap rounded-full border border-terminal-border px-3 text-sm font-semibold text-zinc-400 transition hover:border-brand hover:text-brand"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {turns.map((turn, i) => (
          <div key={i} className={turn.role === 'user' ? 'text-right' : ''}>
            <div
              className={`inline-block max-w-[92%] rounded-2xl px-3.5 py-2.5 text-left text-sm leading-relaxed ${
                turn.role === 'user'
                  ? 'bg-brand-soft text-zinc-100'
                  : 'border border-terminal-border bg-terminal-muted text-zinc-300'
              }`}
            >
              {turn.content.split('\n').filter(Boolean).map((line, j) => (
                <p key={j} className={j > 0 ? 'mt-2' : ''}>{line}</p>
              ))}
              {turn.sources && turn.sources.length > 0 && (
                <p className="mt-2 border-t border-terminal-border pt-1.5 text-xs text-zinc-500">
                  From {turn.sources.map(s => SOURCE_LABEL[s] ?? s).join(', ')}
                </p>
              )}
            </div>
          </div>
        ))}

        {busy && (
          <p className="text-sm text-zinc-500" role="status">Edge is looking that up…</p>
        )}
        {error && (
          <div role="alert">
            <p className="text-sm text-signal-red">{error}</p>
            {status?.last_error && (
              <p className="mt-1 font-mono text-xs leading-relaxed text-zinc-500">
                {status.last_error}
              </p>
            )}
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={e => { e.preventDefault(); send(question) }}
        className="flex gap-2 border-t border-terminal-border p-3"
      >
        <label htmlFor="ask-edge-input" className="sr-only">Ask Edge a question</label>
        <input
          id="ask-edge-input"
          value={question}
          onChange={e => setQuestion(e.target.value)}
          maxLength={1000}
          placeholder={live ? 'Why did the probability move?' : 'Ask about this game…'}
          className="min-w-0 flex-1 rounded-lg border border-terminal-border bg-terminal-bg px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600"
        />
        <button
          type="submit"
          disabled={busy || !question.trim()}
          className="tap shrink-0 rounded-lg bg-brand px-4 text-sm font-semibold text-white hover:bg-brand-strong disabled:opacity-50"
        >
          Ask
        </button>
      </form>

      <p className="border-t border-terminal-border px-4 py-2 text-xs text-zinc-500">
        Edge AI explains StatEdge's data and model. It is not betting advice.
      </p>
    </section>
  )
}
