/**
 * Shared stub payloads for the offline visual/E2E harnesses.
 *
 * The sandbox cannot reach site.api.espn.com, so every screenshot and layout
 * check runs against the real built bundle with the API stubbed at the network
 * boundary. Shapes mirror backend/src/api/routes/predictions.py.
 */
const iso = () => new Date().toISOString()
const inHours = h => new Date(Date.now() + h * 3600e3).toISOString()

const mkGame = (o = {}) => ({
  league: 'ncaaf', event_id: '401752',
  home: 'Florida State', away: 'Clemson', home_abbr: 'FSU', away_abbr: 'CLEM',
  home_score: null, away_score: null, state: 'pre', detail: 'Sat 3:30 PM',
  kickoff: inHours(3),
  market_spread: 3, market_over_under: 52.5,
  market_home_ml: 130, market_away_ml: -155,
  market_details: 'CLEM -3', market_provider: 'ESPN BET',
  ...o,
})

const mkModel = (o = {}) => ({
  home_win_prob: 0.58, away_win_prob: 0.42,
  calibrated_home_win: 0.56, calibrated_away_win: 0.44, market_anchored: true,
  home_expected: 27.4, away_expected: 24.9,
  proj_home_score: 27.4, proj_away_score: 24.9, total_estimate: 52.3,
  over_prob: 0.57, under_prob: 0.43, home_cover_prob: 0.7,
  total_line: 52.5, conditions: [], live: false,
  ...o,
})

const mkEdge = (o = {}) => ({
  market: 'Spread', selection: 'FSU +3', model_prob: 0.7, implied_prob: 0.524,
  market_prob: 0.524, decimal_odds: 1.91, fair_odds: 1.43,
  edge_pp: 17.6, ev_per_unit: 0.337, kelly_stake: 0.12, rating: 'A',
  ...o,
})

const slate = [
  { g: {}, m: {}, e: [mkEdge()] },
  {
    g: {
      event_id: '401753', home: 'Georgia', away: 'Alabama',
      home_abbr: 'UGA', away_abbr: 'ALA', state: 'in',
      home_score: 17, away_score: 14, detail: '3rd 7:22',
      period: 3, clock: '7:22', down_distance: '2nd & 6 at ALA 41',
      possession_abbr: 'UGA', last_play: 'C. Beck pass complete to O. Delp for 9 yards',
      market_spread: -2.5, market_over_under: 48.5,
      market_home_ml: -135, market_away_ml: 115, market_details: 'UGA -2.5',
      kickoff: inHours(-2),
    },
    m: {
      home_win_prob: 0.66, away_win_prob: 0.34, calibrated_home_win: 0.63,
      calibrated_away_win: 0.37, home_expected: 27.9, away_expected: 24.2,
      total_estimate: 49.1, over_prob: 0.53, under_prob: 0.47,
      home_cover_prob: 0.55, total_line: 48.5, live: true,
      live_home_win: 0.71, live_away_win: 0.29, live_proj_home: 27, live_proj_away: 23,
    },
    e: [mkEdge({ selection: 'UGA -2.5', model_prob: 0.55, edge_pp: 2.6, rating: 'C' })],
  },
  {
    g: {
      event_id: '401754', home: 'Ohio State', away: 'Michigan',
      home_abbr: 'OSU', away_abbr: 'MICH', state: 'post',
      home_score: 31, away_score: 20, detail: 'Final',
      market_spread: -6.5, market_over_under: 45.5,
      market_home_ml: -260, market_away_ml: 210, market_details: 'OSU -6.5',
      kickoff: inHours(-6),
    },
    m: { home_win_prob: 0.74, away_win_prob: 0.26, home_expected: 29.8, away_expected: 21.1,
         total_estimate: 50.9, over_prob: 0.61, under_prob: 0.39, home_cover_prob: 0.58,
         total_line: 45.5 },
    e: [],
  },
  {
    g: {
      event_id: '401755', home: 'Texas', away: 'Oklahoma',
      home_abbr: 'TEX', away_abbr: 'OU', state: 'pre',
      detail: 'Sat 7:00 PM', kickoff: inHours(6),
      market_spread: -9.5, market_over_under: 55.5,
      market_home_ml: -380, market_away_ml: 300, market_details: 'TEX -9.5',
    },
    m: { home_win_prob: 0.79, away_win_prob: 0.21, home_expected: 33.1, away_expected: 23.4,
         total_estimate: 56.5, over_prob: 0.55, under_prob: 0.45, home_cover_prob: 0.52,
         total_line: 55.5 },
    e: [mkEdge({ market: 'Total', selection: 'Over 55.5', model_prob: 0.55, edge_pp: 4.2, rating: 'B' })],
  },
]

