import type {
  SoccerPredictResponse,
  NFLPredictResponse,
  RankingsResponse,
  TeamInfo,
} from '../types'

const BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export const api = {
  predictSoccer: (
    home: string,
    away: string,
    opts: { knockout?: boolean; neutral?: boolean; defensiveDampener?: number } = {},
  ) =>
    post<SoccerPredictResponse>('/api/v1/predict/soccer', {
      home,
      away,
      knockout: opts.knockout ?? false,
      neutral: opts.neutral ?? true,
      defensive_dampener: opts.defensiveDampener ?? 1.0,
    }),

  predictNFL: (home: string, away: string, neutralSite = false) =>
    post<NFLPredictResponse>('/api/v1/predict/nfl', { home, away, neutral_site: neutralSite }),

  soccerTeams: () => get<TeamInfo[]>('/api/v1/teams/soccer'),
  nflTeams: () => get<TeamInfo[]>('/api/v1/teams/nfl'),
  soccerRankings: () => get<RankingsResponse>('/api/v1/rankings/soccer'),
  nflRankings: () => get<RankingsResponse>('/api/v1/rankings/nfl'),
  r16Fixtures: () => get<unknown[]>('/api/v1/fixtures/r16'),
}
