import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useSession } from '../session/SessionProvider'

const MIN_PASSWORD = 10

export function Register() {
  const { register, user } = useSession()
  const navigate = useNavigate()

  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [handleState, setHandleState] = useState<'idle' | 'checking' | 'free' | 'taken'>('idle')
  const checkSeq = useRef(0)

  useEffect(() => { if (user) navigate('/onboarding', { replace: true }) }, [user, navigate])

  // Live handle check, debounced so typing doesn't hit the API every keystroke.
  useEffect(() => {
    const handle = username.trim()
    if (handle.length < 3) { setHandleState('idle'); return }
    setHandleState('checking')
    const seq = ++checkSeq.current
    const id = setTimeout(() => {
      api.usernameAvailable(handle)
        .then(r => { if (seq === checkSeq.current) setHandleState(r.available ? 'free' : 'taken') })
        .catch(() => { if (seq === checkSeq.current) setHandleState('idle') })
    }, 350)
    return () => clearTimeout(id)
  }, [username])

  const passwordTooShort = password.length > 0 && password.length < MIN_PASSWORD
  const canSubmit = useMemo(
    () => username.trim().length >= 3 && email.includes('@')
      && password.length >= MIN_PASSWORD && handleState !== 'taken' && !busy,
    [username, email, password, handleState, busy],
  )

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await register({ username: username.trim(), email: email.trim(), password })
      navigate('/onboarding', { replace: true })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto w-full max-w-md px-4 py-10">
      <h1 className="font-display text-2xl font-black text-zinc-100">Create your account</h1>
      <p className="mt-1 text-sm leading-relaxed text-zinc-400">
        Publish predictions, build a verified record, and see how you compare.
        Full access is free during the beta.
      </p>

      <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
        <Field
          id="username" label="Username" value={username} onChange={setUsername}
          autoComplete="username" prefix="@"
          hint={
            handleState === 'taken' ? 'That username is taken.'
            : handleState === 'free' ? 'Available.'
            : '3–20 characters. Letters, numbers and underscores.'
          }
          tone={handleState === 'taken' ? 'error' : handleState === 'free' ? 'good' : 'muted'}
        />
        <Field
          id="email" label="Email" type="email" value={email} onChange={setEmail}
          autoComplete="email" hint="Used to sign in and recover your account."
        />
        <Field
          id="password" label="Password" type="password" value={password}
          onChange={setPassword} autoComplete="new-password"
          hint={passwordTooShort
            ? `At least ${MIN_PASSWORD} characters.`
            : 'At least 10 characters. A short phrase works well.'}
          tone={passwordTooShort ? 'error' : 'muted'}
        />

        {error && (
          <p role="alert" className="rounded-lg border border-signal-red/40 bg-signal-red-dim px-3 py-2 text-sm text-signal-red">
            {error}
          </p>
        )}

        <button
          type="submit" disabled={!canSubmit}
          className="tap w-full rounded-lg bg-brand px-4 font-semibold text-white transition hover:bg-brand-strong disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? 'Creating your account…' : 'Create account'}
        </button>

        <p className="text-xs leading-relaxed text-zinc-500">
          Accounts created during the beta keep a permanent{' '}
          <span className="font-semibold text-zinc-400">Founding Analyst</span> badge.
        </p>
      </form>

      <p className="mt-6 text-sm text-zinc-400">
        Already have an account?{' '}
        <Link to="/login" className="font-semibold text-brand hover:underline">Sign in</Link>
      </p>
    </div>
  )
}

export function Field({
  id, label, value, onChange, hint, tone = 'muted', type = 'text',
  autoComplete, prefix,
}: {
  id: string; label: string; value: string; onChange: (v: string) => void
  hint?: string; tone?: 'muted' | 'error' | 'good'; type?: string
  autoComplete?: string; prefix?: string
}) {
  const hintColor = tone === 'error' ? 'text-signal-red'
    : tone === 'good' ? 'text-signal-green' : 'text-zinc-500'
  return (
    <div>
      <label htmlFor={id} className="block text-xs font-bold uppercase tracking-wide text-zinc-500">
        {label}
      </label>
      <div className="mt-1 flex items-center rounded-lg border border-terminal-border bg-terminal-muted focus-within:border-brand focus-within:bg-terminal-surface">
        {prefix && <span className="pl-3 text-sm font-semibold text-zinc-500">{prefix}</span>}
        <input
          id={id} type={type} value={value} autoComplete={autoComplete}
          onChange={e => onChange(e.target.value)}
          aria-describedby={hint ? `${id}-hint` : undefined}
          className="tap w-full bg-transparent px-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none"
        />
      </div>
      {hint && <p id={`${id}-hint`} className={`mt-1 text-xs ${hintColor}`}>{hint}</p>}
    </div>
  )
}
