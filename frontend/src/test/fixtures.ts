import type {
  BoardEntry, BoardResponse, FootballLeague,
  GameDetailOut, LiveGameOut, MarketOut, TodayResponse,
} from '../types'

export const pregameGame: LiveGameOut = {
  league: 'ncaaf', event_id: '401752',
  home: 'Florida State', away: 'Clemson',
  home_abbr: 'FSU', away_abbr: 'CLEM',
  home_score: null, away_score: null,
  state: 'pre', detail: 'Sat 3:30 PM',
  kickoff: new Date(Date.now() + 3 * 3600_000).toISOString(),
  market_spread: 3, market_over_under: 52.5,
  market_home_ml: 130, market_away_ml: -155,
  market_details: 'CLEM -3', market_provider: 'ESPN BET',
}

export const liveGame: LiveGameOut = {
  ...pregameGame,
  state: 'in', home_score: 14, away_score: 10,
  period: 3, clock: '6:59', detail: 'Q3 6:59',
  possession_abbr: 'FSU', down_distance: '1st & 10 at FSU 42',
  yard_line: 42, down: 1, distance: 10,
  last_play: 'Rush for 6 yards',
}

export const spreadMarket: MarketOut = {
  key: 'spread', label: 'Spread', question: 'Who covers the point spread?',
  probability_kind: 'cover', line: 3, source: 'ESPN BET', assumed_price: true,
  selections: [
    { label: 'CLEM -3.0', side: 'away', model_prob: 0.34, model_prob_raw: 0.30,
      book_prob: 0.502, price_american: -110, price_decimal: 1.909,
      fair_price_american: 194, edge_pp: -16.2, ev_per_unit: -0.35, grade: '-' },
    { label: 'FSU +3.0', side: 'home', model_prob: 0.66, model_prob_raw: 0.70,
      book_prob: 0.502, price_american: -110, price_decimal: 1.909,
      fair_price_american: -194, edge_pp: 15.8, ev_per_unit: 0.26, grade: 'A' },
  ],
}

export const moneylineMarket: MarketOut = {
  key: 'moneyline', label: 'Moneyline', question: 'Who wins the game outright?',
  probability_kind: 'win', line: null, source: 'ESPN BET', assumed_price: false,
  selections: [
    { label: 'CLEM ML', side: 'away', model_prob: 0.44, model_prob_raw: 0.42,
      book_prob: 0.58, crowd_prob: 0.56, price_american: -155, price_decimal: 1.645,
      fair_price_american: 127, edge_pp: -14.0, ev_per_unit: -0.27, grade: '-' },
    { label: 'FSU ML', side: 'home', model_prob: 0.56, model_prob_raw: 0.58,
      book_prob: 0.42, crowd_prob: 0.44, price_american: 130, price_decimal: 2.3,
      fair_price_american: -127, edge_pp: 14.0, ev_per_unit: 0.29, grade: 'A' },
  ],
}

export const totalMarket: MarketOut = {
  key: 'total', label: 'Total', question: 'Do both teams combine for more or fewer than 52.5 points?',
  probability_kind: 'total', line: 52.5, source: 'ESPN BET', assumed_price: true,
  selections: [
    { label: 'Over 52.5', side: 'over', model_prob: 0.55, model_prob_raw: 0.57,
      book_prob: 0.5, price_american: -110, price_decimal: 1.909,
      fair_price_american: -122, edge_pp: 5.0, ev_per_unit: 0.05, grade: 'B' },
    { label: 'Under 52.5', side: 'under', model_prob: 0.45, model_prob_raw: 0.43,
      book_prob: 0.5, price_american: -110, price_decimal: 1.909,
      fair_price_american: 122, edge_pp: -5.0, ev_per_unit: -0.14, grade: '-' },
  ],
}

export const gradeScale = [
  { grade: 'A', min_edge_pp: 6.0, label: 'Strong' },
  { grade: 'B', min_edge_pp: 3.5, label: 'Solid' },
  { grade: 'C', min_edge_pp: 1.5, label: 'Slight' },
  { grade: '-', min_edge_pp: 0.0, label: 'No edge' },
]

export function gameDetail(overrides: Partial<GameDetailOut> = {}): GameDetailOut {
  return {
    league: 'ncaaf', event_id: '401752', status: 'pre',
    fetched_at: new Date().toISOString(), source_ok: true, source: 'ESPN BET',
    model_version: '2026.09.1-gridiron', grade_scale: gradeScale,
    game: pregameGame, mapped: true,
    model: {
      home_win_prob: 0.58, away_win_prob: 0.42,
      calibrated_home_win: 0.56, calibrated_away_win: 0.44, market_anchored: true,
      home_expected: 27.4, away_expected: 24.9,
      proj_home_score: 27.4, proj_away_score: 24.9,
      total_estimate: 52.3, over_prob: 0.57, under_prob: 0.43,
      home_cover_prob: 0.70, total_line: 52.5, conditions: [], live: false,
    },
    edges: [],
    markets: [moneylineMarket, spreadMarket, totalMarket],
    best_edge: {
      ...spreadMarket.selections[1],
      market_key: 'spread', market_label: 'Spread', line: 3,
      source: 'ESPN BET', assumed_price: true, probability_kind: 'cover',
    },
    polymarket: null, snapshot: null,
    ...overrides,
  }
}


/** A minimal today-board response for the homepage. */
export function todayBoard(league = 'ncaaf'): TodayResponse {
  const detail = gameDetail()
  return {
    league,
    fetched_at: new Date().toISOString(),
    source_ok: true,
    market_source: 'ESPN BET',
    games: [{
      game: { ...pregameGame, league },
      mapped: true,
      model: detail.model,
      edges: [],
      polymarket: null,
    }],
  }
}


/** One entry on the merged board. */
export function boardEntry(
  league: FootballLeague,
  overrides: Partial<LiveGameOut> = {},
): BoardEntry {
  const detail = gameDetail()
  return {
    league,
    projected: true,
    game: { ...pregameGame, league, ...overrides },
    mapped: true,
    model: detail.model,
    edges: [],
    polymarket: null,
  }
}

/**
 * A merged board across both leagues.
 *
 * The default has today empty and tomorrow carrying both an NFL and a college
 * game, which is the case the homepage exists to handle: a midweek visitor
 * should see the next day that has football on it rather than an empty board.
 */
export function mergedBoard(days: BoardResponse['days'] | null = null): BoardResponse {
  const list = days ?? [{
    date: '2026-09-10',
    label: 'Tomorrow',
    games: [
      boardEntry('nfl', { event_id: 'n1', home: 'Chiefs', away: 'Ravens', home_abbr: 'KC', away_abbr: 'BAL' }),
      boardEntry('ncaaf', { event_id: 'c1' }),
    ],
    live: 0,
    by_league: { nfl: 1, ncaaf: 1 },
  }]
  return {
    days: list,
    live_count: list.reduce((n, d) => n + d.live, 0),
    total_games: list.reduce((n, d) => n + d.games.length, 0),
    predicted: list.reduce((n, d) => n + d.games.length, 0),
    leagues: ['nfl', 'ncaaf'],
    source_ok: true,
    fetched_at: new Date().toISOString(),
    market_source: 'ESPN BET',
    note: '',
  }
}
