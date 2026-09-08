/**
 * Captures the main screens at 390 / 768 / 1440 px against the real built
 * bundle, with the API stubbed at the network boundary.
 *
 *   npm run build && npm run screenshots
 *
 * Output: e2e/screens/<page>-<width>.png
 */
const { chromium } = require('playwright-core')
const { spawn } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')
const fx = require('./fixtures.cjs')

const PORT = Number(process.env.SHOT_PORT || 4326)
const BASE = `http://localhost:${PORT}`
const OUT = path.resolve(__dirname, 'screens')
const CHROME = [
  '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell',
  '/opt/pw-browsers/chromium/chrome-linux/chrome',
].find(p => fs.existsSync(p))

const VIEWPORTS = [[390, 844, 'mobile'], [768, 1024, 'tablet'], [1440, 900, 'desktop']]
const PAGES = [
  ['games', '/'],
  ['game-center', '/game/ncaaf/401752'],
  ['live', '/live'],
  ['props', '/props'],
  ['edges', '/best-bets'],
  ['leaderboard', '/leaderboard'],
  ['login', '/login'],
  ['register', '/register'],
  ['my-edge', '/my-edge'],
  ['staff', '/staff'],
  ['analyst', '/@someone'],
  ['notfound', '/no-such-page'],
  ['news', '/news'],
  ['results', '/results'],
  ['parlay', '/parlay'],
  ['faq', '/faq'],
  ['about', '/about'],
  ['account', '/account'],
]

async function stub(page) {
  // Playwright matches the most recently added route first, so this catch-all
  // is registered up front: anything not stubbed below returns an empty but
  // well-formed body instead of hanging on blocked egress.
  await page.route('**/api/v1/**', r => r.fulfill({ json: {} }))
  await page.route('**/api/v1/today/**', r =>
    r.fulfill({ json: fx.today(new URL(r.request().url()).pathname.split('/').pop()) }))
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

async function main() {
  if (!CHROME) throw new Error('No Chromium binary found')
  if (!fs.existsSync(path.resolve(__dirname, '..', 'dist'))) throw new Error('Run `npm run build` first')
  fs.mkdirSync(OUT, { recursive: true })

  const server = spawn('node_modules/.bin/vite', ['preview', '--port', String(PORT), '--strictPort'], {
    cwd: path.resolve(__dirname, '..'), stdio: 'ignore',
  })
  const stop = () => { try { server.kill() } catch { /* already gone */ } }
  process.on('exit', stop)
  for (let i = 0; i < 60; i++) {
    try { const r = await fetch(BASE); if (r.ok) break } catch { /* not up yet */ }
    await new Promise(r => setTimeout(r, 250))
  }

  const browser = await chromium.launch({ executablePath: CHROME, args: ['--no-proxy-server', '--no-sandbox'] })
  const problems = []
  try {
    // One page per viewport, all three walking the route list at once — the
    // sandbox is slow enough that doing this serially dominates the run.
    await Promise.all(VIEWPORTS.map(async ([w, h, vp]) => {
      const page = await browser.newPage({ viewport: { width: w, height: h } })
      const errors = []
      page.on('pageerror', e => errors.push(e.message))
      await stub(page)
      for (const [name, route] of PAGES) {
        await page.goto(BASE + route, { waitUntil: 'load' })
        await page.waitForTimeout(700)
        const file = path.join(OUT, `${name}-${vp}.png`)
        await page.screenshot({ path: file, fullPage: true })

        // Every screen must be genuinely white and must not scroll sideways.
        const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor)
        if (bg !== 'rgb(255, 255, 255)') problems.push(`${name}/${vp}: body background is ${bg}`)
        const overflow = await page.evaluate(() =>
          document.documentElement.scrollWidth - document.documentElement.clientWidth)
        if (overflow > 0) problems.push(`${name}/${vp}: ${overflow}px horizontal overflow`)
        console.log(`  ${vp.padEnd(7)} ${name.padEnd(12)} ${path.relative(process.cwd(), file)}`)
      }
      if (errors.length) problems.push(`${vp}: runtime errors — ${errors.join(' | ')}`)
      await page.close()
    }))
  } finally {
    await browser.close()
    stop()
  }

  if (problems.length) {
    console.error('\nPROBLEMS:\n' + problems.map(p => '  - ' + p).join('\n'))
    process.exitCode = 1
  } else {
    console.log(`\nCaptured ${VIEWPORTS.length * PAGES.length} screens — all white, no overflow.`)
  }
}

main().catch(e => { console.error(e); process.exit(1) })
