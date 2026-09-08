import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Avatar } from '../components/Avatar'
import { api } from '../api/client'
import type { LeaderboardOut, Standing } from '../types'

const LEAGUES: { id?: string; label: string }[] = [
  { id: undefined, label: 'Overall' },
  { id: 'ncaaf', label: 'NCAAF' },
  { id: 'nfl', label: 'NFL' },
]

const pill = (on: boolean) =>
  `tap inline-flex items-center rounded-full px-4 text-sm font-bold transition ${
    on ? 'bg-brand text-white shadow-card' : 'bg-terminal-muted text-zinc-400 hover:text-zinc-100'
  }`

const units = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}u`
const pct = (v?: number | null) => (v == null ? '—' : `${(v * 100).toFixed(1)}%`)

export function Leaderboard() {
  const [league, setLeague] = useState<string | undefined>(undefined)
  const [data, setData] = useState<LeaderboardOut | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    setData(null)
    api.leaderboard(league)
      .then(d => { if (alive) setData(d) })
      .catch((e: Error) => { if (alive) setError(e.message) })
    return () => { alive = false }
  }, [league])

  return (
    <div className="mx-auto w-full max-w-app px-4 py-6">
      <h1 className="font-display text-2xl font-black text-zinc-100">Leaderboard</h1>
      <p className="mt-1 max-w-2xl text-sm leading-relaxed text-zinc-400">
        Ranked on results, not followers. Every pick counted here was published before
        its game started and graded automatically afterwards.
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        {LEAGUES.map(l => (
          <button key={l.label} type="button" onClick={() => setLeague(l.id)}
            aria-pressed={league === l.id} className={pill(league === l.id)}>
            {l.label}
          </button>
        ))}
      </div>

      {error && <p role="alert" className="mt-5 text-sm text-signal-red">{error}</p>}
      {!data && !error && <div className="skeleton mt-5 h-48 rounded-card" />}

      {data && data.count === 0 && (
        <div className="mt-6 rounded-card border border-dashed border-terminal-border bg-terminal-muted p-8 text-center">
          <p className="font-display text-lg font-bold text-zinc-100">No graded records yet</p>
          <p className="mx-auto mt-1 max-w-md text-sm leading-relaxed text-zinc-500">
            The table fills in as analysts publish picks and those games finish. Nothing
            here is seeded with example accounts.
          </p>
          <Link to="/register" className="tap mt-4 inline-flex items-center rounded-lg bg-brand px-4 text-sm font-semibold text-white hover:bg-brand-strong">
            Be the first
          </Link>
        </div>
      )}

      {data && data.count > 0 && (
        <>
          {/* Desktop: a dense table. Mobile: cards — a wide table crushed into a
              narrow screen is unreadable, not responsive. */}
          <div className="mt-5 hidden w-full max-w-full overflow-x-auto md:block">
            <table className="w-full min-w-[44rem] text-sm">
              <thead>
                <tr className="border-b border-terminal-border text-xs uppercase tracking-wide text-zinc-500">
                  <th scope="col" className="px-3 py-2 text-left font-semibold">#</th>
                  <th scope="col" className="px-3 py-2 text-left font-semibold">Analyst</th>
                  <th scope="col" className="px-3 py-2 text-right font-semibold">Edge Rating</th>
                  <th scope="col" className="px-3 py-2 text-right font-semibold">Record</th>
                  <th scope="col" className="px-3 py-2 text-right font-semibold">Win rate</th>
                  <th scope="col" className="px-3 py-2 text-right font-semibold">Units</th>
                  <th scope="col" className="px-3 py-2 text-right font-semibold">ROI</th>
                </tr>
              </thead>
              <tbody>
                {data.standings.map((s, i) => (
                  <tr key={s.user_id} className="border-b border-terminal-border/60 last:border-0">
                    <td className="px-3 py-2.5 font-mono tabular-nums text-zinc-500">{i + 1}</td>
                    <th scope="row" className="px-3 py-2.5 text-left">
                      <AnalystCell s={s} />
                    </th>
                    <td className="px-3 py-2.5 text-right font-mono font-bold tabular-nums text-zinc-100">
                      {s.edge_rating.toFixed(1)}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono tabular-nums text-zinc-400">
                      {s.wins}-{s.losses}{s.pushes ? `-${s.pushes}` : ''}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono tabular-nums text-zinc-400">{pct(s.win_rate)}</td>
                    <td className={`px-3 py-2.5 text-right font-mono font-bold tabular-nums ${
                      s.units >= 0 ? 'text-signal-green' : 'text-signal-red'}`}>
                      {units(s.units)}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono tabular-nums text-zinc-400">
                      {s.roi_pct == null ? '—' : `${s.roi_pct >= 0 ? '+' : ''}${s.roi_pct.toFixed(1)}%`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <ul className="mt-5 space-y-2 md:hidden">
            {data.standings.map((s, i) => (
              <li key={s.user_id} className="rounded-card border border-terminal-border bg-terminal-surface p-4">
                <div className="flex items-start gap-3">
                  <span className="font-mono text-sm font-bold tabular-nums text-zinc-500">{i + 1}</span>
                  <div className="min-w-0 flex-1"><AnalystCell s={s} /></div>
                  <span className="font-mono text-lg font-black tabular-nums text-zinc-100">
                    {s.edge_rating.toFixed(1)}
                  </span>
                </div>
                <dl className="mt-3 grid grid-cols-3 gap-2 text-xs">
                  {[
                    ['Record', `${s.wins}-${s.losses}`],
                    ['Units', units(s.units)],
                    ['Win rate', pct(s.win_rate)],
                  ].map(([label, value]) => (
                    <div key={label}>
                      <dt className="font-semibold uppercase tracking-wide text-zinc-500">{label}</dt>
                      <dd className="mt-0.5 font-mono font-bold tabular-nums text-zinc-100">{value}</dd>
                    </div>
                  ))}
                </dl>
              </li>
            ))}
          </ul>

          <p className="mt-5 max-w-2xl text-xs leading-relaxed text-zinc-500">
            {data.note} Analysts with fewer than {data.min_graded} graded picks are marked
            provisional and rank below established records, however good the numbers look.
          </p>
        </>
      )}
    </div>
  )
}

function AnalystCell({ s }: { s: Standing }) {
  return (
    <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
      <Avatar user={s} size={24} />
      <Link to={`/@${s.username}`} className="font-semibold text-zinc-100 hover:text-brand hover:underline">
        {s.display_name}
      </Link>
      <span className="font-mono text-xs text-zinc-500">@{s.username}</span>
      {s.provisional && (
        <span className="rounded-full border border-signal-amber/40 bg-signal-amber-dim px-2 py-0.5 text-xs font-bold text-signal-amber">
          Provisional · {s.graded}
        </span>
      )}
    </span>
  )
}
