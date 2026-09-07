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
  source: 'weather' | 'lineup' | 'altitude'
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
  league: string
  event_id: string
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

export interface ParlayLeg {
  fixture_id: string
  league: string
  kickoff: string
  home: string
  away: string
  market: string
  selection: string
  model_prob: number
  market_prob: number
  decimal_odds: number
  edge_pp: number
  rating: string
}

export interface BestParlayResponse {
  generated_with: string
  legs: ParlayLeg[]
  leg_count: number
  model_prob: number
  decimal_odds: number
  american_odds: number
  implied_prob: number
  edge_pp: number
  ev_per_unit: number
  payout_per_unit: number
  pool: ParlayLeg[]
}

export interface BestBetsResponse {
  generated_with: string
  bets: BestBetOut[]
}

// ─── Live scoreboards + Today ─────────────────────────────────────────────────

export interface LiveGameOut {
  league: string
  event_id: string
  home: string
  away: string
  home_abbr: string
  away_abbr: string
  home_score?: number | null
  away_score?: number | null
  state: 'pre' | 'in' | 'post'
  detail: string
  kickoff: string
  period?: number | null
  clock?: string
  down_distance?: string
  possession_abbr?: string
  is_red_zone?: boolean
  last_play?: string
  home_logo?: string
  away_logo?: string
  market_spread?: number | null
  market_over_under?: number | null
  market_home_ml?: number | null
  market_away_ml?: number | null
  market_details: string
  market_provider: string
}

export interface PlayOut {
  period?: number | null
  clock?: string
  text: string
  team_abbr?: string
  scoring?: boolean
  home_score?: number | null
  away_score?: number | null
}

export interface PlayByPlayOut {
  league: string
  event_id: string
  ok: boolean
  plays: PlayOut[]
  fetched_at: string
}

export interface ScoreboardOut {
  league: string
  games: LiveGameOut[]
  fetched_at: string
  source: string
  ok: boolean
}

export interface AllScoreboardsOut {
  boards: Record<string, ScoreboardOut>
  fetched_at: string
}

export interface TodayModelOut {
  home_win_prob: number
  away_win_prob: number
  calibrated_home_win?: number
  calibrated_away_win?: number
  market_anchored?: boolean
  home_expected: number
  away_expected: number
  proj_home_score?: number
  proj_away_score?: number
  total_estimate: number
  over_prob: number
  under_prob: number
  home_cover_prob: number
  total_line?: number | null
  conditions: AdjustmentOut[]
  live?: boolean
  live_home_win?: number
  live_away_win?: number
  live_proj_home?: number
  live_proj_away?: number
  time_remaining_pct?: number
}

export interface PolymarketOut {
  home_prob: number
  away_prob: number
  volume_usd: number
  url: string
  title: string
}

export interface TodayGameOut {
  game: LiveGameOut
  mapped: boolean
  model?: TodayModelOut | null
  edges: EdgeOut[]
  polymarket?: PolymarketOut | null
}

export interface TodayResponse {
  league: string
  fetched_at: string
  source_ok: boolean
  market_source: string
  games: TodayGameOut[]
}

export type GridironLeague = 'nfl' | 'cfl' | 'mlb'
export type FootballLeague = 'nfl' | 'ncaaf'

// ─── World Cup spotlight ──────────────────────────────────────────────────────

export interface SoccerUpcomingGame {
  id: string
  kickoff: string
  state: 'pre' | 'in' | 'post'
  detail: string
  home: { code: string; name: string; flag: string }
  away: { code: string; name: string; flag: string }
  home_score?: number | null
  away_score?: number | null
  home_win: number
  draw: number
  away_win: number
  expected_scoreline: [number, number]
  over_2_5: number
}

export interface SoccerUpcomingResponse {
  generated_with: string
  games: SoccerUpcomingGame[]
}

// ─── Track record ─────────────────────────────────────────────────────────────

export interface SignalScore {
  n: number
  brier: number
  winner_hit_rate: number
}

export interface AccuracyBucket {
  games_graded: number
  model?: SignalScore | null
  book?: SignalScore | null
  crowd?: SignalScore | null
}

