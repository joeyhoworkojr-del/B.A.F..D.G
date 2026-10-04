import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { KeyPlayers } from './KeyPlayers'
import { api } from '../../api/client'
import type { GamePropsOut, PropProjectionOut } from '../../types'

/**
 * A projection with nothing behind it is an assertion.
 *
 * The spread is the part that matters: the whole over/under probability comes
 * out of it, and two players with the same average and different spreads are
 * not the same bet. So the page has to say whether the spread shown is the
 * player's own or a league-wide stand-in.
 */
const projection = (over: Partial<PropProjectionOut> = {}): PropProjectionOut => ({
  athlete_id: 'nflverse:1', player: 'J. Allen', team_abbr: 'BUF', position: 'QB',
  market: 'pass_yards', label: 'Passing yards',
  projection: 303.1, season_avg: 255, games_played: 8, actual: false,
  recent_avg: 306.2, form_weight: 0.45,
  environment_mult: 1.09, opponent_abbr: 'MIA', opponent_mult: 0.95,
  opponent_note: 'MIA rated 4 of 32',
  sigma: 61.1, sigma_source: 'player', sigma_games: 8,
  game_log: [{ season: 2026, week: 1, opponent: 'MIA', value: 210 }],
  ...over,
})

const feed = (rows: PropProjectionOut[], over: Partial<GamePropsOut> = {}): GamePropsOut => ({
  league: 'nfl', event_id: '1', status: 'pre',
  home: 'Buffalo Bills', away: 'Miami Dolphins',
  home_abbr: 'BUF', away_abbr: 'MIA',
  fetched_at: new Date().toISOString(), source: 'ESPN + nflverse 2026',
  source_ok: true, model_version: 'v1',
  projected_home_points: 27, projected_away_points: 21,
  lines_available: false, lines_note: '', projections: rows, note: '',
  ...over,
})

const show = () => render(
  <MemoryRouter><KeyPlayers league="nfl" eventId="1" /></MemoryRouter>,
)

afterEach(() => vi.restoreAllMocks())

describe('What a projection is made of', () => {
  it('shows the season average and where recent form moved it', async () => {
    vi.spyOn(api, 'gameProps').mockResolvedValue(feed([projection()]) as never)
    show()
    expect(await screen.findByText('303.1')).toBeInTheDocument()
    expect(screen.getByText(/season 255\.0/)).toBeInTheDocument()
    expect(screen.getByText(/last games 306\.2/)).toBeInTheDocument()
  })

  it('says when the spread is the player’s own, and over how many games', async () => {
    vi.spyOn(api, 'gameProps').mockResolvedValue(feed([projection()]) as never)
    show()
    await screen.findByText('303.1')
    expect(screen.getByText(/± 61\.1 over 8 games/)).toBeInTheDocument()
  })

  it('says when the spread is a league-wide stand-in instead', async () => {
    // The honest distinction: a short log means we are using an average for
    // the market, not this player's volatility, and that changes how much the
    // over/under probability is worth.
    vi.spyOn(api, 'gameProps').mockResolvedValue(
      feed([projection({ sigma_source: 'market', sigma_games: 2, sigma: 76.5 })]) as never,
    )
    show()
    await screen.findByText('303.1')
    expect(screen.getByText(/market average spread/)).toBeInTheDocument()
  })

  it('shows the opponent adjustment with its direction', async () => {
    vi.spyOn(api, 'gameProps').mockResolvedValue(feed([projection()]) as never)
    show()
    await screen.findByText('303.1')
    expect(screen.getByText(/vs MIA −5%/)).toBeInTheDocument()
  })

  it('explains nothing for a line that already happened', async () => {
    // An actual is a fact. There is no projection to justify.
    vi.spyOn(api, 'gameProps').mockResolvedValue(
      feed([projection({ actual: true, recent_avg: null, form_weight: 0 })], { status: 'in' }) as never,
    )
    show()
    expect(await screen.findByText('actual')).toBeInTheDocument()
    expect(screen.queryByText(/season 255/)).not.toBeInTheDocument()
  })

  it('stays quiet when there is nothing extra to say', async () => {
    vi.spyOn(api, 'gameProps').mockResolvedValue(
      feed([projection({
        recent_avg: null, form_weight: 0, opponent_mult: 1,
        sigma: null, sigma_source: 'none', sigma_games: 0,
      })]) as never,
    )
    show()
    await screen.findByText('303.1')
    expect(screen.queryByText(/±/)).not.toBeInTheDocument()
  })
})
