import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { WinnerCall } from './WinnerCall'
import type { WinnerOut } from '../../types'

/**
 * The board already said who covers and whether to take the over. It did not
 * say who wins the game, which is the question most people arrive with — and a
 * different question, which routinely has a different answer.
 */
const winner = (over: Partial<WinnerOut> = {}): WinnerOut => ({
  side: 'home', team: 'Chiefs', abbr: 'KC', opponent: 'Ravens',
  win_prob: 0.66, model_prob: 0.70, market_prob: 0.62,
  market_prob_is_implied: false, price_american: -180,
  market_agrees: true, band: 'clear', live: false, graded: true,
  ...over,
})

describe('The outright winner', () => {
  it('names the team and its chance of winning', () => {
    render(<WinnerCall winner={winner()} />)
    expect(screen.getByText('Chiefs')).toBeInTheDocument()
    expect(screen.getByText('66%')).toBeInTheDocument()
    expect(screen.getByText(/wins outright/i)).toBeInTheDocument()
  })

  it('shows the price for the team it named, not the other one', () => {
    render(<WinnerCall winner={winner({ side: 'away', team: 'Ravens', opponent: 'Chiefs', price_american: 155 })} />)
    expect(screen.getByText('+155')).toBeInTheDocument()
  })

  it('says so when the market has the other team', () => {
    // The case the field exists for: a nine-point favourite the model does not
    // expect to win. Burying that would be the whole point missed.
    render(<WinnerCall winner={winner({
      side: 'away', team: 'Ravens', opponent: 'Chiefs',
      market_agrees: false, market_prob_is_implied: true, price_american: null,
    })} />)
    expect(screen.getByText(/market has chiefs/i)).toBeInTheDocument()
  })

  it('separates a spread-implied market read from a quoted price', () => {
    render(<WinnerCall winner={winner({ market_prob_is_implied: true })} />)
    expect(screen.getByText(/from the spread/i)).toBeInTheDocument()
  })

  it('makes clear a live call is not part of the record', () => {
    render(<WinnerCall winner={winner({ live: true, graded: false, model_prob: null })} />)
    expect(screen.getByText(/wins from here/i)).toBeInTheDocument()
    expect(screen.getByText(/live, not graded/i)).toBeInTheDocument()
    expect(screen.queryByText(/wins outright/i)).not.toBeInTheDocument()
  })

  it('does not dress a coin flip up as a call', () => {
    render(<WinnerCall winner={winner({ win_prob: 0.51, band: 'toss-up' })} />)
    expect(screen.getByText(/too close to call/i)).toBeInTheDocument()
  })

  it('says nothing about the market when there is no market', () => {
    render(<WinnerCall winner={winner({ market_agrees: null, market_prob: null, price_american: null })} />)
    expect(screen.getByText(/no market price/i)).toBeInTheDocument()
  })
})
