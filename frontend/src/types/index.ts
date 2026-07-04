// API response types matching backend Pydantic schemas

export interface TeamInfo {
  code: string
  name: string
  flag: string
  elo: number
  group?: string
  is_host?: boolean
  conference?: string
  division?: string
}

export interface WDLProbs {
  home_win: number
  draw: number
  away_win: number
  home_xg: number
  away_xg: number
}

export interface TotalsOut {
  over_1_5: number
  under_1_5: number
  over_2_5: number
  under_2_5: number
  over_3_5: number
  under_3_5: number
  over_4_5: number
  under_4_5: number
  btts: number
  btts_no: number
  home_over_0_5: number
  home_over_1_5: number
  home_over_2_5: number
  away_over_0_5: number
  away_over_1_5: number
  away_over_2_5: number
  most_likely_total: number
  expected_scoreline: [number, number]
  over_by_line: Record<string, number>
}

export interface AdjustmentOut {
  label: string
  detail: string
  source: 'weather' | 'lineup'
  home_xg_mult: number
  away_xg_mult: number
  home_pts_delta: number
  away_pts_delta: number
}

export interface WeatherInfoOut {
  venue: string
  temperature_c: number
  wind_speed_kmh: number
  precipitation_prob: number
  condition: string
  is_indoor: boolean
}

export interface EdgeOut {
  market: string
  selection: string
  model_prob: number
  implied_prob: number
  market_prob: number
  decimal_odds: number
  fair_odds: number
  edge_pp: number
  ev_per_unit: number
  kelly_stake: number
  rating: 'A' | 'B' | 'C' | '-'
}

export interface KeyPlayerOut {
  name: string
  team: string
  sport: string
  position: string
  importance: number
  status: 'fit' | 'doubtful' | 'out'
}

export interface SoccerMarketOdds {
  format?: 'decimal' | 'american'
  home?: number | null
  draw?: number | null
  away?: number | null
  over_2_5?: number | null
  under_2_5?: number | null
}

export interface NFLMarketOdds {
  format?: 'decimal' | 'american'
  moneyline_home?: number | null
  moneyline_away?: number | null
  spread_home_price?: number | null
  spread_away_price?: number | null
  over_price?: number | null
  under_price?: number | null
}

export interface BestBetOut {
  fixture_id: string
  kickoff: string
  venue: string
  home: string
  away: string
  home_flag: string
  away_flag: string
  market: string
  selection: string
  model_prob: number
  market_prob?: number | null
  edge_pp?: number | null
  rating: string
  note: string
}

export interface BestBetsResponse {
  generated_with: string
  bets: BestBetOut[]
}

export interface PlayerPropOut {
  name: string
  team: string
  anytime_scorer: number
  two_plus_goals: number
  xg: number
}

export interface WhyFactorOut {
  label: string
  value: number
}

export interface SimOut {
  home_wins: number
  draws: number
  away_wins: number
  home_advance: number
  away_advance: number
  home_score_dist: Record<string, number>
  away_score_dist: Record<string, number>
  total_score_dist: Record<string, number>
  std_error: number
}

export interface SoccerPredictResponse {
  home_team: TeamInfo
  away_team: TeamInfo
  model_probs: WDLProbs
  blended_probs: WDLProbs
  totals: TotalsOut
  player_props: PlayerPropOut[]
  scoreline_grid: number[][]
  why_factors: WhyFactorOut[]
  simulation: SimOut
  sim_error_bound: number
  has_sr_data: boolean
  data_warning: string
  base_probs?: WDLProbs | null
  conditions: AdjustmentOut[]
  weather?: WeatherInfoOut | null
  fair_odds: Record<string, number>
  edges: EdgeOut[]
}

export interface NFLPredictResponse {
  home_team: TeamInfo
  away_team: TeamInfo
  home_win_prob: number
  away_win_prob: number
  predicted_spread: number
  home_cover_prob: number
  away_cover_prob: number
  total_points_estimate: number
  why_factors: WhyFactorOut[]
  data_warning: string
  home_expected_pts: number
  away_expected_pts: number
  total_line?: number | null
  over_prob: number
  under_prob: number
  over_by_line: Record<string, number>
  home_team_total_over: Record<string, number>
  away_team_total_over: Record<string, number>
  base_home_win_prob: number
  base_total_estimate: number
  conditions: AdjustmentOut[]
  weather?: WeatherInfoOut | null
  fair_odds: Record<string, number>
  edges: EdgeOut[]
}

export interface RankedTeam {
  rank: number
  code: string
  name: string
  flag: string
  elo: number
  group?: string
  conference?: string
}

export interface RankingsResponse {
  sport: string
  teams: RankedTeam[]
}

export interface HistoryEntry {
  id: string
  sport: string
  home_code: string
  away_code: string
  home_name: string
  away_name: string
  predicted_home_win: number
  actual_outcome: 'home' | 'draw' | 'away'
  home_goals_actual?: number
  away_goals_actual?: number
  brier_score?: number
  logged_at: string
}
