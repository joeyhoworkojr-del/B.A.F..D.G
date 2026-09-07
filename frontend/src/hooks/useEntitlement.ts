import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { EntitlementsOut, FeatureKey } from '../types'

export type Entitlement = FeatureKey

export interface EntitlementState {
  has: boolean
  loading: boolean
  /** Why the feature is unavailable, when the server withheld it. */
  reason: string
}

/**
 * Access check for a single feature.
 *
 * The server decides — this hook only reads `GET /api/v1/entitlements`. Client
 * state is never the security boundary: an endpoint that would serve a premium
 * payload refuses it independently, so hiding a panel here is presentation,
 * not enforcement.
 *
 * The whole response is fetched once and shared, so a page asking about three
 * features makes one request.
 */

let cached: Promise<EntitlementsOut> | null = null
const load = () => (cached ??= api.entitlements())

/** Test seam: drop the shared response so the next read refetches. */
export function resetEntitlements() {
  cached = null
}

export function useEntitlements(): { data: EntitlementsOut | null; loading: boolean } {
  const [data, setData] = useState<EntitlementsOut | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    load()
      .then(d => { if (alive) setData(d) })
      .catch(() => { /* treated as "no access", below */ })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

  return { data, loading }
}

export function useEntitlement(entitlement: Entitlement): EntitlementState {
  const { data, loading } = useEntitlements()
  if (loading || !data) return { has: false, loading, reason: '' }
  return {
    has: data.features[entitlement] === true,
    loading: false,
    // A withheld feature always explains itself; fall back rather than go blank.
    reason: data.unavailable_reason[entitlement] ?? '',
  }
}
