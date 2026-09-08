import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { Dashboard } from './Dashboard'
import { api } from '../api/client'
import { SessionProvider } from '../session/SessionProvider'
import { boardEntry, mergedBoard } from '../test/fixtures'

/**
 * The homepage: one board across both leagues.
 *
 * Two things are being protected here. First, that NFL and college football
 * are not two tabs one of which is usually empty — a Wednesday has one NFL
 * game and no college football, and the board should open on the next day that
 * has something on it. Second, that team keys stay `league:CODE`, which is what
 * keeps a college team from matching an NFL team sharing an abbreviation.
 */
function profile(overrides: Record<string, unknown> = {}) {
  return {
    id: 'u1', username: 'fan', display_name: 'Fan', bio: '', avatar_url: '',
    favourite_sports: [], favourite_teams: [], badges: [],
    created_at: '2026-01-01T00:00:00Z', email: 'f@e.com', email_verified: false,
    level: 'beta', interests: [], onboarded: true, profile_public: true,
    ...overrides,
  }
}

function session(user: Record<string, unknown> | null) {
  return {
    user,
    entitlements: {
      level: user ? 'beta' : 'guest', powers: [], authenticated: !!user,
      beta_open: true, features: {}, unavailable_reason: {},
      billing_enabled: false, note: '',
    },
  }
}

beforeEach(() => {
  vi.spyOn(api, 'accuracy').mockResolvedValue({} as never)
  vi.spyOn(api, 'board').mockResolvedValue(mergedBoard() as never)
  // Props are fetched for the featured game; nothing here is about them.
  vi.spyOn(api, 'gameProps').mockRejectedValue(new Error('no props'))
  vi.spyOn(api, 'session').mockResolvedValue(session(null) as never)
})
afterEach(() => vi.restoreAllMocks())

function renderDashboard() {
  return render(
    <SessionProvider>
      <MemoryRouter><Dashboard /></MemoryRouter>
    </SessionProvider>,
  )
}

describe('The merged board', () => {
  it('shows NFL and college games together, not on separate tabs', async () => {
    renderDashboard()
    expect(await screen.findByText('Chiefs')).toBeInTheDocument()
    expect(screen.getByText('Florida State')).toBeInTheDocument()
    expect(screen.getAllByText('NFL').length).toBeGreaterThan(0)
    expect(screen.getAllByText('NCAAF').length).toBeGreaterThan(0)
  })

  it('opens on the next day that has football when today is empty', async () => {
    renderDashboard()
    // The fixture's only day is tomorrow; the board opens there rather than
    // rendering an empty Today.
    const tab = await screen.findByRole('tab', { name: /tomorrow/i })
    expect(tab).toHaveAttribute('aria-selected', 'true')
  })

  it('lets you move to another day', async () => {
    vi.spyOn(api, 'board').mockResolvedValue(mergedBoard([
      {
        date: '2026-09-09', label: 'Today', live: 0, by_league: { nfl: 1, ncaaf: 0 },
        games: [boardEntry('nfl', { event_id: 'n1', home: 'Chiefs', away: 'Ravens', home_abbr: 'KC', away_abbr: 'BAL' })],
      },
      {
        date: '2026-09-12', label: 'Saturday 12 Sep', live: 0, by_league: { nfl: 0, ncaaf: 1 },
        games: [boardEntry('ncaaf', { event_id: 'c1' })],
      },
    ]) as never)
    renderDashboard()
    expect(await screen.findByText('Chiefs')).toBeInTheDocument()
    expect(screen.queryByText('Florida State')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('tab', { name: /saturday 12 sep/i }))
    expect(await screen.findByText('Florida State')).toBeInTheDocument()
    expect(screen.queryByText('Chiefs')).not.toBeInTheDocument()
  })

  it('sorts a live game above the rest of its day', async () => {
    vi.spyOn(api, 'board').mockResolvedValue(mergedBoard([{
      date: '2026-09-09', label: 'Today', live: 1, by_league: { nfl: 1, ncaaf: 1 },
      games: [
        boardEntry('ncaaf', { event_id: 'c1' }),
        boardEntry('nfl', {
          event_id: 'n1', home: 'Chiefs', away: 'Ravens', home_abbr: 'KC', away_abbr: 'BAL',
          state: 'in', home_score: 21, away_score: 17, period: 3, clock: '4:12',
        }),
      ],
    }]) as never)
    renderDashboard()
    const names = await screen.findAllByText(/Chiefs|Florida State/)
    expect(names[0]).toHaveTextContent('Chiefs')
    expect(screen.getAllByText(/LIVE/).length).toBeGreaterThan(0)
  })

  it('says plainly when there is nothing scheduled at all', async () => {
    vi.spyOn(api, 'board').mockResolvedValue({
      ...mergedBoard([]),
      note: 'No games scheduled in the next 8 days.',
    } as never)
    renderDashboard()
    expect(await screen.findByText(/nothing on the board/i)).toBeInTheDocument()
    expect(screen.getByText(/no games scheduled in the next 8 days/i)).toBeInTheDocument()
  })

  it('marks a game the model has not been run on, rather than claiming no edge', async () => {
    vi.spyOn(api, 'board').mockResolvedValue(mergedBoard([{
      date: '2026-09-09', label: 'Today', live: 0, by_league: { nfl: 0, ncaaf: 1 },
      games: [{ ...boardEntry('ncaaf', { event_id: 'c1' }), projected: false, mapped: false, model: null }],
    }]) as never)
    renderDashboard()
    expect(await screen.findByText(/not projected yet/i)).toBeInTheDocument()
    expect(screen.queryByText(/no edge is claimed/i)).not.toBeInTheDocument()
  })
})

describe('Homepage personalisation', () => {
  it('shows no Your teams section to a signed-out visitor', async () => {
    renderDashboard()
    await screen.findByText('Game Center')
    expect(screen.queryByText(/your teams/i)).not.toBeInTheDocument()
  })

  it('pulls a followed team’s game into its own section', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(
      session(profile({ favourite_teams: ['nfl:KC'] })) as never,
    )
    renderDashboard()
    expect(await screen.findByText(/your teams/i)).toBeInTheDocument()
  })

  it('does not match a team from another league that shares an abbreviation', async () => {
    // FSU plays on the college board; the same code keyed to the NFL must not
    // pull it in.
    vi.spyOn(api, 'session').mockResolvedValue(
      session(profile({ favourite_teams: ['nfl:FSU'] })) as never,
    )
    renderDashboard()
    await screen.findByText('Game Center')
    await waitFor(() =>
      expect(screen.queryByText(/^your teams$/i)).not.toBeInTheDocument())
  })

  it('says so when a followed team simply is not playing, rather than showing nothing', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(
      session(profile({ favourite_teams: ['ncaaf:NOTPLAYING'] })) as never,
    )
    renderDashboard()
    expect(await screen.findByText(/none of the teams you follow/i)).toBeInTheDocument()
  })
})
