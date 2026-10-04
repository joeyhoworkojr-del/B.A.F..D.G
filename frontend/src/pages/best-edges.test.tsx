import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { BestBets } from './BestBets'
import { api } from '../api/client'
import type { EdgeRow, EdgesResponse } from '../types'

/**
 * The Best Edges terminal.
 *
 * The thing being protected is that the four numbers stay four numbers. The
 * temptation on a page like this is a single score out of a hundred, and that
 * is exactly what makes it untrustworthy: "82" invites "82% chance of
 * winning", which is not what any of win probability, break-even, EV or input
 * coverage actually says.
 */
const row = (over: Partial<EdgeRow> = {}): EdgeRow => ({
  league: 'nfl', event_id: '1', kickoff: '2026-10-05T17:00:00Z',
  home: 'Buffalo Bills', away: 'Miami Dolphins',
  home_abbr: 'BUF', away_abbr: 'MIA',
  market: 'spread', market_label: 'Spread', line: -3.5,
  selection: 'BUF -3.5', side: 'home',
  price_american: -110, assumed_price: true,
  model_prob: 0.585, break_even_prob: 0.524, ev_per_unit: 0.117,
  edge_pp: 8.5, grade: 'A',
  fair_label: 'BUF -4.8', market_label_spread: 'BUF -3.5', edge_points: 1.3,
  confidence: 'medium', source: 'ESPN BET',
  why: ['BUF rated 3rd of 32', 'Shrunk 50% toward the market price'],
  ...over,
})

const response = (edges: EdgeRow[], over: Partial<EdgesResponse> = {}): EdgesResponse => ({
  edges,
  total_matching: edges.length,
  scanned: 12,
  filters: { league: 'all', market: 'all', min_ev: 0, confidence: 'low', hours: 0, limit: 50 },
  leagues: ['nfl', 'ncaaf'],
  markets: ['moneyline', 'spread', 'total'],
  source_ok: true, market_source: 'ESPN BET',
  fetched_at: new Date().toISOString(),
  note: '', ranking: 'Ranked by expected value on a one-unit stake, not by how likely the pick is to win.',
  ...over,
})

beforeEach(() => {
  vi.spyOn(api, 'edges').mockResolvedValue(response([row()]) as never)
})
afterEach(() => vi.restoreAllMocks())

const show = () => render(<MemoryRouter><BestBets /></MemoryRouter>)

describe('Best edges', () => {
  it('shows win probability, break-even, EV and confidence as four things', async () => {
    show()
    expect(await screen.findByText('BUF -3.5')).toBeInTheDocument()
    // Exact labels: the footnote explaining each term mentions them too, so a
    // loose regex matches the caveat as well as the column it describes.
    expect(screen.getByText('Win prob')).toBeInTheDocument()
    expect(screen.getByText('58.5%')).toBeInTheDocument()
    expect(screen.getByText('Break-even')).toBeInTheDocument()
    expect(screen.getByText('52.4%')).toBeInTheDocument()
    expect(screen.getByText('Expected value')).toBeInTheDocument()
    expect(screen.getByText('Model confidence')).toBeInTheDocument()
    // ...and the four are never collapsed into one score out of a hundred.
    expect(screen.queryByText(/\b\d{1,3}\s*\/\s*100\b/)).not.toBeInTheDocument()
  })

  it('says it ranks by expected value, not by likelihood', async () => {
    show()
    await screen.findByText('BUF -3.5')
    expect(screen.getByText(/not by how likely a pick is to win/i)).toBeInTheDocument()
  })

  it('shows the fair line against the market line and the gap', async () => {
    show()
    await screen.findByText('BUF -3.5')
    expect(screen.getByText(/StatEdge BUF -4\.8/)).toBeInTheDocument()
    expect(screen.getByText(/1\.3 pts/)).toBeInTheDocument()
  })

  it('flags a price it had to assume rather than passing it off as quoted', async () => {
    show()
    await screen.findByText('BUF -3.5')
    expect(screen.getByText(/publishes spread and total lines without a price/i)).toBeInTheDocument()
  })

  it('does not print the assumed-price caveat when every price is quoted', async () => {
    vi.spyOn(api, 'edges').mockResolvedValue(
      response([row({ market: 'moneyline', selection: 'BUF ML', price_american: -175, assumed_price: false })]) as never,
    )
    show()
    await screen.findByText('BUF ML')
    expect(screen.queryByText(/without a price/i)).not.toBeInTheDocument()
  })

  it('asks the API again when a filter changes', async () => {
    const spy = vi.spyOn(api, 'edges')
    show()
    await screen.findByText('BUF -3.5')

    await userEvent.selectOptions(screen.getByLabelText(/league/i), 'nfl')
    await waitFor(() => expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ league: 'nfl' }),
    ))
  })

  it('passes a minimum EV through as a fraction, not a percentage', async () => {
    const spy = vi.spyOn(api, 'edges')
    show()
    await screen.findByText('BUF -3.5')

    await userEvent.selectOptions(screen.getByLabelText(/min ev/i), '0.05')
    await waitFor(() => expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ minEv: 0.05 }),
    ))
  })

  it('distinguishes "nothing clears the filters" from "nothing is on"', async () => {
    vi.spyOn(api, 'edges').mockResolvedValue(response([], {
      total_matching: 0, scanned: 40,
      note: 'No game on the board clears these filters right now.',
    }) as never)
    show()
    expect(await screen.findByText(/clears these filters/i)).toBeInTheDocument()
  })

  it('surfaces a failed scan instead of showing an empty list', async () => {
    vi.spyOn(api, 'edges').mockRejectedValue(new Error('feed unreachable'))
    show()
    expect(await screen.findByRole('alert')).toHaveTextContent(/feed unreachable/i)
  })

  it('shows the reasons, not just the number', async () => {
    show()
    await screen.findByText('BUF -3.5')
    expect(screen.getByText(/BUF rated 3rd of 32/)).toBeInTheDocument()
  })
})
