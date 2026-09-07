import { Link } from 'react-router-dom'
import { useEntitlement } from '../hooks/useEntitlement'

/**
 * Account is deliberately separate from About: this is the user's own state
 * (plan, entitlements), not information about the product.
 */
export function Account() {
  const premium = useEntitlement('line_movement_history')

  return (
    <div className="mx-auto w-full max-w-[1200px] px-4 py-6">
      <h1 className="font-display text-2xl font-black text-zinc-100">Account</h1>
      <p className="mt-1 text-sm text-zinc-400">Your plan and access.</p>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <section className="rounded-xl border border-terminal-border bg-terminal-surface p-4">
          <h2 className="text-sm font-bold text-zinc-100">Sign in</h2>
          <p className="mt-1 text-sm text-zinc-400">
            Accounts aren’t enabled yet. When they are, signing in will sync your tracked
            games and alerts across devices.
          </p>
          <button
            type="button"
            disabled
            className="mt-3 cursor-not-allowed rounded-lg border border-terminal-border px-3 py-2 text-sm font-semibold text-zinc-500"
          >
            Sign in — coming soon
          </button>
        </section>

        <section className="rounded-xl border border-terminal-border bg-terminal-surface p-4">
          <h2 className="text-sm font-bold text-zinc-100">Plan</h2>
          <p className="mt-1 text-sm text-zinc-400">
            {premium.loading
              ? 'Checking access…'
              : premium.has
                ? 'Premium panels are currently open while StatEdge is in development.'
                : 'Premium panels (line-movement history, model internals, alerts) are locked.'}
          </p>
          <p className="mt-3 text-xs text-zinc-500">
            Billing isn’t implemented. Entitlements resolve through a single hook so the
            server can become the source of truth without changing any panel.
          </p>
        </section>
      </div>

      <p className="mt-6 text-sm text-zinc-400">
        Looking for how the model works?{' '}
        <Link to="/about" className="font-semibold text-signal-green hover:underline">Read About StatEdge</Link>.
      </p>
    </div>
  )
}
