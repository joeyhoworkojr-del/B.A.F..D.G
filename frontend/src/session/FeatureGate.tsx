import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useFeature, useSession } from './SessionProvider'

/**
 * Wraps premium surface.
 *
 * During the beta this renders its children for anyone signed in, so a gate
 * never fires before a paywall exists. Signed-out visitors see the reason and
 * a way in, which is what gives an account a purpose.
 */
export function FeatureGate({
  feature, children, title, blurb,
}: { feature: string; children: ReactNode; title?: string; blurb?: string }) {
  const { allowed, reason, loading } = useFeature(feature)
  const { user } = useSession()

  if (loading) return <div className="skeleton h-32 rounded-card" />
  if (allowed) return <>{children}</>

  return (
    <section className="rounded-card border border-terminal-border bg-terminal-muted p-5">
      <div className="flex flex-wrap items-center gap-2">
        <PremiumBadge />
        <h3 className="text-sm font-bold text-zinc-100">{title ?? 'Stat Edge Pro'}</h3>
      </div>
      <p className="mt-2 max-w-prose text-sm leading-relaxed text-zinc-400">
        {blurb ?? reason ?? 'This is part of Stat Edge Pro.'}
      </p>
      {!user && (
        <Link
          to="/register"
          className="tap mt-3 inline-flex items-center rounded-lg bg-brand px-4 text-sm font-semibold text-white hover:bg-brand-strong"
        >
          Create a free account
        </Link>
      )}
    </section>
  )
}

/** Marks premium surface without nagging: during beta it says so plainly. */
export function PremiumBadge({ className = '' }: { className?: string }) {
  const { entitlements } = useSession()
  const included = entitlements.beta_open && entitlements.authenticated
  return (
    <span
      className={`inline-flex items-center rounded-full border border-brand/30 bg-brand-soft px-2 py-0.5 text-xs font-bold text-brand ${className}`}
    >
      PRO{included ? ' · Included during beta' : ''}
    </span>
  )
}
