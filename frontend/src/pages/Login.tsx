import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useSession } from '../session/SessionProvider'
import { Field } from './Register'

export function Login() {
  const { login, user } = useSession()
  const navigate = useNavigate()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => { if (user) navigate('/my-edge', { replace: true }) }, [user, navigate])

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(identifier.trim(), password)
      navigate('/my-edge', { replace: true })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto w-full max-w-md px-4 py-10">
      <h1 className="font-display text-2xl font-black text-zinc-100">Sign in</h1>
      <p className="mt-1 text-sm text-zinc-400">Pick up where your record left off.</p>

      <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
        <Field id="identifier" label="Username or email" value={identifier}
               onChange={setIdentifier} autoComplete="username" />
        <Field id="password" label="Password" type="password" value={password}
               onChange={setPassword} autoComplete="current-password" />

        {error && (
          <p role="alert" className="rounded-lg border border-signal-red/40 bg-signal-red-dim px-3 py-2 text-sm text-signal-red">
            {error}
          </p>
        )}

        <button
          type="submit" disabled={busy || !identifier || !password}
          className="tap w-full rounded-lg bg-brand px-4 font-semibold text-white transition hover:bg-brand-strong disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>

      <p className="mt-6 text-sm text-zinc-400">
        New to Stat Edge?{' '}
        <Link to="/register" className="font-semibold text-brand hover:underline">Create an account</Link>
      </p>
      <p className="mt-3 text-xs leading-relaxed text-zinc-500">
        Password recovery isn’t available yet — it needs an email provider, which isn’t
        configured. Until then, keep your password somewhere safe.
      </p>
    </div>
  )
}
