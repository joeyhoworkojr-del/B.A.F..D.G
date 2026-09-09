import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { UpsetWatch, upsetPicks } from './UpsetWatch'
import { boardEntry } from '../../test/fixtures'
import type { BoardEntry, UpsetOut } from '../../types'

function withUpset(id: string, upset: Partial<UpsetOut> | null): BoardEntry {
  const base = boardEntry('nfl', { event_id: id })
  return {
    ...base,
    model: {
      ...base.model!,
      upset: upset && {
        side: 'away', team: 'BAL', model_prob: 0.62, market_prob: 0.35,
        rule_hit_rate: 0.47, rule_base_rate: 0.318, ...upset,
      },
    },
  }
}

describe('Upset watch', () => {
  it('renders nothing at all when the model agrees with the market', () => {
    const { container } = render(
      <MemoryRouter><UpsetWatch entries={[withUpset('1', null)]} /></MemoryRouter>,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('names the underdog the model takes, and who it takes them over', async () => {
    render(<MemoryRouter><UpsetWatch entries={[withUpset('1', {})]} /></MemoryRouter>)
    expect(screen.getByText('BAL')).toBeInTheDocument()
    expect(screen.getByText(/over FSU/)).toBeInTheDocument()
  })

  it('keeps this game’s probability and the rule’s record clearly apart', () => {
    render(<MemoryRouter><UpsetWatch entries={[withUpset('1', {})]} /></MemoryRouter>)
    // The model's read on this game...
    expect(screen.getByText('62%')).toBeInTheDocument()
    // ...and, said as a record over many games rather than a forecast.
    expect(screen.getByText(/won 47% of the time/)).toBeInTheDocument()
    expect(screen.getByText(/not the chance of any one of these/i)).toBeInTheDocument()
  })

  it('shows the market’s number beside the model’s, so the gap is visible', () => {
    render(<MemoryRouter><UpsetWatch entries={[withUpset('1', {})]} /></MemoryRouter>)
    expect(screen.getByText('35%')).toBeInTheDocument()
  })

  it('stays short — a board that cries upset constantly is worth nothing', () => {
    const many = ['1', '2', '3', '4', '5'].map(id => withUpset(id, {}))
    render(<MemoryRouter><UpsetWatch entries={many} /></MemoryRouter>)
    expect(screen.getAllByRole('listitem')).toHaveLength(3)
  })

  it('leads with the biggest disagreement', () => {
    const entries = [
      withUpset('small', { model_prob: 0.59, market_prob: 0.45, team: 'SMALL' }),
      withUpset('big', { model_prob: 0.70, market_prob: 0.30, team: 'BIG' }),
    ]
    expect(upsetPicks(entries)[0].model!.upset!.team).toBe('BIG')
  })

  it('never calls an upset on a game already under way', () => {
    const live = { ...withUpset('1', {}) }
    live.game = { ...live.game, state: 'in' }
    expect(upsetPicks([live])).toHaveLength(0)
  })
})
