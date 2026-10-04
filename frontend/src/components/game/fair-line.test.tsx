import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { FairLine } from './FairLine'
import { WhyThisEdge } from './WhyThisEdge'
import type { ValueOut, WhyOut } from '../../types'

const value = (over: Partial<ValueOut> = {}): ValueOut => ({
  spread: {
    fair: -4.8, fair_label: 'BUF -4.8', market: -3.5, market_label: 'BUF -3.5',
    edge_points: 1.3, side: 'home', side_abbr: 'BUF', points: 1.3,
  },
  total: { fair: 48.3, market: 46.5, edge_points: 1.8, side: 'over', points: 1.8 },
  confidence: {
    level: 'high', inputs_present: 4, inputs_total: 4, inputs: [],
    means: "How much of the model's input was available for this game. Not the chance a bet wins.",
  },
  ...over,
})

describe('Fair line against the market', () => {
  it('shows all three numbers, in that order', () => {
    render(<FairLine value={value()} />)
    expect(screen.getByText('BUF -4.8')).toBeInTheDocument()
    expect(screen.getByText('BUF -3.5')).toBeInTheDocument()
    expect(screen.getByText(/\+1\.3/)).toBeInTheDocument()
    expect(screen.getByText(/pts BUF/)).toBeInTheDocument()
  })

  it('never lets confidence read as a chance of winning', () => {
    render(<FairLine value={value()} />)
    expect(screen.getByText(/high/i)).toBeInTheDocument()
    expect(screen.getByText(/not the chance a bet wins/i)).toBeInTheDocument()
  })

  it('renders nothing when the market has published no line to compare', () => {
    const { container } = render(<FairLine value={value({
      spread: { fair: -4.8, fair_label: 'BUF -4.8', market: null, market_label: '', edge_points: null, side: null, side_abbr: '', points: null },
      total: { fair: 48.3, market: null, edge_points: null, side: null, points: null },
    })} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('shows the total comparison separately from the spread', () => {
    render(<FairLine value={value()} />)
    expect(screen.getByText(/48\.3/)).toBeInTheDocument()
    expect(screen.getByText(/over/)).toBeInTheDocument()
  })
})

const why = (over: Partial<WhyOut> = {}): WhyOut => ({
  fair_label: 'BUF -4.8', side: 'home', side_abbr: 'BUF', points: 1.3,
  line: {
    opening: -2.5, current: -3.5, moved_points: -1,
    state: 'value', note: 'StatEdge still has 1.3 points on BUF.',
  },
  reasons: [
    { label: 'BUF rated 3rd of 32', detail: '+6.1 points per game against an average team over 5 games (nflverse-epa)', impact_points: null, source: 'ratings' },
    { label: '22 mph wind', detail: 'Total shaded down', impact_points: -1.9, source: 'weather' },
  ],
  basis: 'Every line here is an input the model read.',
  ...over,
})

describe('Why StatEdge has this number', () => {
  it('lists the inputs with the points they moved', () => {
    render(<WhyThisEdge why={why()} />)
    expect(screen.getByText('BUF rated 3rd of 32')).toBeInTheDocument()
    expect(screen.getByText(/nflverse-epa/)).toBeInTheDocument()
    expect(screen.getByText('-1.9 pts')).toBeInTheDocument()
  })

  it('shows the opening line, the current line and ours', () => {
    render(<WhyThisEdge why={why()} />)
    expect(screen.getByText(/Opened -2\.5/)).toBeInTheDocument()
    expect(screen.getByText(/now -3\.5/)).toBeInTheDocument()
    expect(screen.getByText(/StatEdge BUF -4\.8/)).toBeInTheDocument()
  })

  it('labels a surviving edge and a vanished one differently', () => {
    const { unmount } = render(<WhyThisEdge why={why()} />)
    expect(screen.getByText(/still value/i)).toBeInTheDocument()
    unmount()

    render(<WhyThisEdge why={why({
      line: { opening: -2.5, current: -4.6, moved_points: -2.1, state: 'gone', note: 'The market has caught up.' },
    })} />)
    expect(screen.getByText(/edge gone/i)).toBeInTheDocument()
  })

  it('shows a missing input as missing rather than omitting it', () => {
    // A short honest list beats a plausible fabrication; dropping the row
    // would let a reader assume ratings were considered.
    render(<WhyThisEdge why={why({
      reasons: [{
        label: 'No play-by-play ratings for either team',
        detail: 'College priors need CFBD_API_KEY, which is not set.',
        impact_points: null, source: 'missing',
      }],
    })} />)
    expect(screen.getByText(/missing input/i)).toBeInTheDocument()
    expect(screen.getByText(/CFBD_API_KEY/)).toBeInTheDocument()
  })

  it('renders nothing rather than an empty panel when there are no reasons', () => {
    const { container } = render(<WhyThisEdge why={why({ reasons: [] })} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('says what the list is, so it is not read as a story about the game', () => {
    render(<WhyThisEdge why={why()} />)
    expect(screen.getByText(/an input the model read/i)).toBeInTheDocument()
  })
})
