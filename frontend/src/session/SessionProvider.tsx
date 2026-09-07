import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { api } from '../api/client'
import type { AccountEntitlements, PrivateProfile, SessionOut } from '../types'

const GUEST: AccountEntitlements = {
  level: 'guest', authenticated: false, beta_open: true,
  features: {}, unavailable_reason: {}, billing_enabled: false, note: '',
}

interface SessionState {
  user: PrivateProfile | null
  entitlements: AccountEntitlements
  loading: boolean
  /** True once the first /auth/me has resolved, however it resolved. */
  ready: boolean
  refresh: () => Promise<void>
  login: (identifier: string, password: string) => Promise<void>
  register: (body: { username: string; email: string; password: string; display_name?: string }) => Promise<void>
  logout: () => Promise<void>
  applySession: (next: SessionOut) => void
}

const Ctx = createContext<SessionState | null>(null)

/**
 * The signed-in account, resolved from the server on every load.
 *
 * There is no token in JavaScript and nothing about identity in storage: the
 * session is an httpOnly cookie the browser attaches automatically, and this
 * provider only ever asks the server who that cookie belongs to. A client that
 * cannot read its own session is a client that cannot leak one.
 */
export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<PrivateProfile | null>(null)
  const [entitlements, setEntitlements] = useState<AccountEntitlements>(GUEST)
  const [loading, setLoading] = useState(true)
  const [ready, setReady] = useState(false)

  const applySession = useCallback((next: SessionOut) => {
    setUser(next.user)
    setEntitlements(next.entitlements ?? GUEST)
  }, [])

  const refresh = useCallback(async () => {
    try {
      applySession(await api.session())
    } catch {
      // A failed check means "not signed in", not an error worth showing.
      setUser(null)
      setEntitlements(GUEST)
    } finally {
      setLoading(false)
      setReady(true)
    }
  }, [applySession])

  useEffect(() => { void refresh() }, [refresh])

  const login = useCallback(async (identifier: string, password: string) => {
    applySession(await api.login({ identifier, password }))
  }, [applySession])

  const register = useCallback(async (body: {
    username: string; email: string; password: string; display_name?: string
  }) => {
    applySession(await api.register(body))
  }, [applySession])

  const logout = useCallback(async () => {
    try { await api.logout() } finally {
      setUser(null)
      setEntitlements(GUEST)
    }
  }, [])

  const value = useMemo<SessionState>(() => ({
    user, entitlements, loading, ready, refresh, login, register, logout, applySession,
  }), [user, entitlements, loading, ready, refresh, login, register, logout, applySession])

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useSession(): SessionState {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useSession must be used inside SessionProvider')
  return ctx
}

/**
 * Whether the current account may use a feature.
 *
 * Every gate in the product goes through here, so switching from free beta to
 * paid access is a server change rather than a hunt through components. This is
 * presentation only — the endpoint that would serve a gated payload refuses it
 * independently.
 */
export function useFeature(feature: string): { allowed: boolean; reason: string; loading: boolean } {
  const { entitlements, loading } = useSession()
  return {
    allowed: entitlements.features[feature] === true,
    reason: entitlements.unavailable_reason[feature] ?? '',
    loading,
  }
}
