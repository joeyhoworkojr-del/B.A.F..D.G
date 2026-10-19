import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PageHeader } from './PageHeader'
import { chipCls } from '../ui/chip'

describe('The page header', () => {
  it('gives the page exactly one h1, and it is the title', () => {
    render(<PageHeader eyebrow="Value" title="Best edges" blurb="Where the model disagrees." />)
    const headings = screen.getAllByRole('heading', { level: 1 })
    expect(headings).toHaveLength(1)
    expect(headings[0]).toHaveTextContent('Best edges')
  })

  it('does not make the eyebrow a heading', () => {
    // The eyebrow names the section, not the page. Marking it up as a heading
    // would put two headings above every page and read as the title to a
    // screen reader before the real one.
    render(<PageHeader eyebrow="Value" title="Best edges" />)
    expect(screen.queryByRole('heading', { name: /value/i })).not.toBeInTheDocument()
    expect(screen.getByText('Value')).toBeInTheDocument()
  })

  it('leaves out the blurb entirely rather than rendering an empty line', () => {
    const { container } = render(<PageHeader eyebrow="Help" title="FAQ" />)
    expect(container.querySelectorAll('p')).toHaveLength(1)
  })

  it('puts the aside beside the title', () => {
    render(
      <PageHeader eyebrow="Wire" title="News" aside={<span>Updated 2m ago</span>} />,
    )
    expect(screen.getByText('Updated 2m ago')).toBeInTheDocument()
  })
})

describe('The filter chip', () => {
  // What these pin is that there is one chip and that its two states differ.
  // Whether the active fill actually clears 4.5:1 under white text is not
  // something a class string can tell you — the end-to-end suite measures the
  // rendered colours for that, on every page at two widths.
  it('is one class string shared by every filter row', () => {
    expect(chipCls(true)).toBe(
      'tap inline-flex items-center rounded-full px-4 text-sm font-bold transition ' +
      'bg-brand text-white shadow-card',
    )
  })

  it('is visibly different when inactive', () => {
    expect(chipCls(false)).not.toContain('text-white')
    expect(chipCls(false)).toContain('bg-terminal-muted')
  })
})
