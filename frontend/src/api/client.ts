import type {
  BoardResponse,
  SoccerPredictResponse,
  NFLPredictResponse,
  RankingsResponse,
  TeamInfo,
  KeyPlayerOut,
  SoccerMarketOdds,
  NFLMarketOdds,
  BestBetsResponse,
  BestParlayResponse,
  AllScoreboardsOut,
  ScoreboardOut,
  TodayResponse,
  GridironLeague,
  AccuracyResponse,
  SoccerUpcomingResponse,
  ChatMessage,
  ChatPage,
  EdgeAiAnswer,
  EdgeAiStatus,
  EdgeAiTurn,
  UpcomingResponse,
  WinHistoryOut,
  PlayByPlayOut,
  GameDetailOut,
  FootballLeague,
  NewsFeedOut,
  EntitlementsOut,
  PropsOut,
  GamePropsOut,
  SessionOut,
  MyPicksOut,
  PickOut,
  GameCommunityOut,
  AnalystOut,
  SubmitPickBody,
  LeaderboardOut,
  AdminOverview,
  AdminUserRow,
} from '../types'

// Same-origin by default. Vite's dev server proxies /api to :8000, the Docker
// image serves the SPA from the API process, and on Vercel the rewrites in
// vercel.json forward /api to the Fly API — so an unset VITE_API_BASE is
// correct in every environment rather than pointing at localhost.
// Trailing slashes are stripped so VITE_API_BASE="/" yields "/api/v1/..." and
// not a protocol-relative "//api/v1/..." URL.
const BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/+$/, '')

/**
 * Session token, used only when the cookie cannot get through.
 *
 * The httpOnly cookie is the real credential and is always preferred — script
 * cannot read it, so an XSS cannot steal it. But a proxy that strips the
 * Cookie header makes a cookie-only session unusable, which is what broke
 * sign-in on statedge.ca. This is the fallback for that case.
 *
 * It is deliberately weaker and deliberately temporary: once the API is
 * same-origin with the site the cookie arrives, the server prefers it, and
 * this stops mattering.
 */
const TOKEN_KEY = 'statedge.session'

export function setSessionToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch { /* private mode — the session then lasts as long as the tab */ }
}

export function getSessionToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // The session is an httpOnly cookie, so it has to be sent explicitly:
  // fetch omits credentials on cross-origin requests, and would silently log
  // the user out if VITE_API_BASE ever pointed at the API's own host.
  const token = getSessionToken()
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    const detail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail ?? `HTTP ${res.status}`)
    throw new Error(detail)
  }
  return res.json()
}

async function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

const get = <T,>(path: string) => request<T>(path)

export interface SoccerPredictOpts {
  knockout?: boolean
  neutral?: boolean
  defensiveDampener?: number
  applyWeather?: boolean
  applyLineups?: boolean
  missingHome?: string[]
  missingAway?: string[]
  odds?: SoccerMarketOdds | null
  venue?: string | null
}

export interface NFLPredictOpts {
  neutralSite?: boolean
  spreadLine?: number | null
  totalLine?: number | null
  applyWeather?: boolean
  applyLineups?: boolean
  missingHome?: string[]
  missingAway?: string[]
  odds?: NFLMarketOdds | null
}

