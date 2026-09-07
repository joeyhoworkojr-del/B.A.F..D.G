import type { ReactNode } from 'react'
import { useEntitlement, type Entitlement } from '../../hooks/useEntitlement'

export interface LockedPremiumPanelProps {
  title: string
  /** What the user gets by unlocking — concrete, not marketing fluff. */
  description: string
  /** Entitlement this panel requires. */
  requires: Entitlement
  children: ReactNode
}

/**
 * Boundary around premium content. Entitlement resolution is deliberately
 * behind a hook so a real server-side check (and a paywall) can replace the
 * stub without touching any panel that uses this.
 */
export function LockedPremiumPanel({ title, description, requires, children }: LockedPremiumPanelProps) {
  const { has, loading } = useEntitlement(requires)

  if (loading) {
    return <div className="skeleton h-24 rounded-xl" aria-busy="true" />
  }
  if (has) return <>{children}</>

  return (
    <section className="rounded-xl border border-dashed border-terminal-border bg-terminal-surface p-4">
      <div className="flex items-start gap-3">
        <span aria-hidden="true" className="mt-0.5 text-zinc-500">🔒</span>
        <div>
          <h2 className="text-sm font-bold text-zinc-100">{title}</h2>
          <p className="mt-1 text-sm text-zinc-400">{description}</p>
          <p className="mt-2 text-xs text-zinc-500">Included with StatEdge Pro.</p>
        </div>
      </div>
    </section>
  )
}
