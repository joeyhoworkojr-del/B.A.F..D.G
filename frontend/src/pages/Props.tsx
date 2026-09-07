import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { PropsOut } from '../types'

/**
 * Player props.
 *
 * There is no props data source. Rather than mock lines or leave a blank tab,
 * this page reports exactly what is missing and what closing the gap requires —
 * the same answer the server gives at GET /api/v1/props.
 */
export function Props() {
  const [status, setStatus] = useState<PropsOut | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    api.propsStatus()
      .then(s => { if (alive) setStatus(s) })
      .catch((e: Error) => { if (alive) setError(e.message) })
    return () => { alive = false }
  }, [])

  return (
    <div className="mx-auto w-full max-w-app px-4 py-6">
      <h1 className="font-display text-2xl font-black text-zinc-100">Player props</h1>
      <p className="mt-1 text-sm text-zinc-400">
        Passing, rushing and receiving markets for individual players.
      </p>

      {error && (
        <p role="alert" className="mt-5 text-sm text-signal-red">
          Couldn’t reach the props endpoint: {error}
        </p>
      )}

      {status && !status.available && (
        <section
          aria-labelledby="props-unavailable"
          className="mt-5 rounded-card border border-signal-amber/40 bg-signal-amber-dim p-5"
        >
          <h2 id="props-unavailable" className="text-base font-bold text-zinc-100">
            Player props aren’t available yet
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-zinc-400">{status.reason}</p>

          <h3 className="mt-4 text-sm font-bold text-zinc-100">What it would take</h3>
          <ul className="mt-2 space-y-2">
            {status.requires.map(req => (
              <li key={req} className="flex gap-2 text-sm leading-relaxed text-zinc-400">
                <span aria-hidden="true" className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-signal-amber" />
                <span>{req}</span>
              </li>
            ))}
          </ul>

          <p className="mt-4 text-sm text-zinc-500">
            We’d rather show nothing than show numbers we can’t source. Nothing on this page
            is estimated, simulated or filled in.
          </p>
        </section>
      )}

      <div className="mt-5 rounded-card border border-terminal-border bg-terminal-surface p-5">
        <h2 className="text-base font-bold text-zinc-100">What you can use today</h2>
        <p className="mt-2 text-sm leading-relaxed text-zinc-400">
          The model projects team scores, game totals, spreads and win probability from
          real posted lines. Those are live now.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Link to="/" className="tap inline-flex items-center rounded-lg bg-brand px-4 text-sm font-semibold text-white hover:bg-brand-strong">
            Browse games
          </Link>
          <Link to="/best-bets" className="tap inline-flex items-center rounded-lg border border-terminal-border px-4 text-sm font-semibold text-zinc-300 hover:bg-terminal-muted">
            See current edges
          </Link>
        </div>
      </div>
    </div>
  )
}
