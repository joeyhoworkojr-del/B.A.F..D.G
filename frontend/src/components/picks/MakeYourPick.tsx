import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import { useSession } from '../../session/SessionProvider'
import type { LiveGameOut, PickMarket, PickOut, PickSide } from '../../types'

const MARKETS: { key: PickMarket; label: string; question: string }[] = [
  { key: 'moneyline', label: 'Winner', question: 'Who wins the game outright?' },
  { key: 'spread', label: 'Spread', question: 'Who covers the point spread?' },
  { key: 'total', label: 'Total', question: 'Over or under the combined score?' },
]

const fmt = (n: number) => (n > 0 ? `+${n}` : `${n}`)

/**
 * Publish a prediction on a game.
 *
 * The line shown here is the one submitted and stored: a pick is graded
 * against the number the analyst actually saw, not one that moved later. The
 * server refuses anything sent after kickoff regardless of what this form
 * allows, so the lock is real rather than a disabled button.
 */
export function MakeYourPick({
  league, game, existing, onSubmitted,
}: {
  league: string
  game: LiveGameOut
  existing?: PickOut[]
  onSubmitted?: (pick: PickOut) => void
}) {
  const { user, entitlements } = useSession()
  const [market, setMarket] = useState<PickMarket>('spread')
  const [side, setSide] = useState<PickSide | null>(null)
  const [confidence, setConfidence] = useState(65)
  const [reasoning, setReasoning] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState<PickOut | null>(null)

  const started = game.state !== 'pre'
  const alreadyPicked = useMemo(
    () => (existing ?? []).find(p => p.market === market),
    [existing, market],
  )

  const spread = game.market_spread ?? null
  const total = game.market_over_under ?? null

  const options: { side: PickSide; label: string; line: number | null; price: number | null }[] =
    market === 'moneyline'
      ? [
          { side: 'away', label: game.away, line: null, price: game.market_away_ml ?? null },
          { side: 'home', label: game.home, line: null, price: game.market_home_ml ?? null },
        ]
      : market === 'spread'
        ? [
            { side: 'away', label: `${game.away} ${spread == null ? '' : fmt(-spread)}`.trim(), line: spread == null ? null : -spread, price: -110 },
            { side: 'home', label: `${game.home} ${spread == null ? '' : fmt(spread)}`.trim(), line: spread, price: -110 },
          ]
        : [
            { side: 'over', label: total == null ? 'Over' : `Over ${total}`, line: total, price: -110 },
            { side: 'under', label: total == null ? 'Under' : `Under ${total}`, line: total, price: -110 },
          ]

  const chosen = options.find(o => o.side === side)
  const lineMissing = market !== 'moneyline' && chosen?.line == null

  async function submit() {
    if (!chosen) return
    setBusy(true)
    setError('')
    try {
      const pick = await api.submitPick({
        league, event_id: game.event_id, home: game.home, away: game.away,
        kickoff: game.kickoff, market, side: chosen.side,
        selection: chosen.label, line: chosen.line,
        price_american: chosen.price, odds_source: game.market_provider || '',
        confidence, reasoning: reasoning.trim(),
      })
      setDone(pick)
      onSubmitted?.(pick)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  // ── States that aren't the form ──────────────────────────────────────────
  if (!user) {
    return (
      <Panel>
        <p className="text-sm leading-relaxed text-zinc-400">
          Create a free account to publish a prediction on this game. Every pick locks at
          kickoff and grades itself, so your record is verifiable.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Link to="/register" className="tap inline-flex items-center rounded-lg bg-brand px-4 text-sm font-semibold text-white hover:bg-brand-strong">
            Create free account
          </Link>
          <Link to="/login" className="tap inline-flex items-center rounded-lg border border-terminal-border px-4 text-sm font-semibold text-zinc-300 hover:bg-terminal-muted">
            Sign in
          </Link>
        </div>
      </Panel>
    )
  }

  if (!entitlements.features.make_pick) {
    return <Panel><p className="text-sm text-zinc-400">Publishing picks isn’t part of your plan.</p></Panel>
  }

  if (started) {
    return (
      <Panel>
        <p className="text-sm text-zinc-400">
          This game has started, so picks are locked. That’s what makes the record worth
          publishing — nothing can be added or changed once the ball is in play.
        </p>
      </Panel>
    )
  }

  if (done) {
    return (
      <Panel>
        <p className="text-sm font-bold text-zinc-100">Pick published — {done.selection}</p>
        <p className="mt-1 text-sm leading-relaxed text-zinc-400">
          {done.confidence}% confidence. It locks at kickoff and grades automatically when
          the game goes final.
        </p>
        <Link to="/my-edge" className="mt-3 inline-block text-sm font-semibold text-brand hover:underline">
          See it in My Edge ›
        </Link>
      </Panel>
    )
  }

  return (
    <section aria-labelledby="make-pick" className="rounded-card border border-terminal-border bg-terminal-surface">
      <header className="border-b border-terminal-border px-4 py-3">
        <h2 id="make-pick" className="text-sm font-bold text-zinc-100">Make your pick</h2>
        <p className="mt-0.5 text-xs text-zinc-500">
          Locks at kickoff. Graded automatically. Permanent either way.
        </p>
      </header>

      <div className="space-y-4 p-4">
        <div role="tablist" aria-label="Market" className="flex flex-wrap gap-2">
          {MARKETS.map(m => (
            <button
              key={m.key} role="tab" aria-selected={market === m.key} type="button"
              onClick={() => { setMarket(m.key); setSide(null) }}
              className={`tap rounded-full px-4 text-sm font-bold transition ${
                market === m.key ? 'bg-brand text-white shadow-card'
                  : 'bg-terminal-muted text-zinc-400 hover:text-zinc-100'
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
        <p className="text-xs text-zinc-500">{MARKETS.find(m => m.key === market)?.question}</p>

        {alreadyPicked ? (
          <p className="rounded-lg border border-terminal-border bg-terminal-muted px-3 py-2 text-sm text-zinc-400">
            You’ve already published a {market} pick on this game:{' '}
            <span className="font-semibold text-zinc-100">{alreadyPicked.selection}</span>.
            One pick per market keeps a record honest.
          </p>
        ) : (
          <>
            <div className="grid gap-2 sm:grid-cols-2">
              {options.map(o => (
                <button
                  key={o.side} type="button" onClick={() => setSide(o.side)}
                  aria-pressed={side === o.side}
                  className={`tap flex items-center justify-between rounded-lg border px-4 text-left transition ${
                    side === o.side
                      ? 'border-brand bg-brand-soft text-zinc-100'
                      : 'border-terminal-border bg-terminal-surface text-zinc-300 hover:bg-terminal-muted'
                  }`}
                >
                  <span className="text-sm font-bold">{o.label}</span>
                  {o.price != null && (
                    <span className="font-mono text-sm tabular-nums text-zinc-500">{fmt(o.price)}</span>
                  )}
                </button>
              ))}
            </div>

            {lineMissing && (
              <p className="text-xs text-signal-amber">
                No {market} line is published for this game yet, so this pick couldn’t be
                graded. Choose the winner instead, or come back once a line is posted.
              </p>
            )}

            <div>
              <label htmlFor="confidence" className="flex items-center justify-between text-xs font-bold uppercase tracking-wide text-zinc-500">
                Confidence
                <span className="font-mono text-sm text-zinc-100 tabular-nums">{confidence}%</span>
              </label>
              <input
                id="confidence" type="range" min={50} max={99} value={confidence}
                onChange={e => setConfidence(Number(e.target.value))}
                className="mt-2 w-full accent-brand"
              />
              <p className="mt-1 text-xs text-zinc-500">
                How likely you think this is — not how much you like it.
              </p>
            </div>

            <div>
              <label htmlFor="reasoning" className="block text-xs font-bold uppercase tracking-wide text-zinc-500">
                Explain your edge <span className="font-normal normal-case text-zinc-500">(optional)</span>
              </label>
              <textarea
                id="reasoning" value={reasoning} onChange={e => setReasoning(e.target.value)}
                rows={3} maxLength={2000}
                placeholder="Why do you think this outcome is being mispriced?"
                className="mt-1 w-full rounded-lg border border-terminal-border bg-terminal-muted p-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-brand focus:bg-terminal-surface"
              />
              <p className="mt-1 text-xs text-zinc-500">
                Published with your pick once the game starts. {2000 - reasoning.length} characters left.
              </p>
            </div>

            {error && <p role="alert" className="text-sm text-signal-red">{error}</p>}

            <button
              type="button" onClick={() => void submit()}
              disabled={!side || busy || lineMissing}
              className="tap w-full rounded-lg bg-brand px-4 font-semibold text-white transition hover:bg-brand-strong disabled:cursor-not-allowed disabled:opacity-40"
            >
              {busy ? 'Publishing…' : side ? `Publish — ${chosen?.label}` : 'Choose a side'}
            </button>
          </>
        )}
      </div>
    </section>
  )
}

function Panel({ children }: { children: React.ReactNode }) {
  return (
    <section className="rounded-card border border-terminal-border bg-terminal-surface p-4">
      <h2 className="text-sm font-bold text-zinc-100">Make your pick</h2>
      <div className="mt-2">{children}</div>
    </section>
  )
}
