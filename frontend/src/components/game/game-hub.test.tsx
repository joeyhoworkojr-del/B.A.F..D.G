import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { MatchupBanner } from './MatchupBanner'
import { WhoWins } from './WhoWins'
import { KeyPlayers } from './KeyPlayers'
import { api } from '../../api/client'
import { liveGame, pregameGame, moneylineMarket, spreadMarket } from '../../test/fixtures'

afterEach(() => vi.restoreAllMocks())

describe('Matchup banner', () => {
  it('shows the kickoff instead of a scoreline before the game starts', () => {
    render(<MatchupBanner game={pregameGame} leagueLabel="College Football" />)
    // A 0–0 before kickoff reads as a game already under way.
    expect(screen.queryByText('0')).not.toBeInTheDocument()
    expect(screen.getByText('Clemson')).toBeInTheDocument()
    expect(screen.getByText('Florida State')).toBeInTheDocument()
    // Both sides are identified. FSU appears twice without a logo — once as
    // the label, once inside the decorative stand-in for the crest.
    expect(screen.getAllByText('FSU').length).toBeGreaterThan(0)
  })

  it('shows the score once the game is under way', () => {
    render(<MatchupBanner game={liveGame} leagueLabel="College Football" />)
    expect(screen.getByText('14')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
  })

  it('shows each team’s record when the feed has one', () => {
    render(
      <MatchupBanner
        game={{ ...pregameGame, home_record: '3-1', away_record: '2-2' }}
        leagueLabel="College Football"
      />,
    )
    expect(screen.getByText('3-1')).toBeInTheDocument()
    expect(screen.getByText('2-2')).toBeInTheDocument()
  })

  it('simply omits a record the feed does not have, rather than inventing 0-0', () => {
    render(<MatchupBanner game={pregameGame} leagueLabel="College Football" />)
    expect(screen.queryByText('0-0')).not.toBeInTheDocument()
  })
})

describe('Who wins', () => {
  const markets = [moneylineMarket, spreadMarket]

  it('puts the model’s number beside the book’s price', () => {
    render(
      <MemoryRouter>
        <WhoWins game={pregameGame} markets={markets} active="moneyline" onChange={() => {}} />
      </MemoryRouter>,
    )
    expect(screen.getByText('FSU ML')).toBeInTheDocument()
    expect(screen.getByText('+130')).toBeInTheDocument()   // the book's price
    expect(screen.getByText('56%')).toBeInTheDocument()    // what the model says
  })

  it('marks the side the model prefers, and only that side', () => {
    render(
      <MemoryRouter>
        <WhoWins game={pregameGame} markets={markets} active="moneyline" onChange={() => {}} />
      </MemoryRouter>,
    )
    expect(screen.getAllByText('Model’s side')).toHaveLength(1)
  })

  it('never suggests a wager is being placed', () => {
    render(
      <MemoryRouter>
        <WhoWins game={pregameGame} markets={markets} active="moneyline" onChange={() => {}} />
      </MemoryRouter>,
    )
    expect(screen.getByText(/does not accept or process wagers/i)).toBeInTheDocument()
  })

  it('reports published picks as picks, not as votes', () => {
    render(
      <MemoryRouter>
        <WhoWins
          game={pregameGame} markets={markets} active="moneyline" onChange={() => {}}
          community={{
            game_id: 'ncaaf:401752', total_picks: 1234,
            moneyline_split: {}, recent_analysis: [], your_picks: [],
          }}
        />
      </MemoryRouter>,
    )
    expect(screen.getByText('1,234 published picks')).toBeInTheDocument()
  })

  it('switches market when another is chosen', async () => {
    const onChange = vi.fn()
    render(
      <MemoryRouter>
        <WhoWins game={pregameGame} markets={markets} active="moneyline" onChange={onChange} />
      </MemoryRouter>,
    )
    await userEvent.click(screen.getByRole('tab', { name: 'Spread' }))
    expect(onChange).toHaveBeenCalledWith('spread')
  })

  it('says the price is assumed when the feed did not publish one', () => {
    render(
      <MemoryRouter>
        <WhoWins game={pregameGame} markets={[spreadMarket]} active="spread" onChange={() => {}} />
      </MemoryRouter>,
    )
    expect(screen.getByText(/Priced at −110 where the feed publishes no price/i)).toBeInTheDocument()
  })
})

describe('Key players', () => {
  const projection = (over: Record<string, unknown>) => ({
    athlete_id: 'a1', player: 'Cade Klubnik', team_abbr: 'CLEM', position: 'QB',
    market: 'pass_yards', label: 'Pass yards', projection: 268.4, season_avg: 254.1,
    games_played: 9, actual: false, ...over,
  })

  const feed = (rows: unknown[], status = 'pre') => ({
    league: 'ncaaf', event_id: '401752', status,
    home: 'Florida State', away: 'Clemson', home_abbr: 'FSU', away_abbr: 'CLEM',
    fetched_at: new Date().toISOString(), source: 'ESPN', source_ok: true,
    model_version: 'x', projected_home_points: 27.4, projected_away_points: 24.9,
    lines_available: false, lines_note: '', projections: rows, note: '',
  })

  beforeEach(() => {
    vi.spyOn(api, 'gameProps').mockResolvedValue(feed([
      projection({}),
      projection({ athlete_id: 'a2', player: 'Tommy Castellanos', team_abbr: 'FSU' }),
      projection({ athlete_id: 'a3', player: 'Phil Mafah', team_abbr: 'CLEM',
                   market: 'rush_yards', label: 'Rush yards', projection: 84.2 }),
    ]) as never)
  })

  it('compares one player a side, by position group', async () => {
    render(<MemoryRouter><KeyPlayers league="ncaaf" eventId="401752" /></MemoryRouter>)
    expect(await screen.findByText('Passing')).toBeInTheDocument()
    expect(screen.getByText('Cade Klubnik')).toBeInTheDocument()
    expect(screen.getByText('Tommy Castellanos')).toBeInTheDocument()
    expect(screen.getByText('Rushing')).toBeInTheDocument()
  })

  it('calls a projection a projection, not a prop line', async () => {
    render(<MemoryRouter><KeyPlayers league="ncaaf" eventId="401752" /></MemoryRouter>)
    expect(await screen.findByText(/not posted prop lines/i)).toBeInTheDocument()
    expect(screen.getAllByText('projected').length).toBeGreaterThan(0)
  })

  it('calls a number from a game in progress what it is — actual, not forecast', async () => {
    vi.spyOn(api, 'gameProps').mockResolvedValue(
      feed([projection({ actual: true })], 'in') as never)
    render(<MemoryRouter><KeyPlayers league="ncaaf" eventId="401752" /></MemoryRouter>)
    expect(await screen.findByText('actual')).toBeInTheDocument()
    expect(screen.getByText(/Actual production so far/i)).toBeInTheDocument()
  })

  it('says there is nothing rather than rendering an empty heading', async () => {
    vi.spyOn(api, 'gameProps').mockRejectedValue(new Error('no source'))
    render(<MemoryRouter><KeyPlayers league="ncaaf" eventId="401752" /></MemoryRouter>)
    expect(await screen.findByText(/No player projections for this game yet/i)).toBeInTheDocument()
  })

  it('links to the full comparison', async () => {
    render(<MemoryRouter><KeyPlayers league="ncaaf" eventId="401752" /></MemoryRouter>)
    const link = await screen.findByRole('link', { name: /full comparison/i })
    expect(link).toHaveAttribute('href', '/props?league=ncaaf&event=401752')
  })
})

describe('Game section tabs', () => {
  it('moves between sections with the arrow keys', async () => {
    const { GameTabs } = await import('./GameTabs')
    const onChange = vi.fn()
    render(
      <GameTabs
        tabs={[
          { key: 'scorecast', label: 'Scorecast' },
          { key: 'markets', label: 'Markets' },
        ]}
        active="scorecast"
        onChange={onChange}
        panelId="p"
      />,
    )
    const list = screen.getByRole('tablist')
    await userEvent.click(within(list).getByRole('tab', { name: 'Scorecast' }))
    await userEvent.keyboard('{ArrowRight}')
    expect(onChange).toHaveBeenCalledWith('markets')
  })
})
