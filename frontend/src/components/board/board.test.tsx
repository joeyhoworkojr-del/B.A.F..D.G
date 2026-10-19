import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ValidationNote } from './ValidationNote'
import { GameRow } from './GameRow'
import { LiveStrip } from './LiveStrip'
import { boardEntry } from '../../test/fixtures'
import type { BoardEntry } from '../../types'

const draw = (ui: JSX.Element) => render(<MemoryRouter>{ui}</MemoryRouter>)

/**
 * The board's three new pieces, and in every case what is being protected is
 * the same thing: the row shows a StatEdge number beside the market's, and a
 * reader has to be able to tell a measured disagreement from an unmeasured
 * one and from no model at all.
 */
describe('The board-level validation note', () => {
  it('says the NFL model has no demonstrated edge on game lines', () => {
    draw(<ValidationNote entries={[boardEntry('nfl', { event_id: 'n1' })]} />)
    expect(screen.getByText(/no demonstrated edge on this league/i)).toBeInTheDocument()
    expect(screen.getByText(/less accurate than the closing line/i)).toBeInTheDocument()
  })

  it('says college football is unmeasured rather than implying it is good', () => {
    draw(<ValidationNote entries={[boardEntry('ncaaf', { event_id: 'c1' })]} />)
    expect(screen.getByText(/not yet measured/i)).toBeInTheDocument()
    expect(screen.getByText(/unknown rather than good or bad/i)).toBeInTheDocument()
    // The NFL's measured result is a claim about the NFL. A college-only board
    // must not carry it.
    expect(screen.queryByText(/no demonstrated edge/i)).not.toBeInTheDocument()
  })

  it('covers each league on the board once, not once per game', () => {
    draw(
      <ValidationNote
        entries={[
          boardEntry('nfl', { event_id: 'n1' }),
          boardEntry('nfl', { event_id: 'n2' }),
          boardEntry('ncaaf', { event_id: 'c1' }),
        ]}
      />,
    )
    expect(screen.getAllByText(/no demonstrated edge on this league/i)).toHaveLength(1)
    expect(screen.getAllByText(/not yet measured/i)).toHaveLength(1)
  })

  it('renders nothing when no game on the board carries a measurement', () => {
    const bare: BoardEntry = { ...boardEntry('nfl', { event_id: 'n1' }), value: null }
    const { container } = draw(<ValidationNote entries={[bare]} />)
    expect(container).toBeEmptyDOMElement()
  })
})

describe('A game row', () => {
  it('names the side and the size of a disagreement that clears the threshold', () => {
    draw(<GameRow entry={boardEntry('nfl', { event_id: 'n1' })} />)
    // The fixture has the model 1.8 points off the market.
    expect(screen.getByText(/1\.8 pts on/i)).toBeInTheDocument()
  })

  it('says the model and the market agree rather than inventing a chip', () => {
    const base = boardEntry('nfl', { event_id: 'n1' })
    const entry: BoardEntry = {
      ...base,
      value: { ...base.value!, spread: { ...base.value!.spread, points: null, edge_points: null } },
    }
    draw(<GameRow entry={entry} />)
    expect(screen.getByText(/model and market agree/i)).toBeInTheDocument()
  })

  it('distinguishes a game with no model from one where the two agree', () => {
    const entry: BoardEntry = {
      ...boardEntry('nfl', { event_id: 'n1' }),
      projected: false, mapped: false, model: null, value: null,
    }
    draw(<GameRow entry={entry} />)
    expect(screen.getByText(/not projected yet/i)).toBeInTheDocument()
    expect(screen.queryByText(/model and market agree/i)).not.toBeInTheDocument()
  })

  it('says a line is missing rather than calling the absence agreement', () => {
    const base = boardEntry('nfl', { event_id: 'n1' })
    const entry: BoardEntry = {
      ...base,
      value: {
        ...base.value!,
        spread: { ...base.value!.spread, market: null, market_label: '—', points: null },
      },
    }
    draw(<GameRow entry={entry} />)
    expect(screen.getByText(/no line posted/i)).toBeInTheDocument()
    expect(screen.queryByText(/model and market agree/i)).not.toBeInTheDocument()
  })
})

describe('The live strip', () => {
  it('renders nothing at all when no game is in progress', () => {
    const { container } = draw(<LiveStrip games={[]} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('shows the clock and the score for a game that is on', () => {
    draw(
      <LiveStrip
        games={[boardEntry('nfl', {
          event_id: 'n1', state: 'in', home_score: 21, away_score: 17,
          period: 3, clock: '4:12',
        })]}
      />,
    )
    expect(screen.getByText('Q3 4:12')).toBeInTheDocument()
    expect(screen.getByText('21')).toBeInTheDocument()
  })
})
