import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { api } from '../api/client'
import { SessionProvider, useSession } from './SessionProvider'
import { FeatureGate, PremiumBadge } from './FeatureGate'
import { MakeYourPick } from '../components/picks/MakeYourPick'
import { GameCommunity } from '../components/picks/GameCommunity'
import { RecordSummary } from '../components/record/RecordSummary'
import { pregameGame, liveGame } from '../test/fixtures'
import type { PickRecord, SessionOut } from '../types'

const guest: SessionOut = {
  user: null,
  entitlements: {
    level: 'guest', authenticated: false, beta_open: true,
    features: { make_pick: false, player_props: false },
    unavailable_reason: { player_props: 'Create an account to see props.' },
    billing_enabled: false, note: '',
  },
}

const member: SessionOut = {
  user: {
    id: 'u1', username: 'joey', display_name: 'Joey', bio: '', avatar_url: '',
    favourite_sports: ['ncaaf'], favourite_teams: [], badges: ['founding_analyst'],
    created_at: '2026-09-01T00:00:00+00:00', email: 'joey@example.com',
    email_verified: false, level: 'beta', interests: [], onboarded: true,
    profile_public: true, auth_provider: 'password',
  },
  entitlements: {
    level: 'beta', authenticated: true, beta_open: true,
    features: { make_pick: true, player_props: true },
    unavailable_reason: {}, billing_enabled: false, note: 'Free during beta.',
  },
}

const wrap = (ui: React.ReactNode) =>
  render(<SessionProvider><MemoryRouter>{ui}</MemoryRouter></SessionProvider>)

afterEach(() => vi.restoreAllMocks())

describe('SessionProvider', () => {
  it('resolves an anonymous visitor as a guest', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(guest)
    function Probe() {
      const { user, entitlements, ready } = useSession()
      return <p>{ready ? `${entitlements.level}:${user ? user.username : 'none'}` : 'loading'}</p>
    }
    wrap(<Probe />)
    expect(await screen.findByText('guest:none')).toBeInTheDocument()
  })

  it('treats a failed session check as signed out, not an error', async () => {
    vi.spyOn(api, 'session').mockRejectedValue(new Error('network'))
    function Probe() {
      const { user, ready } = useSession()
      return <p>{ready ? (user ? 'in' : 'out') : 'loading'}</p>
    }
    wrap(<Probe />)
    expect(await screen.findByText('out')).toBeInTheDocument()
  })

  it('never keeps a session token in browser storage', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(member)
    wrap(<PremiumBadge />)
    await screen.findByText(/PRO/)
    expect(Object.keys(localStorage)).toHaveLength(0)
    expect(document.cookie).not.toContain('statedge_session')
  })
})

describe('FeatureGate', () => {
  it('renders the feature when the server grants it', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(member)
    wrap(<FeatureGate feature="player_props"><p>Prop table</p></FeatureGate>)
    expect(await screen.findByText('Prop table')).toBeInTheDocument()
  })

  it('withholds it and explains why when the server does not', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(guest)
    wrap(<FeatureGate feature="player_props"><p>Prop table</p></FeatureGate>)
    expect(await screen.findByText('Create an account to see props.')).toBeInTheDocument()
    expect(screen.queryByText('Prop table')).not.toBeInTheDocument()
  })

  it('says premium features are included while the beta is open', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(member)
    wrap(<PremiumBadge />)
    expect(await screen.findByText(/included during beta/i)).toBeInTheDocument()
  })
})