export const api = {
  predictSoccer: (home: string, away: string, opts: SoccerPredictOpts = {}) =>
    post<SoccerPredictResponse>('/api/v1/predict/soccer', {
      home,
      away,
      knockout: opts.knockout ?? false,
      neutral: opts.neutral ?? true,
      defensive_dampener: opts.defensiveDampener ?? 1.0,
      apply_weather: opts.applyWeather ?? true,
      apply_lineups: opts.applyLineups ?? true,
      missing_home: opts.missingHome ?? [],
      missing_away: opts.missingAway ?? [],
      odds: opts.odds ?? null,
      venue: opts.venue ?? null,
    }),

  venues: () => get<string[]>('/api/v1/venues'),

  predictGridiron: (league: GridironLeague, home: string, away: string, opts: NFLPredictOpts = {}) =>
    post<NFLPredictResponse>(`/api/v1/predict/${league}`, {
      home,
      away,
      neutral_site: opts.neutralSite ?? false,
      spread_line: opts.spreadLine ?? null,
      total_line: opts.totalLine ?? null,
      apply_weather: opts.applyWeather ?? true,
      apply_lineups: opts.applyLineups ?? true,
      missing_home: opts.missingHome ?? [],
      missing_away: opts.missingAway ?? [],
      odds: opts.odds ?? null,
    }),

  soccerTeams: () => get<TeamInfo[]>('/api/v1/teams/soccer'),
  leagueTeams: (league: GridironLeague | 'ncaaf') =>
    get<TeamInfo[]>(`/api/v1/teams/${league}`),
  soccerRankings: () => get<RankingsResponse>('/api/v1/rankings/soccer'),
  leagueRankings: (league: GridironLeague) => get<RankingsResponse>(`/api/v1/rankings/${league}`),
  r16Fixtures: () => get<unknown[]>('/api/v1/fixtures/r16'),

  // Live data
  liveScores: () => get<AllScoreboardsOut>(`/api/v1/live/scores?_=${Date.now()}`),
  leagueScores: (league: string) => get<ScoreboardOut>(`/api/v1/live/scores/${league}`),
  /** Every live win-probability reading the server has recorded for a game. */
  winHistory: (league: string, eventId: string) =>
    get<WinHistoryOut>(
      `/api/v1/live/win-history/${league}/${encodeURIComponent(eventId)}?_=${Date.now()}`,
    ),
  // The cache-buster is not belt-and-braces: a proxy or CDN that ignores a
  // short max-age will happily serve a frozen game clock, and a unique URL is
  // the only thing that cannot be answered from a cache.
  today: (league: GridironLeague | 'ncaaf') =>
    get<TodayResponse>(`/api/v1/today/${league}?_=${Date.now()}`),
  /** Both leagues on one board, grouped by the day a game is played. The
   *  homepage asks for this instead of one league at a time. Carries live
   *  clocks, so it gets the same cache-buster as `today`. */
  board: (days = 8) =>
    get<BoardResponse>(`/api/v1/board?days=${days}&_=${Date.now()}`),
  /** The week ahead, already predicted. A schedule days out is stable, so no
   *  cache-buster here — unlike a running clock, it can safely be cached. */
  upcoming: (league: GridironLeague | 'ncaaf', days = 7) =>
    get<UpcomingResponse>(`/api/v1/upcoming/${league}?days=${days}`),
  /** One fully-modelled game — the Game Center. Scoped to a single event so
   *  the page never pays for modelling the whole slate. */
  gameDetail: (league: string, eventId: string) =>
    get<GameDetailOut>(`/api/v1/game/${league}/${encodeURIComponent(eventId)}?_=${Date.now()}`),
  playByPlay: (league: string, eventId: string) =>
    get<PlayByPlayOut>(`/api/v1/live/pbp/${league}/${encodeURIComponent(eventId)}?_=${Date.now()}`),

  // Live lineups
  lineup: (sport: 'soccer' | 'nfl' | 'cfl' | 'mlb', team: string) =>
    get<KeyPlayerOut[]>(`/api/v1/lineups/${sport}/${encodeURIComponent(team)}`),
  setPlayerStatus: (sport: 'soccer' | 'nfl' | 'cfl' | 'mlb', team: string, player: string, status: string) =>
    post<KeyPlayerOut>(`/api/v1/lineups/${sport}/${encodeURIComponent(team)}`, { player, status }),
  resetLineup: (sport: 'soccer' | 'nfl' | 'cfl' | 'mlb', team: string) =>
    request(`/api/v1/lineups/${sport}/${encodeURIComponent(team)}`, { method: 'DELETE' }),

  // Value
  bestBets: () => get<BestBetsResponse>('/api/v1/best-bets'),
  bestParlay: (maxLegs = 3) => get<BestParlayResponse>(`/api/v1/best-parlay?max_legs=${maxLegs}`),

  // Track record
  accuracy: () => get<AccuracyResponse>('/api/v1/accuracy'),

  // News — attributed headlines, never full articles
  news: (league: 'all' | FootballLeague = 'all', limit = 30) =>
    get<NewsFeedOut>(`/api/v1/news?league=${league}&limit=${limit}`),

  // Access, decided server-side
  entitlements: () => get<EntitlementsOut>('/api/v1/entitlements'),

  // Player props — reports what it would need rather than inventing lines
  propsStatus: () => get<PropsOut>('/api/v1/props'),
  gameProps: (league: string, eventId: string) =>
    get<GamePropsOut>(`/api/v1/props/${league}/${encodeURIComponent(eventId)}`),

  // ── Accounts. Session lives in an httpOnly cookie, so every one of these
  // sends credentials and none of them handles a token in JavaScript. ──
  session: () => get<SessionOut>('/api/v1/auth/me'),
  register: (body: { username: string; email: string; password: string; display_name?: string }) =>
    post<SessionOut>('/api/v1/auth/register', body),
  login: (body: { identifier: string; password: string }) =>
    post<SessionOut>('/api/v1/auth/login', body),
  logout: () => post<{ ok: boolean }>('/api/v1/auth/logout', {}),

  /** Whether Edge AI can answer on this deployment, and for this caller. */
  aiStatus: () => get<EdgeAiStatus>('/api/v1/ai/status'),

  // ── Live game chat ────────────────────────────────────────────────────────
  /** Messages after a cursor. `after=0` returns the most recent window. */
  chat: (league: string, eventId: string, after = 0) =>
    get<ChatPage>(`/api/v1/chat/${league}/${encodeURIComponent(eventId)}?after=${after}`),
  postChat: (league: string, eventId: string, text: string, reply_to?: string) =>
    post<{ message: ChatMessage }>(
      `/api/v1/chat/${league}/${encodeURIComponent(eventId)}`, { text, reply_to },
    ),
  reactChat: (league: string, eventId: string, messageId: string, emoji: string) =>
    post<{ message: ChatMessage }>(
      `/api/v1/chat/${league}/${encodeURIComponent(eventId)}/${messageId}/react`, { emoji },
    ),
  deleteChat: (league: string, eventId: string, messageId: string) =>
    request<{ message: ChatMessage }>(
      `/api/v1/chat/${league}/${encodeURIComponent(eventId)}/${messageId}`, { method: 'DELETE' },
    ),
  reportChat: (league: string, eventId: string, messageId: string, reason = '') =>
    post<{ reported: boolean; hidden: boolean; note: string }>(
      `/api/v1/chat/${league}/${encodeURIComponent(eventId)}/${messageId}/report`, { reason },
    ),
  /** Ask Edge AI. The game being viewed travels with the question so
   *  "why did we move to 64%" resolves without naming the teams. */
  askEdge: (
    question: string,
    ctx?: { league?: string; event_id?: string },
    history: EdgeAiTurn[] = [],
  ) => post<EdgeAiAnswer>('/api/v1/ai/ask', { question, ...ctx, history }),
  changePassword: (current_password: string, new_password: string) =>
    post<SessionOut & { signed_out_other_sessions: boolean }>(
      '/api/v1/auth/password', { current_password, new_password },
    ),
  /** The image is already cropped and resized by the browser. */
  uploadAvatar: (image: string) => post<SessionOut>('/api/v1/auth/avatar', { image }),
  removeAvatar: () => request<SessionOut>('/api/v1/auth/avatar', { method: 'DELETE' }),
  usernameAvailable: (username: string) =>
    get<{ username: string; available: boolean }>(
      `/api/v1/auth/username-available?username=${encodeURIComponent(username)}`),
  updateProfile: (body: Record<string, unknown>) =>
    request<SessionOut>('/api/v1/auth/profile', {
      method: 'PATCH', headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    }),

  // ── Picks ──
  submitPick: (body: SubmitPickBody) => post<PickOut>('/api/v1/picks', body),
  myPicks: () => get<MyPicksOut>('/api/v1/picks/mine'),
  withdrawPick: (id: string) =>
    request<{ ok: boolean }>(`/api/v1/picks/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  gameCommunity: (league: string, eventId: string) =>
    get<GameCommunityOut>(`/api/v1/picks/game/${league}/${encodeURIComponent(eventId)}`),
  leaderboard: (league?: string) =>
    get<LeaderboardOut>(`/api/v1/leaderboard${league ? `?league=${league}` : ''}`),
  analyst: (username: string) =>
    get<AnalystOut>(`/api/v1/analysts/${encodeURIComponent(username)}`),

  // Staff portal — the server 404s these for anyone who isn't an admin
  adminOverview: () => get<AdminOverview>('/api/v1/admin/overview'),
  adminUsers: () => get<{ count: number; users: AdminUserRow[] }>('/api/v1/admin/users'),
  adminPicks: () => get<{ count: number; picks: PickOut[] }>('/api/v1/admin/picks'),

  // World Cup spotlight (model pre-run on upcoming fixtures)
  soccerUpcoming: () => get<SoccerUpcomingResponse>('/api/v1/soccer/upcoming'),
}
