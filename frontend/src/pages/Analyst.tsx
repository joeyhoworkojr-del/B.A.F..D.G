import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Avatar } from '../components/Avatar'
import { NotFound } from './NotFound'
import { api } from '../api/client'
import { PickRow, RecordSummary } from '../components/record/RecordSummary'
import type { AnalystOut } from '../types'

const BADGE_LABEL: Record<string, string> = {
  founding_analyst: 'Founding Analyst',
}

export function Analyst() {
  const { username = '' } = useParams()
  // Only /@handle is a profile. React Router can't constrain a param to a
  // prefix, so anything else falls through to the 404 rather than rendering
  // "analyst not found" for every mistyped URL.
  const isHandle = username.startsWith('@')
  const handle = username.slice(1)
  const [data, setData] = useState<AnalystOut | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!isHandle) return
    let alive = true
    setData(null)
    setError('')
    api.analyst(handle)
      .then(d => { if (alive) setData(d) })
      .catch((e: Error) => { if (alive) setError(e.message) })
    return () => { alive = false }
  }, [handle, isHandle])

  if (!isHandle) return <NotFound />

  if (error) {
    return (
      <div className="mx-auto w-full max-w-app px-4 py-16">
        <h1 className="font-display text-2xl font-black text-zinc-100">Analyst not found</h1>
        <p className="mt-2 text-sm text-zinc-400">
          No public profile at <span className="font-mono">@{handle}</span>.
        </p>
      </div>
    )
  }
  if (!data) return <div className="mx-auto max-w-app px-4 py-6"><div className="skeleton h-40 rounded-card" /></div>

  const { profile, record, picks } = data

  return (
    <div className="mx-auto w-full max-w-app px-4 py-6">
      <header className="flex flex-wrap items-start gap-4">
        <Avatar user={profile} size={64} />
        <div className="min-w-0">
          <h1 className="font-display text-2xl font-black text-zinc-100">
            {profile.display_name || profile.username}
          </h1>
          <p className="font-mono text-sm text-zinc-500">@{profile.username}</p>
          {profile.bio && <p className="mt-2 max-w-prose text-sm leading-relaxed text-zinc-400">{profile.bio}</p>}
          <div className="mt-2 flex flex-wrap gap-1.5">
            {profile.badges.map(b => (
              <span key={b} className="rounded-full border border-brand/30 bg-brand-soft px-2 py-0.5 text-xs font-bold text-brand">
                {BADGE_LABEL[b] ?? b}
              </span>
            ))}
            {profile.favourite_sports.map(s => (
              <span key={s} className="rounded-full bg-terminal-muted px-2 py-0.5 text-xs font-semibold text-zinc-400">
                {s === 'ncaaf' ? 'NCAAF' : s.toUpperCase()}
              </span>
            ))}
          </div>
        </div>
      </header>

      <div className="mt-5"><RecordSummary record={record} /></div>
      {record.graded < 10 && record.graded > 0 && (
        <p className="mt-2 text-xs text-signal-amber">
          Provisional — {record.graded} graded {record.graded === 1 ? 'pick' : 'picks'}.
          A short sample says very little either way.
        </p>
      )}

      <section className="mt-8">
        <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-500">Picks</h2>
        {picks.length === 0 ? (
          <p className="mt-2 text-sm leading-relaxed text-zinc-400">
            No published picks yet. Open picks stay private until their game starts, so
            nobody can be tailed before kickoff.
          </p>
        ) : (
          <ul className="mt-2 grid gap-2 lg:grid-cols-2">
            {picks.map(p => <PickRow key={p.id} pick={p} />)}
          </ul>
        )}
      </section>
    </div>
  )
}
