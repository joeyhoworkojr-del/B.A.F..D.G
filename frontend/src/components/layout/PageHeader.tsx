import type { ReactNode } from 'react'

/**
 * The top of every page that is not the board.
 *
 * The board gets the dark hero because it has three measured figures to put in
 * it. Everywhere else the same job is done in type: a brand eyebrow naming the
 * part of the product, the title, and one line on what the page is for.
 *
 * It exists because five pages had five different `h1`s — `text-2xl font-bold`,
 * `text-3xl font-bold`, `text-2xl font-black` — written at five different
 * times. Nobody chose that; it is just what happens without a component, and
 * it reads as carelessness rather than as a design.
 *
 * `aside` is for something that belongs beside the title rather than under it:
 * a freshness badge, a count, a link out. Filters are not that — they are the
 * page, and they stay in the body where they can be full width.
 */
export function PageHeader({ eyebrow, title, blurb, aside }: {
  eyebrow: string
  title: ReactNode
  blurb?: ReactNode
  aside?: ReactNode
}) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
      <div className="min-w-0">
        <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-brand">
          {eyebrow}
        </p>
        <h1 className="mt-1 font-display text-[28px] font-black leading-[1.1] tracking-tight text-zinc-100 sm:text-[32px]">
          {title}
        </h1>
        {blurb && (
          <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-zinc-400">
            {blurb}
          </p>
        )}
      </div>
      {aside && <div className="shrink-0">{aside}</div>}
    </header>
  )
}
