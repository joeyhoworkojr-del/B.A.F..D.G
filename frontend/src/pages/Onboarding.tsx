import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useSession } from '../session/SessionProvider'

const SPORTS = [
  { id: 'nfl', label: 'NFL' },
  { id: 'ncaaf', label: 'College Football' },
]

const INTERESTS = [
  'Predictions', 'Player Props', 'Advanced Stats',
  'Live Analysis', 'Community Picks', 'Trends',
]

const chip = (on: boolean) =>
  `tap inline-flex items-center rounded-full border px-4 text-sm font-semibold transition ${
    on ? 'border-brand bg-brand text-white' : 'border-terminal-border bg-terminal-surface text-zinc-400 hover:text-zinc-100'
  }`

/**
 * Four short steps, every one skippable.
 *
 * Onboarding exists to make the first session useful, not to collect data — so
 * nothing here is required and the account already works without it.
 */
export function Onboarding() {
  const { user, applySession } = useSession()
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [sports, setSports] = useState<string[]>([])
  const [interests, setInterests] = useState<string[]>([])
  const [displayName, setDisplayName] = useState('')
  const [busy, setBusy] = useState(false)

  if (!user) return <Navigate to="/register" replace />

  const toggle = (list: string[], set: (v: string[]) => void, value: string) =>
    set(list.includes(value) ? list.filter(v => v !== value) : [...list, value])

  async function finish() {
    setBusy(true)
    try {
      applySession(await api.updateProfile({
        favourite_sports: sports,
        interests,
        display_name: displayName.trim() || user!.username,
        onboarded: true,
      }))
    } catch {
      // Preferences are a convenience; a failure here must not trap someone
      // in onboarding with a working account.
    } finally {
      navigate('/', { replace: true })
    }
  }

  const steps = [
    {
      title: 'Welcome to Stat Edge',
      blurb: 'Build your edge. Publish predictions, and let the results speak.',
      body: null,
    },
    {
      title: 'Which sports do you follow?',
      blurb: 'We’ll lead with these. You can change it any time.',
      body: (
        <div className="flex flex-wrap gap-2">
          {SPORTS.map(s => (
            <button key={s.id} type="button" onClick={() => toggle(sports, setSports, s.id)}
              aria-pressed={sports.includes(s.id)} className={chip(sports.includes(s.id))}>
              {s.label}
            </button>
          ))}
        </div>
      ),
    },
    {
      title: 'What are you here for?',
      blurb: 'This shapes what we surface first.',
      body: (
        <div className="flex flex-wrap gap-2">
          {INTERESTS.map(i => (
            <button key={i} type="button" onClick={() => toggle(interests, setInterests, i)}
              aria-pressed={interests.includes(i)} className={chip(interests.includes(i))}>
              {i}
            </button>
          ))}
        </div>
      ),
    },
    {
      title: 'How should we show your name?',
      blurb: `Your handle stays @${user.username}. This is the name on your analyst profile.`,
      body: (
        <div>
          <label htmlFor="display-name" className="sr-only">Display name</label>
          <input
            id="display-name" value={displayName} onChange={e => setDisplayName(e.target.value)}
            placeholder={user.username} maxLength={60}
            className="tap w-full rounded-lg border border-terminal-border bg-terminal-muted px-3 text-sm text-zinc-100 focus:border-brand focus:bg-terminal-surface"
          />
        </div>
      ),
    },
  ]

  const current = steps[step]
  const last = step === steps.length - 1

  return (
    <div className="mx-auto w-full max-w-lg px-4 py-10">
      <div className="flex items-center gap-1.5" aria-hidden="true">
        {steps.map((_, i) => (
          <span key={i} className={`h-1 flex-1 rounded-full ${i <= step ? 'bg-brand' : 'bg-terminal-border'}`} />
        ))}
      </div>
      <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-zinc-500">
        Step {step + 1} of {steps.length}
      </p>

      <h1 className="mt-2 font-display text-2xl font-black text-zinc-100">{current.title}</h1>
      <p className="mt-1 text-sm leading-relaxed text-zinc-400">{current.blurb}</p>
      {current.body && <div className="mt-5">{current.body}</div>}

      <div className="mt-8 flex items-center gap-2">
        <button
          type="button" disabled={busy}
          onClick={() => (last ? void finish() : setStep(step + 1))}
          className="tap rounded-lg bg-brand px-5 font-semibold text-white hover:bg-brand-strong disabled:opacity-40"
        >
          {last ? (busy ? 'Finishing…' : 'Your Edge starts now') : 'Continue'}
        </button>
        <button
          type="button" onClick={() => void finish()} disabled={busy}
          className="tap rounded-lg px-4 text-sm font-semibold text-zinc-500 hover:text-zinc-100"
        >
          Skip
        </button>
      </div>
    </div>
  )
}
