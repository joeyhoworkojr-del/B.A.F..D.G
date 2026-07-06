import type {
  SoccerPredictResponse,
  NFLPredictResponse,
  RankingsResponse,
  TeamInfo,
  KeyPlayerOut,
  SoccerMarketOdds,
  NFLMarketOdds,
  BestBetsResponse,
  AllScoreboardsOut,
  ScoreboardOut,
  TodayResponse,
  GridironLeague,
  AccuracyResponse,
  SoccerUpcomingResponse,
} from '../types'

// Strip trailing slashes so VITE_API_BASE="/" (same-origin via nginx proxy)
// yields "/api/v1/..." and not a protocol-relative "//api/v1/..." URL.
const BASE = (import.meta.env.VITE_API_BASE ?? 'http://localhost:8000').replace(/\/+$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
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
  leagueTeams: (league: GridironLeague) => get<TeamInfo[]>(`/api/v1/teams/${league}`),
  soccerRankings: () => get<RankingsResponse>('/api/v1/rankings/soccer'),
  leagueRankings: (league: GridironLeague) => get<RankingsResponse>(`/api/v1/rankings/${league}`),
  r16Fixtures: () => get<unknown[]>('/api/v1/fixtures/r16'),

  // Live data
  liveScores: () => get<AllScoreboardsOut>('/api/v1/live/scores'),
  leagueScores: (league: string) => get<ScoreboardOut>(`/api/v1/live/scores/${league}`),
  today: (league: GridironLeague) => get<TodayResponse>(`/api/v1/today/${league}`),

  // Live lineups
  lineup: (sport: 'soccer' | 'nfl' | 'cfl' | 'mlb', team: string) =>
    get<KeyPlayerOut[]>(`/api/v1/lineups/${sport}/${encodeURIComponent(team)}`),
  setPlayerStatus: (sport: 'soccer' | 'nfl' | 'cfl' | 'mlb', team: string, player: string, status: string) =>
    post<KeyPlayerOut>(`/api/v1/lineups/${sport}/${encodeURIComponent(team)}`, { player, status }),
  resetLineup: (sport: 'soccer' | 'nfl' | 'cfl' | 'mlb', team: string) =>
    request(`/api/v1/lineups/${sport}/${encodeURIComponent(team)}`, { method: 'DELETE' }),

  // Value
  bestBets: () => get<BestBetsResponse>('/api/v1/best-bets'),

  // Track record
  accuracy: () => get<AccuracyResponse>('/api/v1/accuracy'),

  // World Cup spotlight (model pre-run on upcoming fixtures)
  soccerUpcoming: () => get<SoccerUpcomingResponse>('/api/v1/soccer/upcoming'),
}
