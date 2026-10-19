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
    // A team now appears twice on its card — in the matchup, and again as the
    // side named to win outright — so these count rather than expect one.
    expect((await screen.findAllByText('Chiefs')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('Florida State').length).toBeGreaterThan(0)
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
    expect((await screen.findAllByText('Chiefs')).length).toBeGreaterThan(0)
    expect(screen.queryAllByText('Florida State')).toHaveLength(0)

    await userEvent.click(screen.getByRole('tab', { name: /saturday 12 sep/i }))
    expect((await screen.findAllByText('Florida State')).length).toBeGreaterThan(0)
    expect(screen.queryAllByText('Chiefs')).toHaveLength(0)
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

  it('frames the board with what the backtest found, before the first row', async () => {
    // Every row shows a StatEdge line beside the market's. The measurement
    // behind those lines is on the board itself, not only on the game page a
    // tap away, and it is above the rows rather than under them.
    renderDashboard()
    const note = await screen.findByText(/no demonstrated edge on this league/i)
    const firstRow = screen.getAllByText(/StatEdge/)[0]
    expect(note.compareDocumentPosition(firstRow) & Node.DOCUMENT_POSITION_FOLLOWING)
      .toBeTruthy()
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

describe('An empty board', () => {
  it('does not claim nothing is scheduled when the feed is down', async () => {
    // The screenshot version of this bug: a Thursday in September, the NFL
    // playing on Sunday, and the page asserting "No games scheduled in the
    // next 8 days" because it could not reach the schedule at all.
    vi.spyOn(api, 'board').mockResolvedValue({
      ...mergedBoard([]),
      source_ok: false,
      note: 'The live schedule feed is unreachable, so what is on cannot be listed right now.',
    } as never)

    renderDashboard()

    expect(await screen.findByText('Schedule feed is unreachable')).toBeInTheDocument()
    expect(screen.queryByText(/no games scheduled/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/nothing on the board/i)).not.toBeInTheDocument()
  })

  it('still says so plainly when the schedule really is empty', async () => {
    vi.spyOn(api, 'board').mockResolvedValue({
      ...mergedBoard([]),
      source_ok: true,
      note: 'No games scheduled in the next 8 days.',
    } as never)

    renderDashboard()

    expect(await screen.findByText(/nothing on the board/i)).toBeInTheDocument()
    expect(screen.getByText(/no games scheduled in the next 8 days/i)).toBeInTheDocument()
  })

  it('offers a retry when the feed is the problem', async () => {
    const board = vi.spyOn(api, 'board').mockResolvedValue({
      ...mergedBoard([]), source_ok: false, note: 'Feed unreachable.',
    } as never)

    renderDashboard()
    const retry = await screen.findByRole('button', { name: /try again/i })
    await userEvent.click(retry)

    await waitFor(() => expect(board.mock.calls.length).toBeGreaterThan(1))
  })
})

describe('The headline record', () => {
  const withPerformance = (perf: Record<string, unknown>) => {
    vi.spyOn(api, 'accuracy').mockResolvedValue({ performance: perf } as never)
    renderDashboard()
  }

  it('states the win/loss split rather than inferring it from a rounded rate', async () => {
    withPerformance({ total_picks: 103, wins: 88, losses: 15, win_rate: 88 / 103, roi_pct: null })
    expect(await screen.findByText('88–15')).toBeInTheDocument()
  })

  it('says what the record counts rather than calling it accuracy', async () => {
    // "Accuracy 85%" reads as "StatEdge is right 85% of the time", and a
    // record sitting beside an ROI reads as a betting record. It is neither:
    // it counts how often the side the model favoured won.
    withPerformance({ total_picks: 103, wins: 88, losses: 15, win_rate: 88 / 103, roi_pct: null })
    expect(await screen.findByText(/the side the model favoured won/i)).toBeInTheDocument()
    expect(screen.queryByText(/^accuracy$/i)).not.toBeInTheDocument()
  })

  it('links to the full record so the headline figure can be checked', async () => {
    withPerformance({ total_picks: 103, wins: 88, losses: 15, win_rate: 88 / 103, roi_pct: null })
    const link = await screen.findByRole('link', { name: /full record/i })
    expect(link).toHaveAttribute('href', '/results')
  })

  it('says why ROI is blank instead of leaving a bare dash', async () => {
    withPerformance({ total_picks: 103, wins: 88, losses: 15, win_rate: 88 / 103, roi_pct: null })
    expect(await screen.findByText(/needs a published price/i)).toBeInTheDocument()
    expect(screen.getByText(/not a betting return/i)).toBeInTheDocument()
  })

  it('reports closing line value against the number of games it is averaged over', async () => {
    // An average of +0.4 points over nine games and over nine hundred are
    // very different claims, so the denominator ships with the figure.
    withPerformance({
      total_picks: 103, wins: 88, losses: 15, win_rate: 88 / 103, roi_pct: null,
      avg_clv_points: 0.42, clv_tracked: 61,
    })
    expect(await screen.findByText('+0.42')).toBeInTheDocument()
    expect(screen.getByText(/61 tracked/i)).toBeInTheDocument()
  })

  it('does not show a closing line value it has not measured', async () => {
    withPerformance({ total_picks: 103, wins: 88, losses: 15, win_rate: 88 / 103, roi_pct: null })
    expect(await screen.findByText(/not tracked yet/i)).toBeInTheDocument()
  })

  it('drops the ROI caveat once there is a real return to show', async () => {
    withPerformance({
      total_picks: 103, wins: 88, losses: 15, win_rate: 88 / 103,
      priced_picks: 103, roi_pct: 4.2,
    })
    expect(await screen.findByText('+4.2%')).toBeInTheDocument()
    expect(screen.queryByText(/needs a published price/i)).not.toBeInTheDocument()
  })

  it('says nothing at all about a record it does not have', async () => {
    withPerformance({ total_picks: 0, wins: 0, losses: 0, win_rate: null, roi_pct: null })
    expect(await screen.findByText('0–0')).toBeInTheDocument()
    expect(screen.queryByText(/not a betting return/i)).not.toBeInTheDocument()
  })
})
