import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { BestParlayResponse, ParlayLeg } from '../types'

const LEAGUE_LABEL: Record<string, string> = { nfl: 'NFL', ncaaf: 'NCAAF' }
const fmtAm = (a: number) => (a > 0 ? `+${a}` : `${a}`)
const pct = (v: number) => `${Math.round(v * 100)}%`

function LegRow({ leg, i }: { leg: ParlayLeg; i: number }) {
  return (
    <div className="flex items-start gap-3 border-b border-terminal-border/60 py-3 last:border-0">
      <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-terminal-muted text-[11px] font-bold text-signal-green">{i + 1}</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-bold text-zinc-100">{leg.selection}</p>
        <p className="text-[11px] text-zinc-500">
          {LEAGUE_LABEL[leg.league] ?? leg.league} · {leg.away} @ {leg.home}
        </p>
      </div>
      <div className="shrink-0 text-right">
        <p className="font-mono text-sm font-bold text-signal-amber tabular-nums">{fmtAm(americanFromDecimal(leg.decimal_odds))}</p>
        <p className="text-[10px] text-zinc-500">model {pct(leg.model_prob)} · <span className="text-signal-green">+{leg.edge_pp.toFixed(1)}pp</span></p>
      </div>
    </div>
  )
}

function americanFromDecimal(dec: number): number {
  return dec >= 2 ? Math.round((dec - 1) * 100) : Math.round(-100 / (dec - 1))
}

export function Parlay() {
  const [maxLegs, setMaxLegs] = useState(3)
  const [data, setData] = useState<BestParlayResponse | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback((n: number) => {
    setLoading(true)
    api.bestParlay(n)
      .then(d => { setData(d); setError('') })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load(maxLegs) }, [maxLegs, load])

  const hasParlay = data && data.leg_count >= 2
  const payoutOn10 = data ? (10 * data.decimal_odds).toFixed(2) : '0'

  return (
    <div className="mx-auto max-w-xl px-3 py-4 sm:px-4">
      <div className="mb-4">
        <h1 className="font-display text-2xl font-black text-zinc-100">Best parlay</h1>
        <p className="mt-1 text-sm text-zinc-400">
          The model’s strongest-value ticket from today’s NFL + NCAA board — legs it both
          favours to win and prices as value, combined honestly.
        </p>
      </div>

      {/* Leg count selector */}
      <div className="mb-4 flex items-center gap-2">
        <span className="text-xs font-semibold text-zinc-500">Legs</span>
        {[2, 3, 4].map(n => (
          <button
            key={n}
            onClick={() => setMaxLegs(n)}
            className={`h-8 w-9 rounded-lg text-sm font-bold ${
              maxLegs === n ? 'bg-zinc-100 text-terminal-bg' : 'bg-terminal-surface text-zinc-400'
            }`}
          >
            {n}
          </button>
        ))}
      </div>

      {error && <div className="rounded-xl border border-signal-red/40 bg-terminal-surface p-4 text-sm text-signal-red">{error}</div>}
      {loading && !data && <div className="skeleton h-72 rounded-2xl" />}

      {data && !hasParlay && !loading && (
        <div className="rounded-2xl border border-dashed border-terminal-border bg-terminal-surface p-8 text-center">
          <p className="font-display text-lg font-bold text-zinc-100">No parlay on the board</p>
          <p className="mx-auto mt-1 max-w-sm text-sm text-zinc-500">
            The model only builds a parlay from plays it both favours to win and prices as value.
            There aren’t enough of those on today’s slate — check back on game day.
          </p>
        </div>
      )}

      {data && hasParlay && (
        <div className="overflow-hidden rounded-2xl border border-terminal-border bg-terminal-surface">
          {/* Betslip header */}
          <div className="border-b border-terminal-border bg-terminal-muted/40 px-4 py-3">
            <div className="flex items-end justify-between">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">{data.leg_count}-leg parlay</p>
                <p className="mt-0.5 font-mono text-3xl font-black text-signal-amber tabular-nums">{fmtAm(data.american_odds)}</p>
              </div>
              <div className="text-right">
                <p className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">$10 pays</p>
                <p className="mt-0.5 font-mono text-xl font-bold text-zinc-100 tabular-nums">${payoutOn10}</p>
              </div>
            </div>
          </div>

          {/* Legs */}
          <div className="px-4">
            {data.legs.map((leg, i) => <LegRow key={leg.fixture_id} leg={leg} i={i} />)}
          </div>

          {/* Model read-out */}
          <div className="grid grid-cols-3 gap-px bg-terminal-border">
            {[
              ['Model win %', pct(data.model_prob), 'text-zinc-100'],
              ['Break-even', pct(data.implied_prob), 'text-zinc-400'],
              ['Edge', `+${data.edge_pp.toFixed(1)}pp`, data.edge_pp >= 0 ? 'text-signal-green' : 'text-signal-red'],
            ].map(([l, v, c]) => (
              <div key={l} className="bg-terminal-surface px-3 py-3 text-center">
                <p className="text-[9px] font-bold uppercase tracking-wider text-zinc-500">{l}</p>
                <p className={`mt-1 font-mono text-sm font-bold tabular-nums ${c}`}>{v}</p>
              </div>
            ))}
          </div>

          {/* EV banner */}
          <div className={`px-4 py-3 text-center text-xs font-semibold ${
            data.ev_per_unit >= 0 ? 'bg-signal-green/10 text-signal-green' : 'bg-terminal-muted text-zinc-400'
          }`}>
            {data.ev_per_unit >= 0
              ? `Model sees positive value here: +${(data.ev_per_unit * 100).toFixed(0)}% expected return per unit staked.`
              : `Model sees this as ${(data.ev_per_unit * 100).toFixed(0)}% expected value — longshot, size it small.`}
          </div>
        </div>
      )}

      {/* Alternative legs pool */}
      {data && data.pool.length > (data.legs.length) && (
        <div className="mt-5">
          <p className="mb-2 text-[11px] font-bold uppercase tracking-widest text-zinc-500">Build your own — other value legs</p>
          <div className="rounded-xl border border-terminal-border bg-terminal-surface px-4">
            {data.pool.slice(data.legs.length).map((leg, i) => <LegRow key={leg.fixture_id} leg={leg} i={i} />)}
          </div>
        </div>
      )}

      <p className="mt-4 text-center text-[10px] text-zinc-600">
        Combined odds multiply each leg’s price; model win % multiplies each leg’s probability (assumes independence).
        Parlays are high-variance — the single legs on Best Bets are steadier. Bet responsibly.
      </p>
    </div>
  )
}