describe('MakeYourPick', () => {
  it('asks a signed-out visitor to create an account', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(guest)
    wrap(<MakeYourPick league="ncaaf" game={pregameGame} />)
    expect(await screen.findByRole('link', { name: /create free account/i })).toBeInTheDocument()
  })

  it('refuses to offer a pick once the game has started', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(member)
    wrap(<MakeYourPick league="ncaaf" game={liveGame} />)
    expect(await screen.findByText(/picks are locked/i)).toBeInTheDocument()
  })

  it('submits the line that is on screen, not a refreshed one', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(member)
    const submit = vi.spyOn(api, 'submitPick').mockResolvedValue({} as never)
    const user = userEvent.setup()
    wrap(<MakeYourPick league="ncaaf" game={pregameGame} />)

    await screen.findByRole('tab', { name: 'Spread' })
    await user.click(screen.getByRole('button', { name: new RegExp(pregameGame.home) }))
    await user.click(screen.getByRole('button', { name: /^Publish/ }))

    await waitFor(() => expect(submit).toHaveBeenCalled())
    const body = submit.mock.calls[0][0]
    expect(body.market).toBe('spread')
    expect(body.line).toBe(pregameGame.market_spread)
    expect(body.event_id).toBe(pregameGame.event_id)
  })

  it('blocks a market with no posted line rather than sending an ungradeable pick', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(member)
    const user = userEvent.setup()
    wrap(<MakeYourPick league="ncaaf" game={{ ...pregameGame, market_over_under: null }} />)

    await user.click(await screen.findByRole('tab', { name: 'Total' }))
    await user.click(screen.getByRole('button', { name: /^Over/ }))
    expect(screen.getByText(/couldn’t be graded/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Publish/ })).toBeDisabled()
  })

  it('will not offer a second pick on a market already taken', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(member)
    wrap(<MakeYourPick league="ncaaf" game={pregameGame} existing={[{
      id: 'p1', market: 'spread', selection: 'Florida State +3',
    } as never]} />)
    expect(await screen.findByText(/already published a spread pick/i)).toBeInTheDocument()
  })
})

describe('GameCommunity', () => {
  const base = { game_id: 'ncaaf:1', recent_analysis: [], your_picks: [] }

  it('invites the first analyst rather than inventing a split', () => {
    wrap(<GameCommunity data={{ ...base, total_picks: 0, moneyline_split: {} }}
                        homeAbbr="FSU" awayAbbr="CLEM" />)
    expect(screen.getByText(/be one of the first analysts/i)).toBeInTheDocument()
    expect(screen.queryByText('%')).not.toBeInTheDocument()
  })

  it('shows the split once real picks exist', () => {
    wrap(<GameCommunity data={{ ...base, total_picks: 10, moneyline_split: { home: 70, away: 30 } }}
                        homeAbbr="FSU" awayAbbr="CLEM" />)
    expect(screen.getByText('70%')).toBeInTheDocument()
    expect(screen.getByText(/not a model output/i)).toBeInTheDocument()
  })
})

describe('RecordSummary', () => {
  const empty: PickRecord = {
    picks: 0, pending: 0, graded: 0, wins: 0, losses: 0, pushes: 0,
    win_rate: null, units: 0, roi_pct: null, avg_confidence: null,
  }

  it('shows an em dash rather than 0% for an unsettled account', () => {
    wrap(<RecordSummary record={empty} />)
    // 0% would read as a losing analyst; nothing has settled.
    expect(screen.queryByText('0.0%')).not.toBeInTheDocument()
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })

  it('reports a real record once picks have graded', () => {
    wrap(<RecordSummary record={{
      ...empty, picks: 3, graded: 3, wins: 2, losses: 1,
      win_rate: 0.6667, units: 0.82, roi_pct: 27.3,
    }} />)
    expect(screen.getByText('2-1')).toBeInTheDocument()
    expect(screen.getByText('66.7%')).toBeInTheDocument()
    expect(screen.getByText('+0.82u')).toBeInTheDocument()
  })
})

describe('Partial payloads', () => {
  it('a community response missing its fields does not crash the game page', () => {
    // The screenshot harness caught this against the real bundle: a partial
    // payload threw Object.keys(undefined) and took the whole page down.
    wrap(<GameCommunity data={{} as never} homeAbbr="FSU" awayAbbr="CLEM" />)
    expect(screen.getByText(/be one of the first analysts/i)).toBeInTheDocument()
    expect(screen.getByText(/0 predictions/i)).toBeInTheDocument()
  })
})

describe('Odds attribution', () => {
  it('names the feed, not the sportsbook, as the source', async () => {
    const { oddsSourceLabel } = await import('../components/OddsSource')
    // "DraftKings" alone implies a relationship StatEdge does not have.
    expect(oddsSourceLabel('DraftKings')).toBe('ESPN (DraftKings line)')
    expect(oddsSourceLabel('ESPN BET')).toBe('ESPN (ESPN BET line)')
  })

  it('does not double up when the feed is its own source', async () => {
    const { oddsSourceLabel } = await import('../components/OddsSource')
    expect(oddsSourceLabel('ESPN')).toBe('ESPN')
    expect(oddsSourceLabel('')).toBe('ESPN')
    expect(oddsSourceLabel(null)).toBe('ESPN')
  })

  it('states plainly that there is no sportsbook relationship', async () => {
    const { oddsSourceSentence } = await import('../components/OddsSource')
    expect(oddsSourceSentence('DraftKings')).toContain('no relationship')
  })
})
