import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import fs from 'node:fs'
import path from 'node:path'
import { NewsCard } from '../components/news/NewsCard'
import { FaqList } from '../components/faq/FaqList'
import { FAQ, FAQ_PREVIEW_IDS } from '../content/faq'
import { Account } from './Account'
import { Props } from './Props'
import { resetEntitlements } from '../hooks/useEntitlement'
import type { EntitlementsOut, NewsItemOut, PropsOut } from '../types'

const newsItem: NewsItemOut = {
  league: 'ncaaf', id: 'n1',
  headline: 'Starting QB listed as questionable',
  description: 'A game-time decision with a shoulder issue.',
  published: new Date(Date.now() - 30 * 60_000).toISOString(),
  byline: 'Staff', url: 'https://www.espn.com/story/n1', image: '',
  category: 'injury', teams: ['FSU'], source: 'ESPN',
  reflected_in_projection: false,
}

const entitlements: EntitlementsOut = {
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
  note: 'StatEdge is free during this release.',
}

const propsStatus: PropsOut = {
  available: false, league: '', event_id: '', props: [],
  reason: 'StatEdge has no player-props data source.',
  requires: ['A licensed player-props odds provider.', 'Per-player projections from the model.'],
}

const wrap = (ui: React.ReactNode) => render(<MemoryRouter>{ui}</MemoryRouter>)

describe('NewsCard', () => {
  it('links back to the publisher rather than reproducing the article', () => {
    wrap(<NewsCard item={newsItem} />)
    const link = screen.getByRole('link', { name: /read at espn/i })
    expect(link).toHaveAttribute('href', 'https://www.espn.com/story/n1')
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'))
  })

  it('attributes the source and byline', () => {
    wrap(<NewsCard item={newsItem} />)
    expect(screen.getByText('ESPN · Staff')).toBeInTheDocument()
  })

  it('never implies a headline moved the projection', () => {
    wrap(<NewsCard item={newsItem} />)
    expect(screen.getByText('Not yet reflected in projection')).toBeInTheDocument()
  })

  it('says so only when the model actually consumed the story', () => {
    wrap(<NewsCard item={{ ...newsItem, reflected_in_projection: true }} />)
    expect(screen.getByText('Reflected in projection')).toBeInTheDocument()
  })
})

describe('FaqList', () => {
  it('answers start collapsed and expand on click', async () => {
    const user = userEvent.setup()
    const entries = FAQ.filter(e => FAQ_PREVIEW_IDS.includes(e.id))
    wrap(<FaqList entries={entries} />)

    const first = screen.getByRole('button', { name: entries[0].q })
    expect(first).toHaveAttribute('aria-expanded', 'false')
    await user.click(first)
    expect(first).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText(entries[0].a[0])).toBeVisible()
  })

  it('opens the answer a deep link points at', () => {
    const entries = FAQ.filter(e => FAQ_PREVIEW_IDS.includes(e.id))
    wrap(<FaqList entries={entries} openIds={[entries[1].id]} />)
    expect(screen.getByRole('button', { name: entries[1].q }))
      .toHaveAttribute('aria-expanded', 'true')
  })

  it('gives every answer a stable anchor', () => {
    const entries = FAQ.filter(e => FAQ_PREVIEW_IDS.includes(e.id))
    const { container } = wrap(<FaqList entries={entries} />)
    entries.forEach(e => expect(container.querySelector(`#${e.id}`)).not.toBeNull())
  })
})

describe('FAQ content', () => {
  it('has unique ids so deep links are unambiguous', () => {
    const ids = FAQ.map(e => e.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('every question has at least one written answer paragraph', () => {
    FAQ.forEach(e => {
      expect(e.a.length).toBeGreaterThan(0)
      e.a.forEach(p => expect(p.trim().length).toBeGreaterThan(20))
    })
  })

  it('the homepage preview only references questions that exist', () => {
    FAQ_PREVIEW_IDS.forEach(id => expect(FAQ.some(e => e.id === id)).toBe(true))
  })
})

describe('Account — access comes from the server', () => {
  beforeEach(() => {
    resetEntitlements()
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(entitlements), {
      status: 200, headers: { 'content-type': 'application/json' },
    })))
  })
  afterEach(() => { vi.unstubAllGlobals(); resetEntitlements() })

  it('shows the plan the server reported', async () => {
    wrap(<Account />)
    expect(await screen.findByText('free')).toBeInTheDocument()
  })

  it('offers no sign-in form when no identity provider is configured', async () => {
    wrap(<Account />)
    await screen.findByText('free')
    expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /sign in|log in|create account/i })).not.toBeInTheDocument()
  })

  it('explains every feature the server withheld', async () => {
    wrap(<Account />)
    await screen.findByText('free')
    expect(screen.getByText(entitlements.unavailable_reason.player_props)).toBeInTheDocument()
    expect(screen.getAllByText(entitlements.unavailable_reason.alerts).length).toBeGreaterThan(0)
  })

  it('never shows a checkout or price', async () => {
    wrap(<Account />)
    await screen.findByText('free')
    expect(screen.queryByText(/\$|upgrade|subscribe|checkout/i)).not.toBeInTheDocument()
  })
})

describe('Props — honest about a missing provider', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(propsStatus), {
      status: 200, headers: { 'content-type': 'application/json' },
    })))
  })
  afterEach(() => vi.unstubAllGlobals())

  it('states the feature is unavailable and why', async () => {
    wrap(<Props />)
    expect(await screen.findByText(/aren’t available yet/i)).toBeInTheDocument()
    expect(screen.getByText(propsStatus.reason)).toBeInTheDocument()
  })

  it('lists what closing the gap would require', async () => {
    wrap(<Props />)
    const section = await screen.findByRole('region', { name: /aren’t available yet/i })
    propsStatus.requires.forEach(r =>
      expect(within(section).getByText(r)).toBeInTheDocument())
  })

  it('shows no prop rows at all', async () => {
    wrap(<Props />)
    await screen.findByText(/aren’t available yet/i)
    await waitFor(() => expect(screen.queryByRole('table')).not.toBeInTheDocument())
  })
})

describe('Vercel config', () => {
  // vitest runs with `frontend/` as its root, so both files resolve from cwd.
  const read = (rel: string) =>
    JSON.parse(fs.readFileSync(path.resolve(process.cwd(), rel), 'utf8'))

  it('keeps both vercel.json files in sync', () => {
    // Vercel reads whichever file matches the project's Root Directory. If the
    // two drift, the deployment behaves differently depending on a dashboard
    // setting nobody remembers changing.
    const root = read('../vercel.json')
    const fe = read('vercel.json')
    expect(root.rewrites).toEqual(fe.rewrites)
    expect(root.headers).toEqual(fe.headers)
  })

  it('proxies the API before falling back to the SPA', () => {
    for (const rel of ['../vercel.json', 'vercel.json']) {
      const sources = read(rel).rewrites.map((r: { source: string }) => r.source)
      expect(sources[0]).toBe('/api/:path*')
      // The catch-all must come last or it swallows /api.
      expect(sources.indexOf('/(.*)')).toBe(sources.length - 1)
    }
  })

  it('builds the frontend regardless of which root Vercel uses', () => {
    expect(read('../vercel.json').outputDirectory).toBe('frontend/dist')
    expect(read('vercel.json').outputDirectory).toBe('dist')
  })
})
