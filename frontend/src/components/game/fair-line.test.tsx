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
  validation: {
    measured: true, games: 750, beats_market: false,
    note: 'Backtested over 750 NFL games: the model alone is less accurate than the closing line.',
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
    // Matched on the total row itself: the validation note below also
    // contains the word "over", in "over 750 NFL games".
    expect(screen.getByText(/StatEdge 48\.3/)).toBeInTheDocument()
    expect(screen.getByText(/\+1\.8 over/)).toBeInTheDocument()
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


describe('What the page says about its own accuracy', () => {
  it('says plainly that the league has no demonstrated edge', () => {
    // The backtest found the model alone is worse than the closing line.
    // Showing an "edge" while hiding that would be the dishonest version.
    render(<FairLine value={value()} />)
    expect(screen.getByText(/no demonstrated edge/i)).toBeInTheDocument()
    expect(screen.getByText(/less accurate than the closing line/i)).toBeInTheDocument()
  })

  it('shows the raw model number and how much of it is published', () => {
    render(<FairLine value={value({
      spread: {
        fair: -3.6, fair_label: 'BUF -3.6', market: -3.5, market_label: 'BUF -3.5',
        edge_points: 0.1, side: 'home', side_abbr: 'BUF', points: 0.1,
        model_line: -4.8, model_weight: 0.1,
      },
    })} />)
    expect(screen.getByText(/Model alone -4\.8, weighted 10%/)).toBeInTheDocument()
  })

  it('marks a league that was never measured as unvalidated', () => {
    render(<FairLine value={value({
      validation: {
        measured: false, games: 0, beats_market: null,
        note: 'Not backtested. Accuracy against the market is unknown rather than good or bad.',
      },
    })} />)
    expect(screen.getByText(/unvalidated league/i)).toBeInTheDocument()
    expect(screen.queryByText(/no demonstrated edge/i)).not.toBeInTheDocument()
  })

  it('stays quiet when the payload carries no verdict at all', () => {
    render(<FairLine value={value({ validation: undefined })} />)
    expect(screen.queryByText(/no demonstrated edge/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/unvalidated/i)).not.toBeInTheDocument()
  })
})
