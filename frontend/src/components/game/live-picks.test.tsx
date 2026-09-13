import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { BestLivePicks, livePicks } from './BestLivePicks'
import { boardEntry } from '../../test/fixtures'
import type { BoardEntry, LiveReadOut } from '../../types'

function live(id: string, read: Partial<LiveReadOut> | null, state = 'in'): BoardEntry {
  const base = boardEntry('nfl', {
    event_id: id, state: state as 'in', home_score: 7, away_score: 28, period: 3,
  })
  return {
    ...base,
    model: {
      ...base.model!,
      live_read: read && {
        team: 'BAL', side: 'away', model_prob: 0.88, market_prob: 0.70,
        edge_pp: 18, market_repriced: true, actionable: true,
        model_move_pp: 52, market_move_pp: 40, note: '', graded: false,
        ...read,
      },
    },
  }
}

const show = (entries: BoardEntry[]) =>
  render(<MemoryRouter><BestLivePicks entries={entries} /></MemoryRouter>)

describe('Best live picks', () => {
  it('ranks a live disagreement with a repricing book', () => {
    show([live('1', {})])
    expect(screen.getByText('BAL')).toBeInTheDocument()
    expect(screen.getByText('88%')).toBeInTheDocument()   // the model
    expect(screen.getByText('70%')).toBeInTheDocument()   // the live price
  })

  it('never ranks a game whose book is still on the pre-game line', () => {
    // The trap: a stale price against a live model looks like the biggest edge
    // on the board and is entirely fictional.
    const stale = live('1', {
      market_repriced: false, actionable: false, edge_pp: 49.6,
      market_move_pp: 2.4,
    })
    expect(livePicks([stale])).toHaveLength(0)
  })

  it('says how many live games were withheld, and why', () => {
    show([live('1', { market_repriced: false, actionable: false })])
    expect(screen.getByText(/1 other live game is not listed/i)).toBeInTheDocument()
    expect(screen.getByText(/has not moved since kickoff/i)).toBeInTheDocument()
  })

  it('states plainly that live reads are not part of the track record', () => {
    // A section headed "best picks" invites exactly the assumption that would
    // be wrong to allow: these are never frozen and never graded.
    show([live('1', {})])
    expect(screen.getByText(/not frozen and not graded/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /track record/i }))
      .toHaveAttribute('href', '/results')
  })

  it('says so when the model agrees with every live price', () => {
    show([live('1', { actionable: false })])
    expect(screen.getByText(/No live pick right now/i)).toBeInTheDocument()
  })

  it('renders nothing at all when no game is in progress', () => {
    const { container } = show([live('1', {}, 'pre')])
    expect(container).toBeEmptyDOMElement()
  })

  it('leads with the biggest live edge', () => {
    const entries = [
      live('small', { edge_pp: 8, team: 'SMALL' }),
      live('big', { edge_pp: 25, team: 'BIG' }),
    ]
    expect(livePicks(entries)[0].model!.live_read!.team).toBe('BIG')
  })

  it('stays short rather than listing every live game', () => {
    show(['1', '2', '3', '4', '5'].map(id => live(id, {})))
    expect(screen.getAllByRole('listitem')).toHaveLength(3)
  })
})
