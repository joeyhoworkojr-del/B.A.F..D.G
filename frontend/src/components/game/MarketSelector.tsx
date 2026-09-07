import { useRef } from 'react'
import type { MarketKey, MarketOut } from '../../types'

export interface MarketSelectorProps {
  markets: MarketOut[]
  active: MarketKey
  onChange: (key: MarketKey) => void
  /** id of the panel each tab controls, for aria-controls. */
  panelId: string
}

/**
 * Proper tablist for Moneyline / Spread / Total: roving tabindex, arrow-key and
 * Home/End navigation, and aria-selected — so the market can be changed without
 * a mouse.
 */
export function MarketSelector({ markets, active, onChange, panelId }: MarketSelectorProps) {
  const refs = useRef<(HTMLButtonElement | null)[]>([])

  const move = (from: number, delta: number) => {
    const next = (from + delta + markets.length) % markets.length
    onChange(markets[next].key)
    refs.current[next]?.focus()
  }

  const onKeyDown = (e: React.KeyboardEvent, i: number) => {
    switch (e.key) {
      case 'ArrowRight': e.preventDefault(); move(i, 1); break
      case 'ArrowLeft': e.preventDefault(); move(i, -1); break
      case 'Home': e.preventDefault(); onChange(markets[0].key); refs.current[0]?.focus(); break
      case 'End': {
        e.preventDefault()
        const last = markets.length - 1
        onChange(markets[last].key); refs.current[last]?.focus()
        break
      }
      default: break
    }
  }

  return (
    <div role="tablist" aria-label="Betting market" className="flex flex-wrap gap-2">
      {markets.map((m, i) => {
        const selected = m.key === active
        return (
          <button
            key={m.key}
            ref={el => { refs.current[i] = el }}
            role="tab"
            id={`market-tab-${m.key}`}
            aria-selected={selected}
            aria-controls={panelId}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(m.key)}
            onKeyDown={e => onKeyDown(e, i)}
            className={`rounded-full px-4 py-1.5 text-sm font-bold transition ${
              selected
                ? 'bg-zinc-100 text-terminal-bg'
                : 'bg-terminal-muted text-zinc-300 hover:text-zinc-100'
            }`}
          >
            {m.label}
          </button>
        )
      })}
    </div>
  )
}