export interface PerformanceOut {
  total_picks: number
  win_rate?: number | null
  avg_edge_pp?: number | null
  profit_units?: number | null
  roi_pct?: number | null
  series: number[]
}

export interface GradedRow {
  event_id: string
  league: string
  kickoff: string
  home: string
  away: string
  model_home_prob: number
  book_home_prob?: number | null
  crowd_home_prob?: number | null
  home_score: number
  away_score: number
  home_won: number
  graded_at: string
}

export interface AccuracyResponse {
  overall: AccuracyBucket
  by_league: Record<string, AccuracyBucket>
  pending: number
  note: string
  /** Everything graded here is a frozen pre-game snapshot. */
  scope?: 'pregame'
  live_record_available?: boolean
  live_note?: string
  model_versions?: string[]
  /** "sqlite" or "postgres". */
  storage_backend?: string
  /** False when the record does not survive a deploy. */
  storage_durable?: boolean
  performance: PerformanceOut
  recent: GradedRow[]
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

// ─── Game Center contract (GET /api/v1/game/{league}/{eventId}) ──────────────

/** Which question a market answers — so win / cover / total can never be
 *  confused with one another in the UI. */
export type ProbabilityKind = 'win' | 'cover' | 'total'
export type MarketKey = 'moneyline' | 'spread' | 'total'

export interface MarketSelectionOut {
  label: string
  side: 'home' | 'away' | 'over' | 'under'
  model_prob: number
  model_prob_raw: number
  book_prob?: number | null
  crowd_prob?: number | null
  price_american: number
  price_decimal?: number | null
  fair_price_american?: number | null
  edge_pp?: number | null
  ev_per_unit?: number | null
  grade: string
}

export interface MarketOut {
  key: MarketKey
  label: string
  question: string
  probability_kind: ProbabilityKind
  line?: number | null
  source: string
  /** True when the price is our -110 assumption, not a quoted price. */
  assumed_price: boolean
  selections: MarketSelectionOut[]
}

export interface BestEdgeOut extends MarketSelectionOut {
  market_key: MarketKey
  market_label: string
  line?: number | null
  source: string
  assumed_price: boolean
  probability_kind: ProbabilityKind
}

export interface GradeBand {
  grade: string
  min_edge_pp: number
  label: string
}

/** The frozen pre-game prediction, as stored by the scheduled snapshot job. */
export interface SnapshotOut {
  event_id: string
  model_version?: string | null
  book_source?: string | null
  snapshot_at?: string | null
  model_home_prob?: number | null
  consensus_home_prob?: number | null
  book_home_prob?: number | null
  market_spread?: number | null
  market_total?: number | null
  closing_spread?: number | null
  closing_total?: number | null
  closing_home_prob?: number | null
  graded?: number | null
  home_score?: number | null
  away_score?: number | null
  home_won?: number | null
}

export interface GameDetailOut {
  league: string
  event_id: string
  status: 'pre' | 'in' | 'post'
  fetched_at: string
  source_ok: boolean
  source: string
  model_version: string
  grade_scale: GradeBand[]
  game: LiveGameOut
  mapped: boolean
  model?: TodayModelOut | null
  edges: EdgeOut[]
  markets: MarketOut[]
  best_edge?: BestEdgeOut | null
  polymarket?: PolymarketOut | null
  snapshot?: SnapshotOut | null
}

// ─── News ─────────────────────────────────────────────────────────────────────

export type NewsCategory = 'news' | 'injury' | 'preview' | 'recap'

export interface NewsItemOut {
  league: string
  id: string
  headline: string
  description: string
  published: string
  byline: string
  url: string
  image: string
  category: NewsCategory
  teams: string[]
  source: string
  /** The model does not read these stories. Never claim otherwise. */
  reflected_in_projection: boolean
}

export interface NewsFeedOut {
  league: string
  items: NewsItemOut[]
  fetched_at: string
  ok: boolean
  source: string
  attribution: string
}

// ─── Entitlements ─────────────────────────────────────────────────────────────

export type FeatureKey =
  | 'line_movement_history'
  | 'model_internals'
  | 'alerts'
  | 'player_props'
  | 'saved_games'

export interface EntitlementsOut {
  plan: string
  authenticated: boolean
  auth_configured: boolean
  features: Record<string, boolean>
  unavailable_reason: Record<string, string>
  billing_enabled: boolean
  note: string
}

// ─── Player props (unavailable until a provider is configured) ────────────────

export interface PropsOut {
  available: boolean
  lines_available: boolean
  league: string
  event_id: string
  props: unknown[]
  reason: string
  requires: string[]
}

// ─── Player prop projections ──────────────────────────────────────────────────

export interface PropProjectionOut {
  athlete_id: string
  player: string
  team_abbr: string
  position: string
  market: string
  label: string
  projection: number
  season_avg: number
  games_played: number
  /** True once the game is under way: this is what happened, not a forecast. */
  actual: boolean
}

export interface GamePropsOut {
  league: string
  event_id: string
  status: 'pre' | 'in' | 'post'
  home: string
  away: string
  home_abbr: string
  away_abbr: string
  fetched_at: string
  source: string
  source_ok: boolean
  model_version: string
  projected_home_points?: number | null
  projected_away_points?: number | null
  lines_available: boolean
  lines_note: string
  projections: PropProjectionOut[]
  note: string
}

// ─── Accounts ─────────────────────────────────────────────────────────────────

export type AccountLevel = 'guest' | 'beta' | 'free' | 'pro' | 'admin'

export interface PublicProfile {
  id: string
  username: string
  display_name: string
  bio: string
  avatar_url: string
  favourite_sports: string[]
  favourite_teams: string[]
  badges: string[]
  created_at: string
}

export interface PrivateProfile extends PublicProfile {
  email: string
  email_verified: boolean
  level: AccountLevel
  interests: string[]
  onboarded: boolean
  profile_public: boolean
  auth_provider: string
}

export interface AccountEntitlements {
  level: AccountLevel
  authenticated: boolean
  beta_open: boolean
  features: Record<string, boolean>
  unavailable_reason: Record<string, string>
  billing_enabled: boolean
  note: string
}

export interface SessionOut {
  user: PrivateProfile | null
  entitlements: AccountEntitlements
}

// ─── Picks ────────────────────────────────────────────────────────────────────

export type PickMarket = 'moneyline' | 'spread' | 'total'
export type PickSide = 'home' | 'away' | 'over' | 'under'
export type PickResult = 'pending' | 'live' | 'win' | 'loss' | 'push' | 'void'

export interface PickOut {
  id: string
  user_id: string
  username: string
  game_id: string
  league: string
  event_id: string
  home: string
  away: string
  market: PickMarket
  side: PickSide
  selection: string
  line?: number | null
  price_american?: number | null
  odds_source: string
  confidence: number
  reasoning: string
  kickoff: string
  created_at: string
  updated_at: string
  result: PickResult
  units: number
  graded_at: string
  final_home?: number | null
  final_away?: number | null
  locked: boolean
  graded: boolean
}

export interface PickRecord {
  picks: number
  pending: number
  graded: number
  wins: number
  losses: number
  pushes: number
  win_rate?: number | null
  units: number
  roi_pct?: number | null
  avg_confidence?: number | null
}

export interface MyPicksOut {
  record: PickRecord
  picks: PickOut[]
}

export interface GameCommunityOut {
  game_id: string
  total_picks: number
  moneyline_split: Record<string, number>
  recent_analysis: {
    username: string
    selection: string
    confidence: number
    reasoning: string
    market: string
    created_at: string
    result: PickResult
  }[]
  your_picks: PickOut[]
}

export interface AnalystOut {
  profile: PublicProfile
  record: PickRecord
  picks: PickOut[]
}

export interface SubmitPickBody {
  league: string
  event_id: string
  home: string
  away: string
  kickoff: string
  market: PickMarket
  side: PickSide
  selection: string
  line?: number | null
  price_american?: number | null
  odds_source?: string
  confidence: number
  reasoning?: string
}
