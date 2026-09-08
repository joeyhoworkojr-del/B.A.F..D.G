import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { AvatarUpload } from '../components/account/AvatarUpload'
import { useSession } from '../session/SessionProvider'
import { can } from '../session/powers'

const FEATURE_LABEL: Record<string, string> = {
  line_movement_history: 'Line-movement history',
  model_internals: 'Model internals',
  alerts: 'Push and email alerts',
  player_props: 'Player props',
  saved_games: 'Saved games and watchlist',
  edge_ai: 'Edge AI',
}

function Section({
  title, description, children,
}: { title: string; description?: string; children: React.ReactNode }) {
  return (
    <section className="rounded-card border border-terminal-border bg-terminal-surface p-5">
      <h2 className="text-base font-bold text-zinc-100">{title}</h2>
      {description && <p className="mt-1 text-sm text-zinc-400">{description}</p>}
      <div className="mt-4">{children}</div>
    </section>
  )
}

function EditProfile() {
  const { user, applySession } = useSession()
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [displayName, setDisplayName] = useState(user?.display_name ?? '')
  const [bio, setBio] = useState(user?.bio ?? '')

  if (!user) return null

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true); setError(''); setSaved(false)
    try {
      applySession(await api.updateProfile({ display_name: displayName, bio }))
      setSaved(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'That could not be saved.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <AvatarUpload />

      <div>
        <label htmlFor="display-name" className="block text-sm font-semibold text-zinc-300">
          Display name
        </label>
        <input
          id="display-name"
          value={displayName}
          maxLength={60}
          onChange={e => setDisplayName(e.target.value)}
          className="mt-1 w-full rounded-lg border border-terminal-border bg-terminal-bg px-3 py-2 text-sm text-zinc-100"
        />
      </div>

      <div>
        <label htmlFor="bio" className="block text-sm font-semibold text-zinc-300">Bio</label>
        <textarea
          id="bio"
          value={bio}
          rows={3}
          maxLength={400}
          onChange={e => setBio(e.target.value)}
          className="mt-1 w-full rounded-lg border border-terminal-border bg-terminal-bg px-3 py-2 text-sm text-zinc-100"
        />
        <p className="mt-1 text-xs text-zinc-500">{bio.length}/400 · shown on your public profile</p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={saving}
          className="tap inline-flex items-center rounded-lg bg-brand px-4 text-sm font-semibold text-white hover:bg-brand-strong disabled:opacity-60"
        >
          {saving ? 'Saving…' : 'Save changes'}
        </button>
        {saved && <span className="text-sm font-semibold text-signal-green">Saved</span>}
        {error && <span role="alert" className="text-sm text-signal-red">{error}</span>}
      </div>
    </form>
  )
}

function ChangePassword() {
  const { applySession } = useSession()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true); setError(''); setDone(false)
    try {
      applySession(await api.changePassword(current, next))
      setCurrent(''); setNext(''); setDone(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'That password could not be changed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div>
        <label htmlFor="current-pw" className="block text-sm font-semibold text-zinc-300">
          Current password
        </label>
        <input
          id="current-pw" type="password" autoComplete="current-password"
          value={current} onChange={e => setCurrent(e.target.value)} required
          className="mt-1 w-full rounded-lg border border-terminal-border bg-terminal-bg px-3 py-2 text-sm text-zinc-100"
        />
      </div>
      <div>
        <label htmlFor="new-pw" className="block text-sm font-semibold text-zinc-300">
          New password
        </label>
        <input
          id="new-pw" type="password" autoComplete="new-password" minLength={10}
          value={next} onChange={e => setNext(e.target.value)} required
          className="mt-1 w-full rounded-lg border border-terminal-border bg-terminal-bg px-3 py-2 text-sm text-zinc-100"
        />
        <p className="mt-1 text-xs text-zinc-500">
          At least 10 characters. Changing it signs out every other device, which is the
          point — a password change that left an intruder signed in would not have locked
          anyone out.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit" disabled={busy}
          className="tap inline-flex items-center rounded-lg bg-brand px-4 text-sm font-semibold text-white hover:bg-brand-strong disabled:opacity-60"
        >
          {busy ? 'Changing…' : 'Change password'}
        </button>
        {done && (
          <span className="text-sm font-semibold text-signal-green">
            Changed · other devices signed out
          </span>
        )}
        {error && <span role="alert" className="text-sm text-signal-red">{error}</span>}
      </div>
    </form>
  )
}

