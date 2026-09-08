import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { api } from '../api/client'
import { PickRow } from '../components/record/RecordSummary'
import { useSession } from '../session/SessionProvider'
import type { AdminOverview, AdminUserRow, PickOut } from '../types'

/**
 * Staff portal.
 *
 * Read-only on purpose. There is deliberately no control here that can edit or
 * delete a graded pick — a staff tool able to quietly rewrite a result would
 * undermine the one claim the product makes. The server enforces that too: the
 * admin routes accept nothing but GET.
 */
export function Staff() {
  const { user, ready } = useSession()
  const [overview, setOverview] = useState<AdminOverview | null>(null)
  const [users, setUsers] = useState<AdminUserRow[]>([])
  const [picks, setPicks] = useState<PickOut[]>([])
  const [error, setError] = useState('')

  const isAdmin = user?.level === 'admin'

  useEffect(() => {
    if (!isAdmin) return
    let alive = true
    Promise.all([api.adminOverview(), api.adminUsers(), api.adminPicks()])
      .then(([o, u, p]) => {
        if (!alive) return
        setOverview(o); setUsers(u.users); setPicks(p.picks)
      })
      .catch((e: Error) => { if (alive) setError(e.message) })
    return () => { alive = false }
  }, [isAdmin])

  if (ready && !user) return <Navigate to="/login" replace />
  if (ready && !isAdmin) {
    return (
      <div className="mx-auto w-full max-w-app px-4 py-16">
        <h1 className="font-display text-2xl font-black text-zinc-100">Not found</h1>
        <p className="mt-2 text-sm text-zinc-400">
          Nothing is served here for your account.
        </p>
        <Link to="/" className="mt-4 inline-block text-sm font-semibold text-brand hover:underline">
          Back to games
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto w-full max-w-app px-4 py-6">
      <h1 className="font-display text-2xl font-black text-zinc-100">Staff</h1>
      <p className="mt-1 text-sm text-zinc-400">
        Operational view. Read-only — nothing here can alter a published or graded pick.
      </p>

      {error && <p role="alert" className="mt-5 text-sm text-signal-red">{error}</p>}
      {!overview && !error && <div className="skeleton mt-5 h-32 rounded-card" />}

      {overview && (
        <>
          {!overview.storage.durable && (
            <p className="mt-5 rounded-lg border border-signal-red/40 bg-signal-red-dim px-3 py-2 text-sm font-semibold text-signal-red">
              Storage is {overview.storage.backend} and not durable — accounts and picks
              will be lost on the next deploy.
            </p>
          )}

          <dl className="mt-5 grid gap-px overflow-hidden rounded-card border border-terminal-border bg-terminal-border sm:grid-cols-2 lg:grid-cols-4">
            {[
              ['Accounts', overview.accounts.total],
              ['Founding analysts', overview.accounts.founding],
              ['Picks published', overview.picks.total],
              ['Picks graded', overview.picks.graded],
              ['Open picks', overview.picks.open],
              ['Ranked analysts', overview.leaderboard_size],
              ['Model graded', overview.model_record.graded],
              ['Model pending', overview.model_record.pending],
            ].map(([label, value]) => (
              <div key={String(label)} className="bg-terminal-surface px-4 py-3">
                <dt className="text-xs font-bold uppercase tracking-wide text-zinc-500">{label}</dt>
                <dd className="mt-0.5 font-mono text-xl font-black tabular-nums text-zinc-100">{value}</dd>
              </div>
            ))}
          </dl>

          <p className="mt-2 text-xs text-zinc-500">
            Storage: <span className="font-mono">{overview.storage.backend}</span>
            {overview.storage.durable ? ' · durable' : ' · not durable'}
          </p>

          <div className="mt-6 grid gap-4 lg:grid-cols-3">
            <Breakdown title="By market" data={overview.picks.by_market} />
            <Breakdown title="By result" data={overview.picks.by_result} />
            <Breakdown title="By league" data={overview.picks.by_league} />
          </div>

          <section className="mt-8">
            <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-500">
              Accounts ({users.length})
            </h2>
            {users.length === 0 ? (
              <p className="mt-2 text-sm text-zinc-400">Nobody has registered yet.</p>
            ) : (
              <div className="mt-2 w-full max-w-full overflow-x-auto">
                <table className="w-full min-w-[38rem] text-sm">
                  <thead>
                    <tr className="border-b border-terminal-border text-xs uppercase tracking-wide text-zinc-500">
                      <th scope="col" className="px-3 py-2 text-left font-semibold">Analyst</th>
                      <th scope="col" className="px-3 py-2 text-left font-semibold">Email</th>
                      <th scope="col" className="px-3 py-2 text-left font-semibold">Level</th>
                      <th scope="col" className="px-3 py-2 text-right font-semibold">Picks</th>
                      <th scope="col" className="px-3 py-2 text-left font-semibold">Joined</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map(u => (
                      <tr key={u.id} className="border-b border-terminal-border/60 last:border-0">
                        <th scope="row" className="px-3 py-2.5 text-left">
                          <Link to={`/@${u.username}`} className="font-semibold text-zinc-100 hover:text-brand hover:underline">
                            @{u.username}
                          </Link>
                        </th>
                        <td className="px-3 py-2.5 text-zinc-400">{u.email}</td>
                        <td className="px-3 py-2.5 text-zinc-400">{u.level}</td>
                        <td className="px-3 py-2.5 text-right font-mono tabular-nums text-zinc-100">{u.picks}</td>
                        <td className="px-3 py-2.5 text-zinc-500">
                          {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="mt-8">
            <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-500">
              Recent picks ({picks.length})
            </h2>
            {picks.length === 0 ? (
              <p className="mt-2 text-sm text-zinc-400">No picks published yet.</p>
            ) : (
              <ul className="mt-2 grid gap-2 lg:grid-cols-2">
                {picks.slice(0, 20).map(p => <PickRow key={p.id} pick={p} />)}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  )
}

function Breakdown({ title, data }: { title: string; data: Record<string, number> }) {
  const rows = Object.entries(data)
  return (
    <section className="rounded-card border border-terminal-border bg-terminal-surface p-4">
      <h3 className="text-xs font-bold uppercase tracking-wide text-zinc-500">{title}</h3>
      {rows.length === 0 ? (
        <p className="mt-2 text-sm text-zinc-400">Nothing yet.</p>
      ) : (
        <dl className="mt-2 space-y-1">
          {rows.map(([k, v]) => (
            <div key={k} className="flex items-baseline justify-between text-sm">
              <dt className="text-zinc-400">{k}</dt>
              <dd className="font-mono font-bold tabular-nums text-zinc-100">{v}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  )
}
