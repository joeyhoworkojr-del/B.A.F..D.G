import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { Dashboard } from './Dashboard'
import { api } from '../api/client'
import { SessionProvider } from '../session/SessionProvider'
import { todayBoard } from '../test/fixtures'

/**
 * The personalised homepage.
 *
 * Team keys are stored as `league:CODE`, which is what keeps a college team
 * from matching an NFL team that shares an abbreviation. These tests are mostly
 * about that boundary and about not showing an empty section as if it were a
 * broken setting.
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

const board = todayBoard('ncaaf')
const firstGame = board.games[0].game

beforeEach(() => {
  vi.spyOn(api, 'accuracy').mockResolvedValue({} as never)
  vi.spyOn(api, 'today').mockResolvedValue(board as never)
})
afterEach(() => vi.restoreAllMocks())

function renderDashboard() {
  return render(
    <SessionProvider>
      <MemoryRouter><Dashboard /></MemoryRouter>
    </SessionProvider>,
  )
}

describe('Homepage personalisation', () => {
  it('shows no Your teams section to a signed-out visitor', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(session(null) as never)
    renderDashboard()
    await screen.findByText('Game Center')
    expect(screen.queryByText(/your teams/i)).not.toBeInTheDocument()
  })

  it('pulls a followed team’s game to the top', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(
      session(profile({ favourite_teams: [`ncaaf:${firstGame.home_abbr}`] })) as never,
    )
    renderDashboard()
    expect(await screen.findByText(/your teams/i)).toBeInTheDocument()
  })

  it('does not match a team from another league that shares an abbreviation', async () => {
    // The same code, but keyed to the NFL board rather than the college one.
    vi.spyOn(api, 'session').mockResolvedValue(
      session(profile({ favourite_teams: [`nfl:${firstGame.home_abbr}`] })) as never,
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

  it('opens on the league the person follows', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(
      session(profile({ favourite_sports: ['nfl'] })) as never,
    )
    renderDashboard()
    await waitFor(() => expect(api.today).toHaveBeenCalledWith('nfl'))
  })

  it('following both leagues says nothing about which board to open', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(
      session(profile({ favourite_sports: ['nfl', 'ncaaf'] })) as never,
    )
    renderDashboard()
    await screen.findByText('Game Center')
    expect(api.today).not.toHaveBeenCalledWith('nfl')
  })
})