const today = league => ({
  league, fetched_at: iso(), source_ok: true, market_source: 'ESPN BET',
  games: slate.map(({ g, m, e }) => ({
    game: mkGame({ league, ...g }), mapped: true, model: mkModel(m), edges: e,
  })),
})

const accuracy = {
  overall: {
    games_graded: 128,
    model: { n: 128, brier: 0.213, winner_hit_rate: 0.664 },
    book: { n: 128, brier: 0.219, winner_hit_rate: 0.656 },
    crowd: null,
  },
  by_league: {
    ncaaf: { games_graded: 96, model: { n: 96, brier: 0.209, winner_hit_rate: 0.677 },
             book: { n: 96, brier: 0.216, winner_hit_rate: 0.667 }, crowd: null },
    nfl: { games_graded: 32, model: { n: 32, brier: 0.226, winner_hit_rate: 0.625 },
           book: { n: 32, brier: 0.228, winner_hit_rate: 0.625 }, crowd: null },
  },
  pending: 14,
  note: 'Graded from snapshots taken before kickoff.',
  performance: {
    total_picks: 128, win_rate: 0.547, avg_edge_pp: 4.1,
    profit_units: 6.4, roi_pct: 5.0,
    series: [0, 0.4, -0.3, 1.1, 0.8, 1.9, 2.4, 1.8, 3.1, 4.0, 3.6, 5.2, 6.4],
  },
  recent: Array.from({ length: 6 }, (_, i) => ({
    event_id: `4017${60 + i}`, league: i % 2 ? 'nfl' : 'ncaaf',
    kickoff: inHours(-24 * (i + 1)),
    home: ['LSU', 'Chiefs', 'Oregon', 'Bills', 'Penn State', 'Ravens'][i],
    away: ['Ole Miss', 'Broncos', 'Utah', 'Jets', 'Iowa', 'Bengals'][i],
    model_home_prob: [0.61, 0.72, 0.55, 0.68, 0.49, 0.58][i],
    book_home_prob: [0.59, 0.7, 0.57, 0.65, 0.52, 0.56][i],
    crowd_home_prob: null,
    home_score: [24, 31, 17, 27, 13, 20][i],
    away_score: [21, 17, 20, 13, 16, 23][i],
    home_won: [1, 1, 0, 1, 0, 0][i],
    graded_at: inHours(-20 * (i + 1)),
  })),
}

const bestBets = {
  generated_with: 'gridiron-2026.09.1',
  bets: slate.filter(s => s.e.length).map(({ g, e }, i) => ({
    fixture_id: g.event_id || '401752',
    league: 'ncaaf', kickoff: g.kickoff || inHours(3),
    home: g.home || 'Florida State', away: g.away || 'Clemson',
    home_flag: '', away_flag: '',
    market: e[0].market, selection: e[0].selection,
    model_prob: e[0].model_prob, market_prob: e[0].market_prob,
    edge_pp: e[0].edge_pp, rating: e[0].rating,
    note: ['Model reads the line as too short.', 'Pace favours the over.'][i] || '',
  })),
}

const parlayLeg = (o = {}) => ({
  fixture_id: '401752', league: 'ncaaf', kickoff: inHours(3),
  home: 'Florida State', away: 'Clemson', market: 'Spread', selection: 'FSU +3',
  model_prob: 0.7, market_prob: 0.524, decimal_odds: 1.91, edge_pp: 17.6, rating: 'A',
  ...o,
})

