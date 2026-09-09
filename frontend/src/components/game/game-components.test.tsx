import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MatchupBanner } from './MatchupBanner'
import { GameStatus } from './GameStatus'
import { MarketSelector } from './MarketSelector'
import { ProbabilityComparison } from './ProbabilityComparison'
import { PrimaryEdgeCard } from './PrimaryEdgeCard'
import { SportsbookOddsTable } from './SportsbookOddsTable'
import { DataFreshnessBadge } from './DataFreshnessBadge'
import { Panel } from './Panel'
import { LineMovementChart } from './LineMovementChart'
import {
  pregameGame, liveGame, spreadMarket, moneylineMarket, totalMarket,
  gradeScale, gameDetail,
} from '../../test/fixtures'

describe('MatchupBanner / GameStatus', () => {
  it('never shows a 0–0 scoreline before kickoff', () => {
    render(<MatchupBanner game={pregameGame} leagueLabel="College Football" />)
    // The middle column carries the kickoff instead of a scoreline, so
    // nothing reads as a game already under way.
    expect(screen.getByText(/Sep|Oct|Nov|Dec|Jan/)).toBeInTheDocument()
    expect(screen.queryByText('0')).not.toBeInTheDocument()
  })

  it('shows a countdown to kickoff', () => {
    render(<GameStatus game={pregameGame} />)
    expect(screen.getByText(/kickoff in/i)).toBeInTheDocument()
  })

  it('shows score, clock, possession and down/distance when live', () => {
    render(<MatchupBanner game={liveGame} leagueLabel="College Football" />)
    expect(screen.getByText('LIVE')).toBeInTheDocument()
    expect(screen.getByText('Q3 6:59')).toBeInTheDocument()
    expect(screen.getByText('FSU ball')).toBeInTheDocument()
    expect(screen.getByText('1st & 10 at FSU 42')).toBeInTheDocument()
    expect(screen.getByText('14')).toBeInTheDocument()
  })

  it('marks a finished game as final', () => {
    render(<GameStatus game={{ ...liveGame, state: 'post' }} />)
    expect(screen.getByText('Final')).toBeInTheDocument()
  })
})

describe('MarketSelector', () => {
  const markets = [moneylineMarket, spreadMarket, totalMarket]

  it('exposes tablist semantics with the active tab selected', () => {
    render(<MarketSelector markets={markets} active="spread" onChange={() => {}} panelId="p" />)
    expect(screen.getByRole('tablist', { name: /betting market/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Spread' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tab', { name: 'Moneyline' })).toHaveAttribute('aria-selected', 'false')
  })

  it('moves between markets with the arrow keys', async () => {
    const onChange = vi.fn()
    render(<MarketSelector markets={markets} active="spread" onChange={onChange} panelId="p" />)
    const tab = screen.getByRole('tab', { name: 'Spread' })
    tab.focus()
    await userEvent.keyboard('{ArrowRight}')
    expect(onChange).toHaveBeenCalledWith('total')
    await userEvent.keyboard('{Home}')
    expect(onChange).toHaveBeenCalledWith('moneyline')
  })
})

describe('Probability labelling', () => {
  it('names cover probability so it cannot be read as a win probability', () => {
    render(<ProbabilityComparison market={spreadMarket} />)
    expect(screen.getByText(/cover probability/i)).toBeInTheDocument()
    expect(screen.queryByText(/win probability/i)).not.toBeInTheDocument()
  })

  it('names win probability on the moneyline', () => {
    render(<ProbabilityComparison market={moneylineMarket} />)
    expect(screen.getByText(/win probability/i)).toBeInTheDocument()
  })

  it('compares model, sportsbook and crowd', () => {
    render(<ProbabilityComparison market={moneylineMarket} />)
    expect(screen.getAllByText('StatEdge').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Sportsbook').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Crowd').length).toBeGreaterThan(0)
  })

  it('omits the crowd row rather than inventing one', () => {
    render(<ProbabilityComparison market={spreadMarket} />)
    expect(screen.queryByText('Crowd')).not.toBeInTheDocument()
    expect(screen.getByText(/No prediction-market quote/i)).toBeInTheDocument()
  })

  it('spells out percentage points', () => {
    render(<ProbabilityComparison market={spreadMarket} />)
    expect(screen.getAllByText(/percentage points vs book/i).length).toBe(2)
  })
})

