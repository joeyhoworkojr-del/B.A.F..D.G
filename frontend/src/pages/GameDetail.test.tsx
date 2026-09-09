import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { GameDetail } from './GameDetail'
import { api } from '../api/client'
import { gameDetail, liveGame, pregameGame } from '../test/fixtures'
import { SessionProvider } from '../session/SessionProvider'

// The game page now hosts Make Your Pick, which reads the session. The
// provider resolves to a guest here, which is the state these tests assert
// against anyway.
function renderAt(path: string) {
  return render(
    <SessionProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/game/:league/:eventId" element={<GameDetail />} />
        </Routes>
      </MemoryRouter>
    </SessionProvider>,
  )
}

beforeEach(() => {
  // Session and community are additive on this page; stub them so these tests
  // stay about the Game Center rather than about the network.
  vi.spyOn(api, 'session').mockResolvedValue({
    user: null,
    entitlements: {
      level: 'guest', authenticated: false, beta_open: true,
      features: {}, unavailable_reason: {}, billing_enabled: false, note: '',
    },
  })
  vi.spyOn(api, 'gameCommunity').mockResolvedValue({
    game_id: 'ncaaf:401752', total_picks: 0, moneyline_split: {},
    recent_analysis: [], your_picks: [],
  })
  vi.spyOn(api, 'playByPlay').mockResolvedValue({
    league: 'ncaaf', event_id: '401752', ok: true, fetched_at: new Date().toISOString(), plays: [],
  })
  // Key players sit on the default tab; no test here is about them.
  vi.spyOn(api, 'gameProps').mockRejectedValue(new Error('no projections'))
})
afterEach(() => vi.restoreAllMocks())

describe('Game Center — pregame', () => {
  it('leads with the model insight, not an empty play-by-play', async () => {
    vi.spyOn(api, 'gameDetail').mockResolvedValue(gameDetail())
    renderAt('/game/ncaaf/401752')

    // The headline recommendation is present without any interaction.
    const card = await screen.findByRole('region', { name: /best available edge/i })
    expect(within(card).getByText('FSU +3.0')).toBeInTheDocument()
    expect(within(card).getByText('Model cover probability')).toBeInTheDocument()

    // Play-by-play has its own section rather than sitting under the model,
    // and says plainly that it has nothing yet rather than looking broken.
    await userEvent.click(screen.getByRole('tab', { name: /plays/i }))
    expect(await screen.findByText(/Play-by-play begins at kickoff/i)).toBeInTheDocument()
  })

  it('shows a projected score labelled as a projection, not a live score', async () => {
    vi.spyOn(api, 'gameDetail').mockResolvedValue(gameDetail())
    renderAt('/game/ncaaf/401752')
    expect(await screen.findByText('Projected score')).toBeInTheDocument()
    expect(screen.getByText(/not a live score/i)).toBeInTheDocument()
    expect(screen.getByText('24.9 – 27.4')).toBeInTheDocument()
  })

  it('always shows the source and freshness', async () => {
    vi.spyOn(api, 'gameDetail').mockResolvedValue(gameDetail())
    renderAt('/game/ncaaf/401752')
    // Attributed to the feed we actually use, with the book named only as the
    // line's origin — printing "ESPN BET" alone reads as a partnership.
    expect((await screen.findAllByText('ESPN (ESPN BET line)')).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Updated .* ago/).length).toBeGreaterThan(0)
  })
})

describe('Game Center — market navigation', () => {
  it('honours a deep-linked market', async () => {
    vi.spyOn(api, 'gameDetail').mockResolvedValue(gameDetail())
    renderAt('/game/ncaaf/401752?market=total')
    await waitFor(() =>
      expect(screen.getAllByRole('tab', { name: 'Total' })[0]).toHaveAttribute('aria-selected', 'true'),
    )
  })

  it('"Why this edge?" selects that market and shows its explanation', async () => {
    vi.spyOn(api, 'gameDetail').mockResolvedValue(gameDetail())
    renderAt('/game/ncaaf/401752?market=moneyline')
    await screen.findByRole('region', { name: /best available edge/i })

    await userEvent.click(screen.getByRole('button', { name: /why this edge/i }))

    // Crosses to the Markets section — the explanation is not on the tab the
    // link was clicked from, and scrolling to a node that is not rendered
    // would silently do nothing.
    await waitFor(() =>
      expect(screen.getByRole('tab', { name: /markets/i })).toHaveAttribute('aria-selected', 'true'),
    )
    // ...and lands on the spread market, where the edge actually is.
    await waitFor(() =>
      expect(screen.getAllByRole('tab', { name: 'Spread' })[0]).toHaveAttribute('aria-selected', 'true'),
    )
    expect(screen.getByText('Why this edge?')).toBeInTheDocument()
    expect(screen.getByText(/How grades are calculated/i)).toBeInTheDocument()
    expect(screen.getByText(/Explaining the spread market/i)).toBeInTheDocument()
  })

  it('switching markets swaps the probability being compared', async () => {
    vi.spyOn(api, 'gameDetail').mockResolvedValue(gameDetail())
    renderAt('/game/ncaaf/401752?market=spread&tab=markets')
    expect(await screen.findByText('cover probability')).toBeInTheDocument()

    await userEvent.click(screen.getAllByRole('tab', { name: 'Moneyline' })[0])
    await waitFor(() => expect(screen.getByText('win probability')).toBeInTheDocument())
    expect(screen.queryByText('cover probability')).not.toBeInTheDocument()
  })
})

