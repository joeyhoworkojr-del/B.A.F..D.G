import { Link } from 'react-router-dom'
import { useEntitlements } from '../hooks/useEntitlement'

const FEATURE_LABEL: Record<string, string> = {
  line_movement_history: 'Line-movement history',
  model_internals: 'Model internals',
  alerts: 'Push and email alerts',
  player_props: 'Player props',
  saved_games: 'Saved games and watchlist',
}

/**
 * Account is the user's own state — plan and access — not information about the
 * product. There is no sign-in here because there is no identity provider
 * configured; rather than render a form that stores a password or a localStorage
 * flag pretending to be a session, this page says exactly what is missing.
 */
export function Account() {
  const { data, loading } = useEntitlements()

  return (
    <div className="mx-auto w-full max-w-app px-4 py-6">
      <h1 className="font-display text-2xl font-black text-zinc-100">Account</h1>
      <p className="mt-1 text-sm text-zinc-400">Your plan and what it includes.</p>

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <section className="rounded-card border border-terminal-border bg-terminal-surface p-5">
          <h2 className="text-base font-bold text-zinc-100">Sign in</h2>
          {loading && <p className="mt-2 text-sm text-zinc-400">Checking…</p>}
          {!loading && data && !data.auth_configured && (
            <>
              <p className="mt-2 text-sm leading-relaxed text-zinc-400">
                Accounts aren’t available. There is no sign-in form on this site on
                purpose — a form that stored a password, or a flag in your browser
                pretending to be a session, would be worse than no account at all.
              </p>
              <h3 className="mt-4 text-sm font-bold text-zinc-100">What accounts need</h3>
              <ul className="mt-2 space-y-2 text-sm leading-relaxed text-zinc-400">
                <li className="flex gap-2">
                  <span aria-hidden="true" className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-signal-amber" />
                  <span>
                    A provider-managed identity service that owns credentials, sessions and
                    password resets. StatEdge would never store a password itself.
                  </span>
                </li>
                <li className="flex gap-2">
                  <span aria-hidden="true" className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-signal-amber" />
                  <span>
                    Storage that survives a deploy. Today the database lives on the
                    machine’s temporary disk, so any account created would disappear on the
                    next release.
                  </span>
                </li>
              </ul>
            </>
          )}
          {!loading && data?.auth_configured && (
            <p className="mt-2 text-sm text-zinc-400">
              Authentication is configured for this deployment.
            </p>
          )}
        </section>

        <section className="rounded-card border border-terminal-border bg-terminal-surface p-5">
          <h2 className="text-base font-bold text-zinc-100">Plan</h2>
          {loading && <p className="mt-2 text-sm text-zinc-400">Checking access…</p>}
          {!loading && !data && (
            <p role="alert" className="mt-2 text-sm text-signal-red">
              Couldn’t reach the entitlements endpoint, so access can’t be confirmed.
            </p>
          )}
          {!loading && data && (
            <>
              <p className="mt-1 inline-flex items-center rounded-full bg-brand-soft px-3 py-1 text-sm font-bold capitalize text-brand">
                {data.plan}
              </p>
              <p className="mt-3 text-sm leading-relaxed text-zinc-400">{data.note}</p>

              <ul className="mt-4 space-y-2">
                {Object.entries(data.features ?? {}).map(([key, granted]) => (
                  <li key={key} className="text-sm">
                    <span className="flex items-center gap-2">
                      <span
                        aria-hidden="true"
                        className={`grid h-4 w-4 shrink-0 place-items-center rounded-full text-xs font-bold text-white ${
                          granted ? 'bg-brand' : 'bg-zinc-600'
                        }`}
                      >
                        {granted ? '✓' : '–'}
                      </span>
                      <span className={granted ? 'font-semibold text-zinc-100' : 'text-zinc-400'}>
                        {FEATURE_LABEL[key] ?? key}
                      </span>
                    </span>
                    {!granted && data.unavailable_reason?.[key] && (
                      <span className="mt-0.5 block pl-6 text-xs leading-relaxed text-zinc-500">
                        {data.unavailable_reason?.[key]}
                      </span>
                    )}
                  </li>
                ))}
              </ul>

              <p className="mt-4 text-xs leading-relaxed text-zinc-500">
                Access is decided on the server, not in this page. Nothing is for sale and
                no payment method is collected.
              </p>
            </>
          )}
        </section>
      </div>

      <p className="mt-6 text-sm text-zinc-400">
        Want to know how the numbers are built?{' '}
        <Link to="/about" className="font-semibold text-brand hover:underline">Read the methodology</Link>
        {' '}or{' '}
        <Link to="/faq" className="font-semibold text-brand hover:underline">browse the FAQ</Link>.
      </p>
    </div>
  )
}
