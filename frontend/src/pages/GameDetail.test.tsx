import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { GameDetail } from './GameDetail'
import { api } from '../api/client'
import { gameDetail, liveGame, pregameGame } from '../test/fixtures'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/game/:league/:eventId" element={<GameDetail />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.spyOn(api, 'playByPlay').mockResolvedValue({
    league: 'ncaaf', event_id: '401752', ok: true, fetched_at: new Date().toISOString(), plays: [],
  })
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

    // Play-by-play is present but explicitly empty until kickoff.
    expect(screen.getByText(/Play-by-play begins at kickoff/i)).toBeInTheDocument()
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
    expect((await screen.findAllByText('ESPN BET')).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Updated .* ago/).length).toBeGreaterThan(0)
  })
})

describe('Game Center — market navigation', () => {
  it('honours a deep-linked market', async () => {
    vi.spyOn(api, 'gameDetail').mockResolvedValue(gameDetail())
    renderAt('/game/ncaaf/401752?market=total')
    await waitFor(() =>
      expect(screen.getByRole('tab', { name: 'Total' })).toHaveAttribute('aria-selected', 'true'),
    )
  })

  it('"Why this edge?" selects that market and shows its explanation', async () => {
    vi.spyOn(api, 'gameDetail').mockResolvedValue(gameDetail())
    renderAt('/game/ncaaf/401752?market=moneyline')
    await screen.findByRole('region', { name: /best available edge/i })

    await userEvent.click(screen.getByRole('button', { name: /why this edge/i }))

    // Jumps to the spread market (where the edge is) and explains it.
    await waitFor(() =>
      expect(screen.getByRole('tab', { name: 'Spread' })).toHaveAttribute('aria-selected', 'true'),
    )
    expect(screen.getByText('Why this edge?')).toBeInTheDocument()
    expect(screen.getByText(/How grades are calculated/i)).toBeInTheDocument()
    expect(screen.getByText(/Explaining the spread market/i)).toBeInTheDocument()
  })

  it('switching markets swaps the probability being compared', async () => {
    vi.spyOn(api, 'gameDetail').mockResolvedValue(gameDetail())
    renderAt('/game/ncaaf/401752?market=spread')
    expect(await screen.findByText('cover probability')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('tab', { name: 'Moneyline' }))
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
    expect(screen.getByText('72.0%')).toBeInTheDocument()
    expect(screen.getByText('FSU has the ball')).toBeInTheDocument()
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
