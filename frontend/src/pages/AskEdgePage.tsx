import { AskEdge } from '../components/ai/AskEdge'

/**
 * Edge AI on its own page — the destination the mobile bar points at.
 *
 * With no game context, so the assistant starts from the whole board rather
 * than one matchup. Opening it from a game carries that game's context
 * instead.
 */
export function AskEdgePage() {
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-6">
      <header>
        <h1 className="font-display text-2xl font-black text-zinc-100">Ask Edge</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Your sports intelligence assistant. It reads StatEdge's projections, live game
          state, published picks and leaderboard — and tells you when it doesn't have
          something rather than filling the gap.
        </p>
      </header>
      <div className="mt-5">
        <AskEdge />
      </div>
    </div>
  )
}
