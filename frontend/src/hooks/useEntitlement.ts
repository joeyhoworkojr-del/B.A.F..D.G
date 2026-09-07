import { useEffect, useState } from 'react'

export type Entitlement = 'line_movement_history' | 'model_internals' | 'alerts'

export interface EntitlementState {
  has: boolean
  loading: boolean
}

/**
 * Entitlement check for premium panels.
 *
 * Deliberately a seam, not a feature: today it resolves from a build-time flag
 * so nothing is gated during development. When auth lands this becomes a call
 * to the server's entitlement endpoint — the panels using it don't change.
 * Client-side state is never the security boundary; the server must also refuse
 * to serve premium payloads to unentitled callers.
 */
export function useEntitlement(_entitlement: Entitlement): EntitlementState {
  const [state, setState] = useState<EntitlementState>({ has: false, loading: true })

  useEffect(() => {
    let alive = true
    // Placeholder resolution. Replace with GET /api/v1/me/entitlements.
    const granted = import.meta.env.VITE_PREMIUM_UNLOCKED !== '0'
    if (alive) setState({ has: granted, loading: false })
    return () => { alive = false }
  }, [])

  return state
}
