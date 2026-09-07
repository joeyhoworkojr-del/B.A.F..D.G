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
  },
  edges: [],
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

      // 5. "Why this edge?" opens the right explanation.
      await page.getByRole('button', { name: /why this edge/i }).click()
      await page.waitForTimeout(400)
      check(`[${name}] why-this-edge selects the spread market`,
        await page.getByRole('tab', { name: 'Spread' }).getAttribute('aria-selected') === 'true')
      check(`[${name}] grade calculation is explained`,
        await page.getByText('How grades are calculated').isVisible())

      // 6. Market tabs are keyboard operable.
      await page.getByRole('tab', { name: 'Spread' }).focus()
      await page.keyboard.press('ArrowRight')
      await page.waitForTimeout(250)
      check(`[${name}] market tabs respond to arrow keys`,
        await page.getByRole('tab', { name: 'Total' }).getAttribute('aria-selected') === 'true')

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
