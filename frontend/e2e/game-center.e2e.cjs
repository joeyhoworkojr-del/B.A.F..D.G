/**
 * End-to-end check of the Game Center against the real built bundle.
 *
 * Runs the production build behind `vite preview`, stubs the API at the network
 * boundary (so the assertions are about the app, not the feed), and verifies the
 * acceptance criteria at 390 / 768 / 1440 px.
 *
 *   npm run build && npm run test:e2e
 */
const { chromium } = require('playwright-core')
const { spawn } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')

const PORT = Number(process.env.E2E_PORT || 4325)
const BASE = `http://localhost:${PORT}`
const CHROME = [
  '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell',
  '/opt/pw-browsers/chromium/chrome-linux/chrome',
].find(p => fs.existsSync(p))

const iso = () => new Date().toISOString()

const game = {
  league: 'ncaaf', event_id: '401752',
  home: 'Florida State', away: 'Clemson', home_abbr: 'FSU', away_abbr: 'CLEM',
  home_score: null, away_score: null, state: 'pre', detail: 'Sat 3:30 PM',
  kickoff: new Date(Date.now() + 3 * 3600e3).toISOString(),
  market_spread: 3, market_over_under: 52.5,
  market_home_ml: 130, market_away_ml: -155,
  market_details: 'CLEM -3', market_provider: 'ESPN BET',
}

const sel = (label, side, model, book, price, edge, grade) => ({
  label, side, model_prob: model, model_prob_raw: model, book_prob: book,
  price_american: price, price_decimal: 1.9, fair_price_american: -194,
  edge_pp: edge, ev_per_unit: 0.26, grade,
})

