import type { ReactNode } from 'react'
import { DataFreshnessBadge } from './DataFreshnessBadge'

export type PanelState = 'ready' | 'loading' | 'error' | 'empty'

export interface PanelProps {
  title: string
  /** Short plain-language explanation of what this panel shows. */
  subtitle?: string
  state?: PanelState
  /** Message for the error state — shown verbatim, never swallowed. */
  errorMessage?: string
  /** Message for the empty state — say why it's empty, not just "no data". */
  emptyMessage?: string
  /** When true we're refreshing but still showing the last good data. */
  refreshing?: boolean
  fetchedAt?: string | null
  source?: string | null
  sourceOk?: boolean
  staleAfterSeconds?: number
  actions?: ReactNode
  children?: ReactNode
  id?: string
}

/**
 * Every data-driven panel on the game page goes through here, so each one gets
 * the same loading / error / empty / last-good-data treatment plus a visible
 * source and timestamp. Panels keep rendering their last good content while a
 * refresh is in flight — no flash back to a skeleton.
 */
export function Panel({
  title, subtitle, state = 'ready', errorMessage, emptyMessage,
  refreshing = false, fetchedAt, source, sourceOk = true,
  staleAfterSeconds, actions, children, id,
}: PanelProps) {
  return (
    <section
      id={id}
      aria-busy={state === 'loading' || refreshing || undefined}
      className="min-w-0 rounded-xl border border-terminal-border bg-terminal-surface"
    >
      <header className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2 border-b border-terminal-border/70 px-4 py-3">
        <div className="min-w-0">
          <h2 className="text-sm font-bold text-zinc-100">{title}</h2>
          {subtitle && <p className="mt-0.5 text-xs text-zinc-400">{subtitle}</p>}
        </div>
        <div className="flex items-center gap-3">
          {actions}
          {(fetchedAt || source) && (
            <DataFreshnessBadge
              fetchedAt={fetchedAt}
              source={source}
              ok={sourceOk}
              staleAfterSeconds={staleAfterSeconds}
            />
          )}
        </div>
      </header>

      <div className="min-w-0 p-4">
        {state === 'loading' && (
          <div className="space-y-2" data-testid="panel-loading">
            <div className="skeleton h-4 w-2/3 rounded" />
            <div className="skeleton h-4 w-1/2 rounded" />
            <div className="skeleton h-16 w-full rounded" />
            <span className="sr-only">Loading {title}</span>
          </div>
        )}

        {state === 'error' && (
          <p role="alert" className="text-sm text-signal-red">
            {errorMessage || `Couldn’t load ${title.toLowerCase()}.`}
          </p>
        )}

        {state === 'empty' && (
          <p className="text-sm text-zinc-400">
            {emptyMessage || `No ${title.toLowerCase()} available yet.`}
          </p>
        )}

        {state === 'ready' && children}
      </div>
    </section>
  )
}
