import { useEffect, useRef, useState } from 'react'
import type { FaqEntry } from '../../content/faq'

export interface FaqListProps {
  entries: FaqEntry[]
  /** Ids that should start open — used for a deep link like /faq#grades. */
  openIds?: string[]
  headingLevel?: 2 | 3
}

/**
 * Accessible disclosure list.
 *
 * Each question is a real <button> inside a heading, so screen readers announce
 * the structure and keyboard users get expand/collapse for free. Every answer
 * carries a stable id, which makes /faq#<id> a shareable link straight to it.
 */
export function FaqList({ entries, openIds = [], headingLevel = 3 }: FaqListProps) {
  const [open, setOpen] = useState<Set<string>>(() => new Set(openIds))
  const H = (headingLevel === 2 ? 'h2' : 'h3') as 'h2' | 'h3'
  const seen = useRef(openIds.join(','))

  useEffect(() => {
    const key = openIds.join(',')
    if (key === seen.current) return
    seen.current = key
    setOpen(prev => new Set([...prev, ...openIds]))
  }, [openIds])

  return (
    <ul className="divide-y divide-terminal-border rounded-card border border-terminal-border bg-terminal-surface">
      {entries.map(entry => {
        const isOpen = open.has(entry.id)
        return (
          <li key={entry.id} id={entry.id} className="scroll-mt-24">
            <H className="m-0">
              <button
                type="button"
                aria-expanded={isOpen}
                aria-controls={`faq-answer-${entry.id}`}
                onClick={() => setOpen(prev => {
                  const next = new Set(prev)
                  if (next.has(entry.id)) next.delete(entry.id)
                  else next.add(entry.id)
                  return next
                })}
                className="tap flex w-full items-center gap-3 px-4 py-3 text-left text-sm font-bold text-zinc-100 hover:bg-terminal-muted"
              >
                <span className="flex-1">{entry.q}</span>
                <svg
                  width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                  strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
                  className={`shrink-0 text-zinc-500 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                >
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </button>
            </H>
            <div id={`faq-answer-${entry.id}`} hidden={!isOpen} className="px-4 pb-4">
              {entry.a.map((p, i) => (
                <p key={i} className="mt-1 text-sm leading-relaxed text-zinc-400">{p}</p>
              ))}
              <a
                href={`#${entry.id}`}
                className="mt-2 inline-block text-xs font-semibold text-brand hover:underline"
              >
                Link to this answer
              </a>
            </div>
          </li>
        )
      })}
    </ul>
  )
}