const bestParlay = {
  generated_with: 'gridiron-2026.09.1',
  legs: [parlayLeg(), parlayLeg({ fixture_id: '401755', home: 'Texas', away: 'Oklahoma',
    market: 'Total', selection: 'Over 55.5', model_prob: 0.55, edge_pp: 4.2, rating: 'B' })],
  leg_count: 2, model_prob: 0.385, decimal_odds: 3.65, american_odds: 265,
  implied_prob: 0.274, edge_pp: 11.1, ev_per_unit: 0.405, payout_per_unit: 2.65,
  pool: [parlayLeg(), parlayLeg({ fixture_id: '401755', home: 'Texas', away: 'Oklahoma',
    market: 'Total', selection: 'Over 55.5', model_prob: 0.55, edge_pp: 4.2, rating: 'B' })],
}

const plays = [
  { period: 3, clock: '7:22', team_abbr: 'UGA', type: 'Pass Reception',
    text: 'C. Beck pass complete to O. Delp for 9 yards to the ALA 32',
    away_score: 14, home_score: 17, scoring: false, down_distance: '2nd & 6 at ALA 41' },
  { period: 3, clock: '8:04', team_abbr: 'UGA', type: 'Rush',
    text: 'T. Etienne rush for 4 yards to the ALA 41',
    away_score: 14, home_score: 17, scoring: false, down_distance: '1st & 10 at ALA 45' },
  { period: 3, clock: '9:31', team_abbr: 'ALA', type: 'Punt',
    text: 'J. Burnip punt for 44 yards, fair catch by A. Bell',
    away_score: 14, home_score: 17, scoring: false, down_distance: '4th & 7 at ALA 33' },
]

const news = {
  league: 'nfl+ncaaf',
  fetched_at: iso(),
  ok: true,
  source: 'ESPN',
  attribution: 'Headlines and summaries from ESPN. Follow a link to read the full story at the source.',
  items: [
    { league: 'ncaaf', id: 'n1', headline: 'Florida State QB listed as questionable',
      description: 'The starter is a game-time decision with a shoulder issue.',
      published: inHours(-1), byline: 'Staff', url: 'https://www.espn.com/story/n1',
      image: '', category: 'injury', teams: ['FSU'], source: 'ESPN',
      reflected_in_projection: false },
    { league: 'nfl', id: 'n2', headline: 'Week 1 takeaways from Sunday’s slate',
      description: 'What the opening weekend told us about the contenders.',
      published: inHours(-4), byline: 'Staff', url: 'https://www.espn.com/story/n2',
      image: '', category: 'recap', teams: ['KC', 'BUF'], source: 'ESPN',
      reflected_in_projection: false },
    { league: 'ncaaf', id: 'n3', headline: 'Preview: Clemson at Florida State',
      description: 'Both teams enter the weekend unbeaten in conference play.',
      published: inHours(-6), byline: 'Staff', url: 'https://www.espn.com/story/n3',
      image: '', category: 'preview', teams: ['CLEM', 'FSU'], source: 'ESPN',
      reflected_in_projection: false },
  ],
}

const entitlements = {
  plan: 'free', authenticated: false, auth_configured: false,
  features: {
    line_movement_history: true, model_internals: true,
    alerts: false, player_props: false, saved_games: false,
  },
  unavailable_reason: {
    alerts: 'Requires a signed-in account and durable storage; neither is configured yet.',
    player_props: 'Requires a licensed player-props odds provider; none is configured yet.',
    saved_games: 'Requires a signed-in account and durable storage; neither is configured yet.',
  },
  billing_enabled: false,
  note: 'StatEdge is free during this release. Every implemented feature is available to everyone; nothing is being sold and no payment method is collected.',
}

const props = {
  available: false, league: '', event_id: '', props: [],
  reason: 'StatEdge has no player-props data source. The keyless ESPN feed behind the rest of the site does not publish player-prop lines, and the model does not yet produce player-level projections.',
  requires: [
    'A licensed player-props odds provider with player-level markets for NFL and NCAA football.',
    "The provider's API key supplied as the PROPS_API_KEY environment variable, plus PROPS_PROVIDER naming the integration to use.",
    'Per-player projections from the model. The gridiron engine currently projects team scores and game totals only.',
  ],
}

module.exports = { iso, inHours, mkGame, mkModel, mkEdge, today, accuracy, bestBets, bestParlay, plays, news, entitlements, props }