describe('PrimaryEdgeCard', () => {
  const edge = gameDetail().best_edge!

  it('puts the recommendation, price, edge and fair price above the fold', () => {
    render(<PrimaryEdgeCard edge={edge} gradeScale={gradeScale} fetchedAt={new Date().toISOString()} />)
    expect(screen.getByText('FSU +3.0')).toBeInTheDocument()
    expect(screen.getByText('66.0%')).toBeInTheDocument()          // model cover prob
    expect(screen.getByText('50.2%')).toBeInTheDocument()          // no-vig book prob
    expect(screen.getByText('+15.8')).toBeInTheDocument()          // edge
    expect(screen.getByText('percentage points')).toBeInTheDocument()
    expect(screen.getByText('Model cover probability')).toBeInTheDocument()
    expect(screen.getByText(/-110/)).toBeInTheDocument()           // current price
  })

  it('explains the grade rather than showing a bare letter', () => {
    render(<PrimaryEdgeCard edge={edge} gradeScale={gradeScale} />)
    expect(screen.getByText('A')).toBeInTheDocument()
    expect(screen.getByText('Strong')).toBeInTheDocument()
  })

  it('flags an assumed price honestly', () => {
    render(<PrimaryEdgeCard edge={edge} gradeScale={gradeScale} />)
    expect(screen.getByText(/assumed — no quoted price/i)).toBeInTheDocument()
  })

  it('says so plainly when there is no edge', () => {
    render(<PrimaryEdgeCard edge={null} gradeScale={gradeScale} />)
    expect(screen.getByText(/agrees with the market/i)).toBeInTheDocument()
  })

  it('calls back with the market to explain', async () => {
    const onExplain = vi.fn()
    render(<PrimaryEdgeCard edge={edge} gradeScale={gradeScale} onExplain={onExplain} />)
    await userEvent.click(screen.getByRole('button', { name: /why this edge/i }))
    expect(onExplain).toHaveBeenCalledWith('spread')
  })
})

describe('SportsbookOddsTable', () => {
  it('shows price, model probability, no-vig book probability and fair price', () => {
    render(<SportsbookOddsTable market={spreadMarket} />)
    expect(screen.getByRole('columnheader', { name: /model cover %/i })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: /book \(no vig\)/i })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: /fair price/i })).toBeInTheDocument()
    expect(screen.getByRole('rowheader', { name: 'FSU +3.0' })).toBeInTheDocument()
  })

  it('states that edge is measured in percentage points', () => {
    render(<SportsbookOddsTable market={totalMarket} />)
    expect(screen.getByText(/percentage points of probability/i)).toBeInTheDocument()
  })
})

describe('DataFreshnessBadge', () => {
  it('always shows the source and age', () => {
    render(<DataFreshnessBadge fetchedAt={new Date().toISOString()} source="ESPN BET" />)
    expect(screen.getByText('ESPN BET')).toBeInTheDocument()
    expect(screen.getByText(/Updated .* ago/)).toBeInTheDocument()
  })

  it('warns when the data is stale', () => {
    const old = new Date(Date.now() - 10 * 60_000).toISOString()
    render(<DataFreshnessBadge fetchedAt={old} source="ESPN BET" staleAfterSeconds={60} />)
    expect(screen.getByText(/^Stale ·/)).toBeInTheDocument()
  })

  it('says it is showing last-good data when the feed is down', () => {
    render(<DataFreshnessBadge fetchedAt={new Date().toISOString()} source="ESPN" ok={false} />)
    expect(screen.getByText(/last good data/i)).toBeInTheDocument()
  })
})

describe('Panel data states', () => {
  it('renders a loading state', () => {
    render(<Panel title="Markets" state="loading" />)
    expect(screen.getByTestId('panel-loading')).toBeInTheDocument()
  })

  it('renders an error state as an alert', () => {
    render(<Panel title="Markets" state="error" errorMessage="Feed down" />)
    expect(screen.getByRole('alert')).toHaveTextContent('Feed down')
  })

  it('explains an empty state', () => {
    render(<Panel title="Markets" state="empty" emptyMessage="No lines posted yet." />)
    expect(screen.getByText('No lines posted yet.')).toBeInTheDocument()
  })
})

describe('LineMovementChart', () => {
  it('refuses to plot a line it has not observed', () => {
    render(<LineMovementChart points={[{ t: 0, v: 3 }]} label="Spread" />)
    expect(screen.getByText(/history isn’t recorded yet/i)).toBeInTheDocument()
  })

  it('plots real movement when two readings exist', () => {
    render(<LineMovementChart points={[{ t: 0, v: 3 }, { t: 1, v: 4.5 }]} label="Spread" />)
    expect(screen.getByRole('img', { name: /spread movement/i })).toBeInTheDocument()
    expect(screen.getByText(/\(\+1.5\)/)).toBeInTheDocument()
  })
})
