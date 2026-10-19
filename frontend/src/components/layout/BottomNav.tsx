import { NavLink } from 'react-router-dom'
import { useSession } from '../../session/SessionProvider'
import { Bars, Football, Person, Spark, Ticked } from './icons'

const baseItems = [
  { to: '/', label: 'Games', Icon: Football, end: true },
  // Live games are on the Games board now, at the top of it, so a Live tab
  // only ever led to a page that was empty most of the week. The slot goes to
  // the record instead — the thing that makes a projection worth reading.
  { to: '/results', label: 'Results', Icon: Ticked, end: false },
  // Ask Edge takes the middle slot: it is the feature people reach for
  // repeatedly, and one-handed reach matters most in the centre.
  { to: '/ask', label: 'Ask Edge', Icon: Spark, end: false },
  { to: '/best-bets', label: 'Edges', Icon: Bars, end: false },
]

/**
 * Primary navigation below `lg`. The full header nav needs more room than a
 * 768px tablet has — squeezing it in there pushed the page 8px wide — so the
 * bottom bar covers everything up to that width and the top bar takes over
 * above it. The page reserves matching bottom padding so it never covers
 * content. News, Leaderboard, Parlay and FAQ sit in the row under the header.
 */
export function BottomNav() {
  const { user } = useSession()
  // The fifth slot is the user's own record once they have one, and the way in
  // before that — the most useful destination in both states.
  const items = [
    ...baseItems,
    user
      ? { to: '/my-edge', label: 'My Edge', Icon: Person, end: false }
      : { to: '/register', label: 'Join', Icon: Person, end: false },
  ]

  return (
    <nav
      aria-label="Primary"
      data-nav="bottom"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-terminal-border bg-terminal-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden"
    >
      <ul className="mx-auto flex max-w-3xl items-end">
        {items.map(({ to, label, Icon, end }, i) => {
          // The middle slot is raised. One-handed reach is best in the centre
          // and Ask Edge is the thing people come back to, so it gets the
          // thumb position and the only filled treatment in the bar.
          const raised = i === Math.floor(items.length / 2)
          return (
            <li key={to} className="flex-1">
              <NavLink
                to={to}
                end={end}
                className={({ isActive }) =>
                  raised
                    ? 'tap flex flex-col items-center justify-end gap-1 pb-1.5'
                    : `tap flex flex-col items-center justify-center gap-0.5 py-2 text-[11px] font-semibold ${
                        isActive ? 'text-brand' : 'text-zinc-400'
                      }`
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      className={
                        raised
                          ? `-mt-6 grid h-14 w-14 place-items-center rounded-full text-white shadow-lift ring-4 ring-terminal-surface ${
                              isActive ? 'bg-brand-strong' : 'bg-brand'
                            }`
                          : ''
                      }
                    >
                      <Icon size={raised ? 24 : 22} />
                    </span>
                    <span
                      className={
                        raised
                          ? `text-[11px] font-bold ${isActive ? 'text-brand' : 'text-zinc-400'}`
                          : ''
                      }
                    >
                      {label}
                    </span>
                  </>
                )}
              </NavLink>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
