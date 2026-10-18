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
  /**
   * Expected value on a one-unit stake on this leg alone, and what the price
   * alone needs. Legs are chosen by EV: for independent legs the ticket's
   * return is the product of each leg's price times its probability, so the
   * highest-EV legs give the highest-EV ticket. A wide probability gap at a
   * bad price is not value.
   */
  ev_per_unit?: number
  break_even_prob?: number
}

/** One ticket at one leg count, priced end to end. */
export interface ParlayTicket {
  leg_count: number
  legs: ParlayLeg[]
  model_prob: number
  decimal_odds: number
  american_odds: number
  implied_prob: number
  edge_pp: number
  ev_per_unit: number
  payout_per_unit: number
  /** The book's hold on this ticket. It grows with every leg added. */
  vig_pct?: number
  /** The fair price this ticket's own no-vig legs imply. */
  fair_decimal_odds?: number
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
  /** One ticket per leg count, so the cost of a leg is visible. */
  tickets?: ParlayTicket[]
  independence_note?: string
  vig_note?: string
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
  /** Yards from the possessing team's own goal line, 0-100; null when the feed omits it. */
  yard_line?: number | null
  down?: number | null
  distance?: number | null
  last_play?: string
  /** Overall record as the feed words it ("2-1"). Empty when it has none. */
  home_record?: string
  away_record?: string
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
  /** Ball position either side of the play, yards from the offence's own goal.
   *  Absent whenever the feed did not publish it — the play then renders as
   *  text rather than being drawn somewhere it was not. */
  start_yard_line?: number | null
  end_yard_line?: number | null
  yards_gained?: number | null
  down?: number | null
  distance?: number | null
  drive_id?: string
  drive_description?: string
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

/**
 * A game where the model's own read disagrees with the market about the
 * winner, by more than a coin flip. Absent when they agree, when no line is
 * posted, or when the disagreement is too slight to be worth saying.
 */
export interface UpsetOut {
  side: 'home' | 'away'
  team: string
  /** What the model gives this underdog, in this game, before market anchoring. */
  model_prob: number
  /** What the market gives the same side. */
  market_prob: number
  /** How the RULE has done across many games. Never a claim about this one. */
  rule_hit_rate: number
  /** How often market underdogs win in general, for comparison. */
  rule_base_rate: number
}
/**
 * The model's read on a game in progress.
 *
 * `market_repriced` is the load-bearing field. A sportsbook feed does not
 * necessarily reprice in play, and comparing a live model against a pre-game
 * price manufactures an enormous edge out of a stale number — so a read is
 * only ever presented as a pick when the book has demonstrably followed the
 * game. `model_move_pp` and `market_move_pp` are how that was decided.
 *
 * `graded` is always false: in-game probabilities are recalculated from the
 * score and clock, never snapshotted, and never graded. They are no part of
 * the track record and must not be shown as if they were.
 */
export interface LiveReadOut {
  team: string
  side: 'home' | 'away'
  model_prob: number
  market_prob: number
  edge_pp: number
  market_repriced: boolean
  actionable: boolean
  model_move_pp: number | null
  market_move_pp: number | null
  note: string
  graded: boolean
}

/**
 * Which team the model expects to win the game, spread aside.
 *
 * A different question from the cover, and the two disagree often: a 9-point
 * favourite the model makes 7 still wins outright, while the spread pick is
 * the underdog. Nothing here is a wager — a probability, the published price
 * beside it where there is one, and whether the market names the same side.
 *
 * `live` marks a call recalculated from the score and clock. Those are never
 * snapshotted and never graded, so `graded` is false for them and the page
 * must not show them as part of the record.
 */
export interface WinnerOut {
  side: 'home' | 'away'
  team: string
  abbr: string
  opponent: string
  win_prob: number
  /** The raw model, before the market anchor. Null on a live call. */
  model_prob: number | null
  market_prob: number | null
  /** True when market_prob was converted from the spread, not a quoted price. */
  market_prob_is_implied: boolean
  price_american: number | null
  market_agrees: boolean | null
  band: 'toss-up' | 'lean' | 'clear' | 'strong'
  live: boolean
  graded: boolean
}

export interface TodayModelOut {
  /** Present only while a game is in progress. */
  live_read?: LiveReadOut | null
  /** Present only when the model disagrees with the market on the winner. */
  upset?: UpsetOut | null
  /** Who wins the game outright. Absent once the game is over. */
  winner?: WinnerOut | null
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
  /** Points the drive in progress is worth over an ordinary possession. */
  drive_value?: number
  /** Plain-language reason the projection moved, or '' when there is none. */
  drive_note?: string
  /** False when the feed published no field position and the projection is
   *  the scoreboard-and-clock model. The two are different claims. */
  state_aware?: boolean
  red_zone?: boolean
  goal_to_go?: boolean
}

export interface WinPoint {
  at: string
  home_win: number
  home_score: number
  away_score: number
  period?: number | null
  clock: string
  possession: string
  note: string
  scored: boolean
}

export interface WinHistoryOut {
  league: string
  event_id: string
  points: WinPoint[]
  swing: {
    opened_at: string
    opening_home_win: number
    current_home_win: number
    change: number
    readings: number
    high: number
    low: number
  } | null
  note: string
  fetched_at: string
}

export interface PolymarketOut {
  home_prob: number
  away_prob: number
  volume_usd: number
  url: string
  title: string
}


/**
 * StatEdge's own line against the book's, and the gap.
 *
 * The model produces a margin (positive = home favoured); a book quotes a line
 * (negative = home laying points). `fair` is already in the book's convention,
 * so the two can be shown side by side without a reader having to flip a sign.
 *
 * `edge_points` is signed on the home team: positive means the market is
 * giving more points on the home side than the model thinks it should.
 * `side`/`points` are the same thing said as "whose, and how many".
 */
export interface SpreadValueOut {
  fair: number
  /** Already written as a bettor reads it, e.g. "BUF -4.8". */
  fair_label: string
  market: number | null
  market_label: string
  edge_points: number | null
  side: 'home' | 'away' | null
  side_abbr: string
  points: number | null
}

export interface TotalValueOut {
  fair: number
  market: number | null
  edge_points: number | null
  side: 'over' | 'under' | null
  points: number | null
}

/**
 * How much of the model's input this game had — deliberately NOT a probability.
 *
 * "High confidence" must never be readable as "high chance of winning". Every
 * input is named with whether it was there and where it came from, so the
 * level can be audited rather than taken on trust.
 */
export interface ConfidenceOut {
  level: 'low' | 'medium' | 'high'
  inputs_present: number
  inputs_total: number
  inputs: { name: string; present: boolean; note: string }[]
  means: string
}

export interface ValueOut {
  spread: SpreadValueOut
  total: TotalValueOut
  confidence: ConfidenceOut
}

/** One input the model read, with the points it moved where it moved any. */
export interface WhyReasonOut {
  label: string
  detail: string
  impact_points: number | null
  source: 'ratings' | 'weather' | 'lineup' | 'line' | 'anchor' | 'missing' | string
}

export interface LineStateOut {
  opening: number | null
  current: number | null
  moved_points: number | null
  state: 'value' | 'gone' | 'unknown'
  note: string
}

export interface WhyOut {
  fair_label: string
  side: 'home' | 'away' | null
  side_abbr: string
  points: number | null
  line: LineStateOut
  reasons: WhyReasonOut[]
  basis: string
}

export interface TodayGameOut {
  game: LiveGameOut
  mapped: boolean
  model?: TodayModelOut | null
  edges: EdgeOut[]
  polymarket?: PolymarketOut | null
  /** Fair line against the market line, and the input coverage behind it. */
  value?: ValueOut | null
  /** The inputs behind the number. Absent on an unprojected game. */
  why?: WhyOut | null
}

export interface TodayResponse {
  league: string
  fetched_at: string
  source_ok: boolean
  market_source: string
  games: TodayGameOut[]
}

/**
 * The week-ahead board. `truncated` is part of the contract: a capped
 * response is a partial answer, and the page says so rather than presenting
 * an incomplete slate as the whole schedule.
 */
export interface UpcomingResponse {
  league: string
  days: number
  fetched_at: string
  source_ok: boolean
  total_scheduled: number
  predicted: number
  truncated: boolean
  market_source: string
  games: TodayGameOut[]
}

/**
 * One board across both leagues, grouped by the day a game is played.
 *
 * The homepage asks for this rather than for NFL and college separately: a
 * Wednesday in September has one NFL game and no college football, and two
 * tabs where one is empty makes the reader guess which. `projected` marks the
 * games carrying a full model run — beyond the server's cap a game still
 * appears with its teams, kickoff and line rather than being dropped.
 */
export interface BoardEntry extends TodayGameOut {
  league: FootballLeague
  projected: boolean
}

export interface BoardDay {
  /** ET calendar day, `YYYY-MM-DD`. The day a game is played, not UTC. */
  date: string
  /** "Today", "Tomorrow", or a weekday and date. */
  label: string
  games: BoardEntry[]
  live: number
  by_league: Record<string, number>
}

export interface BoardResponse {
  days: BoardDay[]
  live_count: number
  total_games: number
  predicted: number
  leagues: string[]
  source_ok: boolean
  fetched_at: string
  market_source: string
  /** Non-empty only when there is genuinely nothing scheduled in the window. */
  note: string
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

/**
 * One side of one market, with every number that decides whether it is worth
 * taking kept separate.
 *
 * `model_prob`, `break_even_prob`, `ev_per_unit` and `confidence` are four
 * different things and are never blended into one score. `break_even_prob` is
 * a property of the price alone; `confidence` is how much of the model's input
 * was available for the game, not how likely the pick is to win.
 *
 * `assumed_price` is load-bearing: ESPN publishes spread and total lines with
 * no price attached, so those are priced at the standard -110 and the EV is
 * only as good as that assumption. Presenting it as a quoted price would be
 * inventing a number a book never offered.
 */
export interface EdgeRow {
  league: FootballLeague
  event_id: string
  kickoff: string
  home: string
  away: string
  home_abbr: string
  away_abbr: string
  market: 'moneyline' | 'spread' | 'total'
  market_label: string
  line: number | null
  selection: string
  side: string
  price_american: number
  assumed_price: boolean
  model_prob: number
  break_even_prob: number | null
  ev_per_unit: number
  edge_pp: number | null
  grade: string
  /** StatEdge's own fair spread for the game, e.g. "BUF -4.8". */
  fair_label: string
  market_label_spread: string
  /** Points of disagreement on this side, where the market quotes a line. */
  edge_points: number | null
  confidence: 'low' | 'medium' | 'high'
  source: string
  why: string[]
}

export interface EdgesResponse {
  edges: EdgeRow[]
  total_matching: number
  scanned: number
  filters: {
    league: string
    market: string
    min_ev: number
    confidence: string
    hours: number
    limit: number
  }
  leagues: string[]
  markets: string[]
  source_ok: boolean
  market_source: string
  fetched_at: string
  note: string
  ranking: string
}

export interface PerformanceOut {
  total_picks: number
  wins?: number
  losses?: number
  win_rate?: number | null
  /** How many graded picks had a book price, and so could be priced for ROI. */
  priced_picks?: number
  avg_edge_pp?: number | null
  profit_units?: number | null
  roi_pct?: number | null
  series: number[]
  /** Spread record, graded against the line the pick was made at. */
  ats?: BetRecord
  /** Over/under record, graded the same way. */
  totals?: BetRecord
  /** Average points by which the recommended line beat the close. */
  avg_clv_points?: number | null
  /** How many graded picks have both an opening and a closing line on file. */
  clv_tracked?: number
  clv_beat_close?: number
}

/** A win/loss/push record where a push is out of the denominator, not a loss. */
export interface BetRecord {
  wins: number
  losses: number
  pushes: number
  win_rate: number | null
  graded: number
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
  /**
   * True when the ledger could not be read at all.
   *
   * An empty scorecard and an unreadable one are identical on the wire, and
   * only one of them is a claim about how the model has done. The page must
   * not present the second as the first.
   */
  unavailable?: boolean
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
  /** Fair line against the market line, and the input coverage behind it. */
  value?: ValueOut | null
  /** The inputs the number came from. */
  why?: WhyOut | null
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
  /** The average over the recent window, where there was one to take. */
  recent_avg?: number | null
  /** How much weight recent form took off the season average, 0 to ~0.45. */
  form_weight?: number
  environment_mult?: number
  opponent_abbr?: string
  opponent_mult?: number
  opponent_note?: string
  /**
   * The spread the over/under probability comes out of, and where it came
   * from. "player" means this athlete's own game-to-game variation carried
   * most of the weight; "market" means the log was too short and the
   * league-wide prior for the market stood. Two players with the same average
   * and different spreads are not the same bet.
   */
  sigma?: number | null
  sigma_source?: 'player' | 'market' | 'none'
  sigma_games?: number
  /** Oldest first. The evidence behind everything above. */
  game_log?: { season: number; week: number; opponent: string; value: number }[]
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
  spread_note?: string
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

/** Staff powers, checked again server-side on every request. */
export type StaffPower = 'view_staff' | 'manage_users' | 'moderate' | 'configure'

export interface AccountEntitlements {
  level: AccountLevel
  /** What this account may do. Empty for everyone who is not staff. */
  powers?: StaffPower[]
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
  /** Only issued on register/login, for clients behind a cookie-stripping proxy. */
  session_token?: string
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

// ─── Leaderboard ──────────────────────────────────────────────────────────────

export interface Standing {
  user_id: string
  username: string
  display_name: string
  avatar_url: string
  badges: string[]
  edge_rating: number
  provisional: boolean
  graded: number
  wins: number
  losses: number
  pushes: number
  win_rate?: number | null
  units: number
  roi_pct?: number | null
  rank?: number
  of?: number
}

export interface LeaderboardOut {
  league: string
  min_graded: number
  count: number
  standings: Standing[]
  note: string
}

// ─── Staff portal ─────────────────────────────────────────────────────────────

export interface AdminOverview {
  storage: { backend: string; durable: boolean }
  accounts: {
    total: number; onboarded: number; founding: number
    by_level: Record<string, number>
  }
  picks: {
    total: number; open: number; graded: number
    by_market: Record<string, number>
    by_result: Record<string, number>
    by_league: Record<string, number>
  }
  model_record: { graded: number; pending: number }
  leaderboard_size: number
  data_feeds?: {
    nflverse: FeedStatus
    cfbd: FeedStatus
    model_priors: ModelPriorStatus
  }
}

/**
 * A provider's health. `configured` and `last_success` are separate on
 * purpose: a key that is set but rejected is configured and not working, and
 * collapsing the two would hide exactly the failure worth seeing.
 */
export interface FeedStatus {
  provider: string
  requires_key: boolean
  configured: boolean
  leagues: string[]
  note?: string
  key_env_var?: string
  last_success?: string
  last_error?: string
  cached_datasets?: number
  loaded?: { season: number | null; players: number; teams: number; fetched_at: string }[]
  used_for?: string
}

export interface ModelPriorStatus {
  max_shift_points: number
  leagues: Record<string, {
    ok: boolean; source: string; teams: number; note: string; fetched_at: string
  }>
}

export interface AdminUserRow {
  id: string
  username: string
  email: string
  display_name: string
  level: string
  badges: string[]
  onboarded: boolean
  created_at: string
  picks: number
}


// ─── Edge AI ──────────────────────────────────────────────────────────────────

export interface EdgeAiStatus {
  available: boolean
  signed_in: boolean
  may_ask: boolean
  /** Why not, when may_ask is false. Shown to the user verbatim. */
  reason: string
  rate_limit_per_hour: number
  level: string
  model: string
  tools: string[]
  /**
   * The provider's own last failure, scrubbed of anything key-shaped by the
   * server. Empty when nothing has failed. Surfaced under a failed answer
   * because "temporarily unreachable" with no detail leaves no way to tell a
   * five-minute blip from a misconfiguration nobody has noticed for a week.
   */
  last_error?: string
  budget?: {
    within_budget: boolean
    spent_usd: number
    daily_limit_usd: number
  }
}

export interface EdgeAiAnswer {
  answer: string
  /** Which StatEdge lookups the answer rests on. */
  sources_used: string[]
  truncated: boolean
  questions_remaining_this_hour: number
}

export interface EdgeAiTurn {
  role: 'user' | 'assistant'
  content: string
}


// ─── Live game chat ───────────────────────────────────────────────────────────

export interface ChatMessage {
  id: string
  seq: number
  user_id: string
  username: string
  display_name: string
  avatar_url: string
  text: string
  created_at: string
  system: boolean
  reply_to?: string | null
  reply_preview: string
  reactions: Record<string, number>
  deleted: boolean
  hidden: boolean
  /** True when the viewer wrote it. Decided by the server, not the client. */
  mine: boolean
}

export interface ChatPage {
  game_id: string
  messages: ChatMessage[]
  cursor: number
  count: number
  signed_in: boolean
  may_post: boolean
  /** Why not, when may_post is false. Shown verbatim. */
  blocked_reason: string
  reactions_available: string[]
}
