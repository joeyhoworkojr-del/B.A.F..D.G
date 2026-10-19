/**
 * The filter chip, in one place.
 *
 * Four pages — props, news, the leaderboard and the FAQ — each carried a
 * byte-identical copy of this, and the board's day tabs a fifth inline. They
 * agreed by luck rather than by construction: change the brand's active state
 * and four of the five would have kept the old one.
 *
 * It returns a class string rather than a component because the element
 * differs every time it is used — a `button` with `aria-pressed`, a `NavLink`
 * with its own active state, an `a` in a tab list — and wrapping that in one
 * component would mean passing the semantics back in as props.
 */
export const chipCls = (active: boolean) =>
  `tap inline-flex items-center rounded-full px-4 text-sm font-bold transition ${
    active
      ? 'bg-brand text-white shadow-card'
      : 'bg-terminal-muted text-zinc-400 hover:text-zinc-100'
  }`