const detail = {
  league: 'ncaaf', event_id: '401752', status: 'pre', fetched_at: iso(),
  source_ok: true, source: 'ESPN BET', model_version: '2026.09.1-gridiron',
  grade_scale: [
    { grade: 'A', min_edge_pp: 6, label: 'Strong' },
    { grade: 'B', min_edge_pp: 3.5, label: 'Solid' },
    { grade: 'C', min_edge_pp: 1.5, label: 'Slight' },
    { grade: '-', min_edge_pp: 0, label: 'No edge' },
  ],
  game, mapped: true,
  model: {
    home_win_prob: 0.58, away_win_prob: 0.42, calibrated_home_win: 0.56,
    calibrated_away_win: 0.44, market_anchored: true,
    home_expected: 27.4, away_expected: 24.9,
    proj_home_score: 27.4, proj_away_score: 24.9, total_estimate: 52.3,
    over_prob: 0.57, under_prob: 0.43, home_cover_prob: 0.7,
    total_line: 52.5, conditions: [], live: false,
    // The outright winner card sits above the markets on the Scorecast tab,
    // so it has to be in this stub — otherwise the above-the-fold check below
    // is passing on a page that is missing the thing being measured.
    winner: {
      side: 'home', team: 'Florida State', abbr: 'FSU', opponent: 'Clemson',
      win_prob: 0.56, model_prob: 0.58, market_prob: 0.53,
      market_prob_is_implied: false, price_american: -125,
      market_agrees: true, band: 'lean', live: false, graded: true,
    },
  },
  edges: [],
  // The fair-line and why panels render from these. They must be in the stub,
  // or the above-the-fold check below measures a page missing them — which is
  // exactly how a layout regression got through once already.
  value: {
    spread: {
      fair: -4.8, fair_label: 'FSU -4.8', market: -3, market_label: 'FSU -3.0',
      edge_points: 1.8, side: 'home', side_abbr: 'FSU', points: 1.8,
    },
    total: { fair: 54.1, market: 52.5, edge_points: 1.6, side: 'over', points: 1.6 },
    confidence: {
      level: 'medium', inputs_present: 3, inputs_total: 4,
      inputs: [
        { name: 'Team ratings from play-by-play', present: true, note: 'cfbd-sp+' },
        { name: 'Quoted moneyline prices', present: true, note: 'ESPN BET' },
        { name: 'Market line to anchor to', present: true, note: 'spread and/or moneyline' },
        { name: 'Conditions and availability', present: false, note: 'not modelled for college football' },
      ],
      means: "How much of the model's input was available for this game. Not the chance a bet wins.",
    },
    validation: {
      measured: false, games: 0, beats_market: null,
      note: 'Not backtested. Accuracy against the market is unknown rather than good or bad.',
    },
  },
  why: {
    fair_label: 'FSU -4.8', side: 'home', side_abbr: 'FSU', points: 1.8,
    line: {
      opening: -2.5, current: -3, moved_points: -0.5, state: 'value',
      note: 'StatEdge still has 1.8 points on FSU.',
    },
    reasons: [
      { label: 'FSU rated 7th of 134', detail: '+9.2 points per game against an average team over 5 games (cfbd-sp+)', impact_points: null, source: 'ratings' },
      { label: 'Shrunk 72% toward the market price', detail: 'The published line is the sharpest single estimate available.', impact_points: null, source: 'anchor' },
    ],
    basis: 'Every line here is an input the model read.',
  },
  markets: [
    { key: 'moneyline', label: 'Moneyline', question: 'Who wins the game outright?',
      probability_kind: 'win', line: null, source: 'ESPN BET', assumed_price: false,
      selections: [sel('CLEM ML', 'away', 0.44, 0.58, -155, -14, '-'),
                   sel('FSU ML', 'home', 0.56, 0.42, 130, 14, 'A')] },
    { key: 'spread', label: 'Spread', question: 'Who covers the point spread?',
      probability_kind: 'cover', line: 3, source: 'ESPN BET', assumed_price: true,
      selections: [sel('CLEM -3.0', 'away', 0.34, 0.502, -110, -16.2, '-'),
                   sel('FSU +3.0', 'home', 0.66, 0.502, -110, 15.8, 'A')] },
    { key: 'total', label: 'Total', question: 'Over or under 52.5?',
      probability_kind: 'total', line: 52.5, source: 'ESPN BET', assumed_price: true,
      selections: [sel('Over 52.5', 'over', 0.55, 0.5, -110, 5, 'B'),
                   sel('Under 52.5', 'under', 0.45, 0.5, -110, -5, '-')] },
  ],
  best_edge: {
    ...sel('FSU +3.0', 'home', 0.66, 0.502, -110, 15.8, 'A'),
    market_key: 'spread', market_label: 'Spread', line: 3,
    source: 'ESPN BET', assumed_price: true, probability_kind: 'cover',
  },
  polymarket: null, snapshot: null,
}

/**
 * The homepage board.
 *
 * Built from the same `game`, `model`, `value` and `why` objects as the game
 * stub above, so the two cannot drift apart, with an NFL game added because
 * the NFL is the league whose backtest result the board has to carry — a
 * college-only stub would render the board with the wrong disclosure on it
 * and the check below would pass on a page that never shows the real one.
 */
const nflGame = {
  ...game, league: 'nfl', event_id: '401671',
  home: 'Kansas City Chiefs', away: 'Baltimore Ravens',
  home_abbr: 'KC', away_abbr: 'BAL', detail: 'Sun 4:25 PM',
}
const liveNflGame = {
  ...nflGame, event_id: '401672', state: 'in',
  home_score: 21, away_score: 17, period: 3, clock: '4:12',
  home: 'Buffalo Bills', away: 'New York Jets', home_abbr: 'BUF', away_abbr: 'NYJ',
}

const entry = (g, league, validation) => ({
  league, projected: true, mapped: true, game: g,
  model: detail.model, edges: [], polymarket: null,
  value: { ...detail.value, validation },
  why: detail.why,
})

const nflValidation = {
  measured: true, games: 750, beats_market: false,
  note: 'Backtested over 750 NFL games: the model alone is less accurate than the closing line.',
}