/**
 * Account settings — the private half of an account.
 *
 * The public profile lives at /@username and is what other people see. This
 * page is everything only the account holder should: the email on file, the
 * password, what the plan includes, and an unmissable way out.
 */
export function Account() {
  const { user, entitlements, ready, logout } = useSession()
  const navigate = useNavigate()
  const [signingOut, setSigningOut] = useState(false)

  if (ready && !user) return <Navigate to="/login" replace />
  if (!user) return <div className="mx-auto w-full max-w-app px-4 py-10"><div className="skeleton h-40 rounded-card" /></div>

  const signOut = async () => {
    setSigningOut(true)
    try { await logout(); navigate('/') } finally { setSigningOut(false) }
  }

  const features = Object.entries(entitlements.features ?? {})

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-black text-zinc-100">Account settings</h1>
          <p className="mt-1 text-sm text-zinc-400">
            Private to you. Your{' '}
            <Link to={`/@${user.username}`} className="font-semibold text-brand hover:underline">
              public profile
            </Link>{' '}
            is what everyone else sees.
          </p>
        </div>
        {can(entitlements, 'view_staff') && (
          <Link
            to="/staff"
            className="tap inline-flex items-center rounded-lg border border-terminal-border px-3 text-sm font-semibold text-zinc-400 hover:text-zinc-100"
          >
            Staff area
          </Link>
        )}
      </header>

      <div className="mt-6 space-y-4">
        <Section title="Profile" description="Your photo, name and bio, as they appear across StatEdge.">
          <EditProfile />
        </Section>

        <Section title="Email">
          <p className="font-mono text-sm text-zinc-100">{user.email}</p>
          <p className="mt-1.5 text-xs text-zinc-500">
            {user.email_verified
              ? 'Verified.'
              : 'Not verified. Email verification is not wired up yet — there is no mail provider configured, and a button that pretended to send one would be worse than none.'}
          </p>
        </Section>

        <Section title="Password">
          <ChangePassword />
        </Section>

        <Section
          title="Notifications"
          description="Alerts are not built yet, so there is nothing here to switch on."
        >
          <p className="text-sm text-zinc-400">
            When alerts ship — probability swings on games you follow, and results on your
            own picks — the controls will be here. Until then StatEdge sends you nothing.
          </p>
        </Section>

        <Section title="Privacy">
          <p className="text-sm leading-relaxed text-zinc-400">
            StatEdge does not run analytics, advertising or third-party trackers, and does
            not record what you browse. What is stored is what you created: your account,
            your profile, and the picks you published.
          </p>
        </Section>

        <Section
          title="Subscription"
          description={`You are on the ${entitlements.level} tier.`}
        >
          <p className="text-sm text-zinc-400">
            StatEdge is free during beta and there is no billing to manage — no card is on
            file and nothing will be charged. Paid tiers are built but not switched on.
          </p>
          {features.length > 0 && (
            <ul className="mt-3 grid gap-1.5 sm:grid-cols-2">
              {features.map(([key, on]) => (
                <li key={key} className="flex items-baseline gap-2 text-sm">
                  <span className={on ? 'text-signal-green' : 'text-zinc-600'} aria-hidden="true">
                    {on ? '✓' : '·'}
                  </span>
                  <span className={on ? 'text-zinc-300' : 'text-zinc-500'}>
                    {FEATURE_LABEL[key] ?? key.replace(/_/g, ' ')}
                    {!on && entitlements.unavailable_reason?.[key]
                      ? ` — ${entitlements.unavailable_reason[key]}`
                      : ''}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Section>

        <section className="rounded-card border border-terminal-border bg-terminal-surface p-5">
          <h2 className="text-base font-bold text-zinc-100">Log out</h2>
          <p className="mt-1 text-sm text-zinc-400">
            Ends this session on this device. Your picks and record are untouched.
          </p>
          <button
            type="button"
            onClick={signOut}
            disabled={signingOut}
            className="tap mt-4 inline-flex items-center rounded-lg border border-signal-red/40 bg-signal-red-dim px-4 text-sm font-bold text-signal-red hover:bg-signal-red/10 disabled:opacity-60"
          >
            {signingOut ? 'Logging out…' : 'Log out'}
          </button>
        </section>
      </div>
    </div>
  )
}
