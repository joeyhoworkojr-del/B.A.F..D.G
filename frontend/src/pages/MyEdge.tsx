import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { api } from '../api/client'
import { PickRow, RecordSummary } from '../components/record/RecordSummary'
import { useSession } from '../session/SessionProvider'
import type { MyPicksOut } from '../types'

export function MyEdge() {
  const { user, ready } = useSession()
  const [data, setData] = useState<MyPicksOut | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) return
    let alive = true
    api.myPicks()
      .then(d => { if (alive) setData(d) })
      .catch((e: Error) => { if (alive) setError(e.message) })
    return () => { alive = false }
  }, [user])

  if (ready && !user) return <Navigate to="/login" replace />

  const open = (data?.picks ?? []).filter(p => !p.graded)
  const settled = (data?.picks ?? []).filter(p => p.graded)

  return (
    <div className="mx-auto w-full max-w-app px-4 py-6">
      <h1 className="font-display text-2xl font-black text-zinc-100">My Edge</h1>
      <p className="mt-1 text-sm text-zinc-400">
        Your verified record. Every pick was published before its game started.
      </p>

      {error && <p role="alert" className="mt-5 text-sm text-signal-red">{error}</p>}
      {!data && !error && <div className="skeleton mt-5 h-24 rounded-card" />}

      {data && data.record.picks === 0 && (
        <div className="mt-6 rounded-card border border-dashed border-terminal-border bg-terminal-muted p-8 text-center">
          <p className="font-display text-lg font-bold text-zinc-100">
            Your track record starts with your first prediction.
          </p>
          <p className="mx-auto mt-1 max-w-sm text-sm leading-relaxed text-zinc-500">
            Nothing here is filled in with zeros — the numbers appear once you have picks
            that have graded.
          </p>
          <Link to="/" className="tap mt-4 inline-flex items-center rounded-lg bg-brand px-4 text-sm font-semibold text-white hover:bg-brand-strong">
            Make your first pick
          </Link>
        </div>
      )}

      {data && data.record.picks > 0 && (
        <>
          <div className="mt-5"><RecordSummary record={data.record} /></div>
          <p className="mt-2 text-xs text-zinc-500">
            {data.record.graded} graded · {data.record.pending} pending
            {data.record.avg_confidence != null && ` · ${data.record.avg_confidence}% average confidence`}
          </p>

          {open.length > 0 && (
            <section className="mt-8">
              <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-500">Open picks</h2>
              <ul className="mt-2 grid gap-2 lg:grid-cols-2">
                {open.map(p => <PickRow key={p.id} pick={p} />)}
              </ul>
            </section>
          )}

          <section className="mt-8">
            <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-500">Graded</h2>
            {settled.length === 0 ? (
              <p className="mt-2 text-sm text-zinc-400">
                Nothing has graded yet. Results appear automatically once your games finish.
              </p>
            ) : (
              <ul className="mt-2 grid gap-2 lg:grid-cols-2">
                {settled.map(p => <PickRow key={p.id} pick={p} />)}
              </ul>
            )}
          </section>

          <p className="mt-8 text-sm text-zinc-400">
            Your public profile:{' '}
            <Link to={`/@${user!.username}`} className="font-semibold text-brand hover:underline">
              @{user!.username}
            </Link>
          </p>
        </>
      )}
    </div>
  )
}
