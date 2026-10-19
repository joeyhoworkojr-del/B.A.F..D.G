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
const { stub, fx } = require('./stub.cjs')

const PORT = Number(process.env.SHOT_PORT || 4326)
const BASE = `http://localhost:${PORT}`
const OUT = path.resolve(__dirname, 'screens')
const CHROME = [
  '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell',
  '/opt/pw-browsers/chromium/chrome-linux/chrome',
].find(p => fs.existsSync(p))

// The full sweep runs three browser pages at once over every route, which is
// more memory than a small container always has. SHOT_VIEWPORTS and SHOT_PAGES
// narrow the run to a comma-separated subset so it can be taken in bites; both
// unset keeps the full sweep, which is what CI runs.
const only = name => {
  const raw = (process.env[name] || '').trim()
  return raw ? new Set(raw.split(',').map(s => s.trim()).filter(Boolean)) : null
}
const VP_FILTER = only('SHOT_VIEWPORTS')
const PAGE_FILTER = only('SHOT_PAGES')

const ALL_VIEWPORTS = [[390, 844, 'mobile'], [768, 1024, 'tablet'], [1440, 900, 'desktop']]
const ALL_PAGES = [
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
  ['ask-edge', '/ask'],
  ['upcoming', '/upcoming'],
]

const VIEWPORTS = ALL_VIEWPORTS.filter(([, , n]) => !VP_FILTER || VP_FILTER.has(n))
const PAGES = ALL_PAGES.filter(([n]) => !PAGE_FILTER || PAGE_FILTER.has(n))


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
