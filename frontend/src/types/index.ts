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