const board = {
  days: [{
    date: '2026-10-18', label: 'Today', live: 1,
    by_league: { nfl: 2, ncaaf: 1 },
    games: [
      entry(liveNflGame, 'nfl', nflValidation),
      entry(nflGame, 'nfl', nflValidation),
      entry(game, 'ncaaf', detail.value.validation),
    ],
  }],
  live_count: 1, total_games: 3, predicted: 3, leagues: ['nfl', 'ncaaf'],
  source_ok: true, fetched_at: iso(), market_source: 'ESPN BET', note: '',
}

// The hero's three tiles are measured figures or nothing, so the stub carries
// a real graded record, a priced ROI and a tracked closing-line average.
const accuracy = {
  overall: { total: 103, correct: 88, accuracy: 88 / 103 },
  by_league: {}, pending: 4, note: '', scope: 'pregame',
  performance: {
    total_picks: 103, wins: 88, losses: 15, win_rate: 88 / 103,
    priced_picks: 103, roi_pct: 4.2, profit_units: 4.33,
    avg_clv_points: 0.42, clv_tracked: 61, clv_beat_close: 38,
    avg_edge_pp: 3.1, series: [], ats: null, totals: null,
  },
  recent: [],
}

const checks = []
function check(name, ok, extra = '') {
  checks.push({ name, ok, extra })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${extra ? ` — ${extra}` : ''}`)
}

async function main() {
  if (!CHROME) throw new Error('No Chromium binary found')
  const dist = path.resolve(__dirname, '..', 'dist')
  if (!fs.existsSync(dist)) throw new Error('Run `npm run build` first')

  const server = spawn('node_modules/.bin/vite', ['preview', '--port', String(PORT), '--strictPort'], {
    cwd: path.resolve(__dirname, '..'), stdio: 'ignore',
  })
  const stop = () => { try { server.kill() } catch { /* already gone */ } }
  process.on('exit', stop)

  // Wait for the preview server.
  for (let i = 0; i < 60; i++) {
    try { const r = await fetch(BASE); if (r.ok) break } catch { /* not up yet */ }
    await new Promise(r => setTimeout(r, 250))
  }

  const browser = await chromium.launch({ executablePath: CHROME, args: ['--no-proxy-server', '--no-sandbox'] })
  try {
    for (const [w, h, name] of [[390, 844, 'mobile'], [768, 1024, 'tablet'], [1440, 900, 'desktop']]) {
      const page = await browser.newPage({ viewport: { width: w, height: h } })
      const errors = []
      page.on('pageerror', e => errors.push(e.message))
      await page.route('**/api/v1/game/**', r => r.fulfill({ json: detail }))
      await page.route('**/api/v1/live/pbp/**', r =>
        r.fulfill({ json: { league: 'ncaaf', event_id: '401752', ok: true, fetched_at: iso(), plays: [] } }))

      await page.goto(`${BASE}/game/ncaaf/401752`, { waitUntil: 'networkidle' })
      await page.waitForSelector('text=Best available edge', { timeout: 10000 })

      // 1. The primary signal is above the fold without scrolling.
      const box = await page.locator('#primary-edge-heading').boundingBox()
      check(`[${name}] primary edge is above the fold`, !!box && box.y < h, box ? `y=${Math.round(box.y)}` : 'missing')

      // 2. Probability kinds are unambiguous.
      check(`[${name}] cover probability is labelled`,
        await page.getByText('Model cover probability').isVisible())

      // 3. Line, price, source and freshness are visible.
      check(`[${name}] price + source + freshness visible`,
        (await page.getByText('-110', { exact: false }).first().isVisible()) &&
        (await page.getByText('ESPN BET').first().isVisible()) &&
        (await page.getByText(/Updated .* ago/).first().isVisible()))

      // 4. Pregame must not render a 0–0 scoreline.
      check(`[${name}] no fake 0–0 scoreline pregame`,
        (await page.getByText('vs.').first().isVisible()) &&
        (await page.locator('header:has-text("Pregame")').getByText('0', { exact: true }).count()) === 0)

      // 5. "Why this edge?" opens the right explanation — which now lives on
      //    the Markets section, so following the link has to cross to it.
      await page.getByRole('button', { name: /why this edge/i }).click()
      await page.waitForTimeout(400)
      check(`[${name}] why-this-edge crosses to the markets section`,
        await page.getByRole('tab', { name: /^Markets/ }).getAttribute('aria-selected') === 'true')
      // Both the section tabs and the market tabs are tabs, so the market ones
      // are addressed inside the panel rather than by name alone.
      const marketTab = label => page.locator('#market-panel-tabs, [role="tablist"]')
        .last().getByRole('tab', { name: label })
      check(`[${name}] why-this-edge selects the spread market`,
        await marketTab('Spread').getAttribute('aria-selected') === 'true')
      check(`[${name}] grade calculation is explained`,
        await page.getByText('How grades are calculated').isVisible())

      // 6. Market tabs are keyboard operable.
      await marketTab('Spread').focus()
      await page.keyboard.press('ArrowRight')
      await page.waitForTimeout(250)
      check(`[${name}] market tabs respond to arrow keys`,
        await marketTab('Total').getAttribute('aria-selected') === 'true')

      // Back to where the page opens, so the checks below measure the section
      // a reader actually lands on.
      await page.getByRole('tab', { name: /^Scorecast/ }).click()
      await page.waitForTimeout(300)

      // 7. Nav: the bottom bar covers everything below `lg`, and the desktop
      // header nav takes over at and above it. Exactly one is ever visible.
      const bottomVisible = await page.locator('[data-nav="bottom"]').isVisible()
      const topVisible = await page.locator('[data-nav="top"]').isVisible()
      check(`[${name}] exactly one primary nav is visible`, bottomVisible !== topVisible)
      check(`[${name}] correct nav for this width`,
        name === 'desktop' ? topVisible : bottomVisible)

      // 8. No horizontal overflow at any width.
      const overflow = await page.evaluate(() =>
        document.documentElement.scrollWidth - document.documentElement.clientWidth)
      check(`[${name}] no horizontal overflow`, overflow <= 1, `overflow=${overflow}px`)

      // 9. Desktop is not a narrow mobile column.
      if (name === 'desktop') {
        const cw = await page.locator('#primary-edge-heading').evaluate(el =>
          el.closest('section').getBoundingClientRect().width)
        check('[desktop] content uses the wide layout', cw > 560, `card=${Math.round(cw)}px`)
      }

      check(`[${name}] no runtime errors`, errors.length === 0, errors.join('; '))
      await page.close()
    }

    // ── The homepage board ───────────────────────────────────────────────
    // The board was redesigned as a dark hero over a scrolling live strip and
    // a two-column grid of rows. Every one of those is an overflow risk at
    // 390px and none of it was measured anywhere before this block.
    // 320px is in the list because that is where it broke: the header's
    // account button and the game row's number column were each sized for a
    // phone wider than the narrowest one people still use, or than anyone
    // gets by zooming in.
    for (const [w, h, name] of [[320, 568, 'narrow'], [390, 844, 'mobile'], [768, 1024, 'tablet'], [1440, 900, 'desktop']]) {
      const page = await browser.newPage({ viewport: { width: w, height: h } })
      const errors = []
      page.on('pageerror', e => errors.push(e.message))
      // Registered first so the specific routes below take precedence: an
      // unstubbed call must fail as JSON rather than be served index.html.
      await page.route('**/api/v1/**', r => r.fulfill({ status: 404, json: { detail: 'not stubbed' } }))
      await page.route('**/api/v1/board**', r => r.fulfill({ json: board }))
      await page.route('**/api/v1/accuracy**', r => r.fulfill({ json: accuracy }))
      await page.route('**/api/v1/news**', r =>
        r.fulfill({ json: { fetched_at: iso(), source_ok: true, items: [] } }))

      await page.goto(`${BASE}/`, { waitUntil: 'networkidle' })
      await page.waitForSelector('#todays-edge', { timeout: 10000 })

      // 1. The headline figures are the measured ones, with their denominators.
      check(`[board/${name}] hero shows the graded record and its denominator`,
        (await page.getByText('88–15').first().isVisible()) &&
        (await page.getByText('103 graded picks').first().isVisible()))
      check(`[board/${name}] hero shows a priced ROI and a tracked CLV`,
        (await page.getByText('+4.2%').first().isVisible()) &&
        (await page.getByText('+0.42').first().isVisible()) &&
        (await page.getByText(/61 tracked/).first().isVisible()))
      // The record is a winner record sitting beside an ROI, so the page has
      // to say which it is — and link to where it can be checked.
      check(`[board/${name}] the record says what it counts, and links to it`,
        (await page.getByText(/the side the model favoured won/i).first().isVisible()) &&
        (await page.getByRole('link', { name: /full record/i }).first().isVisible()))

      // 2. The backtest result is on the board, above the first row — not
      //    only on the game page one tap away.
      const noteBox = await page.getByText(/no demonstrated edge on this league/i).first().boundingBox()
      const rowBox = await page.getByText('StatEdge', { exact: true }).first().boundingBox()
      check(`[board/${name}] the NFL backtest result is above the first row`,
        !!noteBox && !!rowBox && noteBox.y < rowBox.y,
        noteBox && rowBox ? `note=${Math.round(noteBox.y)} row=${Math.round(rowBox.y)}` : 'missing')

      // 3. A game in progress is on the board, and says so.
      check(`[board/${name}] a live game is on the board with its clock`,
        await page.getByText('Q3 4:12').first().isVisible())

      // 4. Nav, as on the game page: exactly one, and the right one.
      const bottomVisible = await page.locator('[data-nav="bottom"]').isVisible()
      const topVisible = await page.locator('[data-nav="top"]').isVisible()
      check(`[board/${name}] exactly one primary nav is visible`, bottomVisible !== topVisible)
      check(`[board/${name}] correct nav for this width`,
        name === 'desktop' ? topVisible : bottomVisible)

      // 5. The raised centre button in the bottom bar sticks out of its row.
      //    It must not stick out of the viewport.
      if (bottomVisible) {
        const btn = await page.locator('[data-nav="bottom"] a').nth(2).boundingBox()
        check(`[board/${name}] the raised nav button stays inside the viewport`,
          !!btn && btn.x >= 0 && btn.x + btn.width <= w && btn.y >= 0,
          btn ? `x=${Math.round(btn.x)} w=${Math.round(btn.width)}` : 'missing')
      }

      // 6. No horizontal overflow — the hero, the chip row and the live strip
      //    all scroll inside themselves or not at all.
      const overflow = await page.evaluate(() =>
        document.documentElement.scrollWidth - document.documentElement.clientWidth)
      check(`[board/${name}] no horizontal overflow`, overflow <= 1, `overflow=${overflow}px`)

      // 7. The hero is the first thing on the page, at every width.
      const hero = await page.locator('#todays-edge').boundingBox()
      check(`[board/${name}] the hero is above the fold`, !!hero && hero.y < h,
        hero ? `y=${Math.round(hero.y)}` : 'missing')

      check(`[board/${name}] no runtime errors`, errors.length === 0, errors.join('; '))
      await page.close()
    }

    // Failure path: a dead feed must show an error, not a blank page.
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } })
    await page.route('**/api/v1/game/**', r => r.fulfill({ status: 500, json: { detail: 'feed down' } }))
    await page.route('**/api/v1/live/pbp/**', r => r.abort())
    await page.goto(`${BASE}/game/ncaaf/401752`, { waitUntil: 'networkidle' })
    await page.waitForTimeout(600)
    check('[error] failed feed surfaces an alert', await page.getByRole('alert').first().isVisible())
    await page.close()
  } finally {
    await browser.close()
    stop()
  }

  const failed = checks.filter(c => !c.ok)
  console.log(`\n${checks.length - failed.length}/${checks.length} checks passed`)
  if (failed.length) process.exit(1)
}

main().catch(e => { console.error(e); process.exit(1) })
