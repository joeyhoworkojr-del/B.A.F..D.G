export type GameTabKey = 'scorecast' | 'markets' | 'plays' | 'chat'

export interface GameTab {
  key: GameTabKey
  label: string
  /** Shown as a small count or dot beside the label. */
  badge?: string
}

/**
 * The game's sections, as a tab bar.
 *
 * A football game page has a lot on it — projection, market comparison, drives,
 * picks, chat — and stacking all of it made a page you scrolled past rather
 * than read. Tabs put one thing in front of the reader at a time.
 *
 * Roving tabindex with arrow keys, which is what a tablist is expected to do:
 * one stop in the page's tab order, then left/right between the tabs.
 */
export function GameTabs({
  tabs, active, onChange, panelId,
}: {
  tabs: GameTab[]
  active: GameTabKey
  onChange: (key: GameTabKey) => void
  panelId: string
}) {
  const move = (delta: number) => {
    const i = tabs.findIndex(t => t.key === active)
    const next = tabs[(i + delta + tabs.length) % tabs.length]
    onChange(next.key)
    document.getElementById(`game-tab-${next.key}`)?.focus()
  }

  return (
    <div
      role="tablist"
      aria-label="Game sections"
      className="flex gap-1 overflow-x-auto border-b border-terminal-border no-scrollbar"
      onKeyDown={e => {
        if (e.key === 'ArrowRight') { e.preventDefault(); move(1) }
        if (e.key === 'ArrowLeft') { e.preventDefault(); move(-1) }
      }}
    >
      {tabs.map(tab => {
        const on = tab.key === active
        return (
          <button
            key={tab.key}
            id={`game-tab-${tab.key}`}
            role="tab"
            type="button"
            aria-selected={on}
            aria-controls={panelId}
            tabIndex={on ? 0 : -1}
            onClick={() => onChange(tab.key)}
            // Padding is tight on purpose: four sections have to fit a 390px
            // screen, and a tab that needs scrolling to reach is a tab most
            // people never find.
            className={`tap relative shrink-0 whitespace-nowrap px-2.5 pb-2.5 pt-1 text-sm font-bold uppercase tracking-wide transition sm:px-4 ${
              on ? 'text-brand' : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            {tab.label}
            {tab.badge && (
              <span className={`ml-1.5 font-mono text-xs ${on ? 'text-brand/70' : 'text-zinc-600'}`}>
                {tab.badge}
              </span>
            )}
            {/* The underline is the selected state, so it must not depend on
                colour alone to be readable. */}
            {on && <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-brand" />}
          </button>
        )
      })}
    </div>
  )
}
