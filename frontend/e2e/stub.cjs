/**
 * Every API route the app calls, stubbed at the network boundary.
 *
 * Shared by the screenshot script and the end-to-end checks. It lived in the
 * screenshot script alone, which meant the checks could only ever visit the
 * two pages whose routes they happened to stub themselves — the reason the
 * board shipped redesigned with nothing measuring it.
 */
const fx = require('./fixtures.cjs')

const s = (label, side, model, book, price, edge, grade) => ({
  label, side, model_prob: model, model_prob_raw: model, book_prob: book,
  price_american: price, price_decimal: 1.91, fair_price_american: -194,
  edge_pp: edge, ev_per_unit: 0.26, grade,
})

const MARKETS = [
  { key: 'moneyline', label: 'Moneyline', question: 'Who wins the game outright?',
    probability_kind: 'win', assumed_price: false,
    selections: [s('Clemson', 'away', 0.42, 0.44, -155, -2.4, '-'),
                 s('Florida State', 'home', 0.58, 0.56, 130, 2.1, 'C')] },
  { key: 'spread', label: 'Spread', question: 'Who covers the point spread?',
    probability_kind: 'cover', assumed_price: true,
    selections: [s('Florida State +3', 'home', 0.70, 0.524, -110, 17.6, 'A'),
                 s('Clemson -3', 'away', 0.30, 0.476, -110, -17.6, '-')] },
  { key: 'total', label: 'Total', question: 'Do the teams combine to go over or under?',
    probability_kind: 'total', assumed_price: true,
    selections: [s('Over 52.5', 'over', 0.57, 0.524, -110, 4.6, 'B'),
                 s('Under 52.5', 'under', 0.43, 0.476, -110, -4.6, '-')] },
]

async function stub(page) {
  // Playwright matches the most recently added route first, so this catch-all
  // is registered up front: anything not stubbed below returns an empty but
  // well-formed body instead of hanging on blocked egress.
  await page.route('**/api/v1/**', r => r.fulfill({ json: {} }))
  await page.route('**/api/v1/today/**', r =>
    r.fulfill({ json: fx.today(new URL(r.request().url()).pathname.split('/').pop()) }))
  await page.route('**/api/v1/board*', r => r.fulfill({ json: fx.board() }))
  await page.route('**/api/v1/props/**', r => r.fulfill({ json: fx.gameProps }))
  await page.route('**/api/v1/accuracy', r => r.fulfill({ json: fx.accuracy }))
  await page.route('**/api/v1/news*', r => r.fulfill({ json: fx.news }))
  await page.route('**/api/v1/entitlements', r => r.fulfill({ json: fx.entitlements }))
  await page.route('**/api/v1/auth/me', r => r.fulfill({ json: fx.session }))
  await page.route('**/api/v1/picks/game/**', r => r.fulfill({ json: fx.community }))
  await page.route('**/api/v1/leaderboard*', r => r.fulfill({ json: fx.leaderboard }))
  await page.route('**/api/v1/picks/mine', r => r.fulfill({ json: fx.myPicks }))
  await page.route('**/api/v1/analysts/**', r =>
    r.fulfill({ status: 404, json: { detail: 'Analyst not found.' } }))
  await page.route('**/api/v1/admin/**', r =>
    r.fulfill({ status: 404, json: { detail: 'Not found' } }))
  await page.route('**/api/v1/auth/username-available*', r =>
    r.fulfill({ json: { username: 'x', available: true } }))
  await page.route('**/api/v1/props*', r => r.fulfill({ json: fx.props }))
  await page.route('**/api/v1/best-bets', r => r.fulfill({ json: fx.bestBets }))
  await page.route('**/api/v1/edges*', r => r.fulfill({ json: fx.edges }))
  await page.route('**/api/v1/chat/**', r => r.fulfill({
    json: {
      game_id: 'ncaaf:401752', messages: [], cursor: 0, count: 0,
      signed_in: false, may_post: false, blocked_reason: '',
      reactions_available: ['\u{1F44D}', '\u{1F525}'],
    },
  }))
  await page.route('**/api/v1/ai/status', r => r.fulfill({
    json: {
      available: true, signed_in: true, may_ask: true, reason: '',
      rate_limit_per_hour: 40, level: 'beta', model: 'claude-opus-5', tools: [],
    },
  }))
  await page.route('**/api/v1/upcoming/**', r => r.fulfill({
    json: {
      league: 'ncaaf', days: 7, fetched_at: fx.iso(), source_ok: true,
      total_scheduled: 2, predicted: 2, truncated: false, market_source: 'ESPN BET',
      games: fx.today('ncaaf').games,
    },
  }))
  await page.route('**/api/v1/live/win-history/**', r => r.fulfill({
    json: { league: 'ncaaf', event_id: '401752', points: [], swing: null, note: '', fetched_at: fx.iso() },
  }))
  await page.route('**/api/v1/best-parlay*', r => r.fulfill({ json: fx.bestParlay }))
  await page.route('**/api/v1/live/pbp/**', r =>
    r.fulfill({ json: { league: 'ncaaf', event_id: '401752', ok: true, fetched_at: fx.iso(), plays: fx.plays } }))
  await page.route('**/api/v1/game/**', r => {
    const t = fx.today('ncaaf')
    const first = t.games[0]
    r.fulfill({
      json: {
        league: 'ncaaf', event_id: '401752', status: 'pre', fetched_at: fx.iso(),
        source_ok: true, source: 'ESPN BET', model_version: '2026.09.1-gridiron',
        grade_scale: [
          { grade: 'A', min_edge_pp: 6, label: 'Strong' },
          { grade: 'B', min_edge_pp: 3.5, label: 'Solid' },
          { grade: 'C', min_edge_pp: 1.5, label: 'Slight' },
          { grade: '-', min_edge_pp: 0, label: 'No edge' },
        ],
        game: first.game, mapped: true, model: first.model, edges: first.edges,
        markets: MARKETS,
        best_edge: {
          ...MARKETS[1].selections[0], market_key: 'spread', market_label: 'Spread',
          line: 3, source: 'ESPN BET', assumed_price: true, probability_kind: 'cover',
        },
      },
    })
  })
}

module.exports = { stub, fx }