describe('Game Center — live', () => {
  it('shows live win probability and field position', async () => {
    vi.spyOn(api, 'gameDetail').mockResolvedValue(gameDetail({
      status: 'in', game: liveGame,
      model: { ...gameDetail().model!, live: true, live_home_win: 0.72, time_remaining_pct: 40 },
    }))
    renderAt('/game/ncaaf/401752')
    expect(await screen.findByText('Live win probability')).toBeInTheDocument()
    // Shown twice on purpose: once in the win-probability panel, once beside
    // the live projected final.
    expect(screen.getAllByText('72.0%').length).toBeGreaterThan(0)
    // The field view places the ball and says which way the offence is going.
    expect(screen.getByRole('img', { name: /FSU on the own 42 yard line/i })).toBeInTheDocument()
    expect(screen.getByText(/58 yards from the CLEM end zone/i)).toBeInTheDocument()
  })

  it('says so rather than guessing when the feed omits field position', async () => {
    vi.spyOn(api, 'gameDetail').mockResolvedValue(gameDetail({
      status: 'in',
      game: { ...liveGame, yard_line: null, distance: null },
      model: { ...gameDetail().model!, live: true, live_home_win: 0.72 },
    }))
    renderAt('/game/ncaaf/401752')
    expect(await screen.findByText(/field position not published/i)).toBeInTheDocument()
    expect(screen.queryByRole('img', { name: /yard line/i })).not.toBeInTheDocument()
  })

  it('projects a live final score, flagged as ungraded', async () => {
    vi.spyOn(api, 'gameDetail').mockResolvedValue(gameDetail({
      status: 'in', game: liveGame,
      model: {
        ...gameDetail().model!, live: true, live_home_win: 0.72,
        live_proj_home: 31.4, live_proj_away: 24.1, time_remaining_pct: 40,
      },
    }))
    renderAt('/game/ncaaf/401752')
    expect(await screen.findByText('Projected final')).toBeInTheDocument()
    expect(screen.getByText('24.1 – 31.4')).toBeInTheDocument()
    expect(screen.getByText(/never graded/)).toBeInTheDocument()
  })
})

describe('Game Center — final', () => {
  it('grades the frozen pre-game call against the closing line', async () => {
    vi.spyOn(api, 'gameDetail').mockResolvedValue(gameDetail({
      status: 'post',
      game: { ...liveGame, state: 'post', home_score: 27, away_score: 24 },
      snapshot: {
        event_id: 'ncaaf:401752', model_version: '2026.09.1-gridiron',
        snapshot_at: '2026-09-06T18:00:00Z', model_home_prob: 0.58,
        closing_spread: 3, graded: 1, home_won: 1,
      },
    }))
    renderAt('/game/ncaaf/401752')
    expect(await screen.findByText('Result vs the pre-game call')).toBeInTheDocument()
    expect(screen.getByText('Model correct')).toBeInTheDocument()
    expect(screen.getAllByText('58.0%').length).toBeGreaterThan(0)
    // The stored model version is shown, so a graded call is attributable.
    expect(screen.getAllByText(/2026\.09\.1-gridiron/).length).toBeGreaterThan(0)
  })
})

describe('Game Center — failure handling', () => {
  it('keeps the last good data on screen when a refresh fails', async () => {
    const good = gameDetail()
    const spy = vi.spyOn(api, 'gameDetail')
      .mockResolvedValueOnce(good)
      .mockRejectedValue(new Error('feed down'))

    renderAt('/game/ncaaf/401752')
    const card = await screen.findByRole('region', { name: /best available edge/i })
    expect(within(card).getByText('FSU +3.0')).toBeInTheDocument()

    // Later refreshes fail, but the good data must stay on screen.
    await waitFor(() => expect(spy).toHaveBeenCalled())
    expect(within(card).getByText('FSU +3.0')).toBeInTheDocument()
  })

  it('surfaces a hard failure when nothing has ever loaded', async () => {
    vi.spyOn(api, 'gameDetail').mockRejectedValue(new Error('feed down'))
    renderAt('/game/ncaaf/401752')
    expect(await screen.findByRole('alert')).toHaveTextContent(/feed down|not found/i)
  })

  it('says a matchup is unmapped instead of inventing an edge', async () => {
    vi.spyOn(api, 'gameDetail').mockResolvedValue(gameDetail({
      mapped: false, model: null, markets: [], best_edge: null, game: pregameGame,
    }))
    renderAt('/game/ncaaf/401752')
    expect(await screen.findByText(/isn’t mapped to the model yet/i)).toBeInTheDocument()
  })
})
