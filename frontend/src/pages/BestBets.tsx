import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { BestBetsResponse } from '../types'
import { RatingChip } from '../components/EdgesTable'

export function BestBets() {
  const [data, setData] = useState<BestBetsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setData(await api.bestBets())
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Scan failed')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-zinc-100">
            Best Bets — <span className="text-signal-amber">Live Scan</span>
          </h1>
          <p className="text-sm text-zinc-500 mt-1 font-body">
            Every upcoming fixture, re-priced with current weather and team news, ranked by
            disagreement with the reference market.
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="rounded-lg border border-terminal-border bg-terminal-surface px-3 py-1.5 text-xs font-display text-zinc-300 hover:border-signal-amber transition-colors disabled:opacity-40 whitespace-nowrap"
        >
          {loading ? 'Scanning…' : '🔄 Re-scan'}
        </button>
      </div>

      {loading && (
        <div className="rounded-xl border border-terminal-border bg-terminal-surface p-8 text-center">
          <p className="text-sm text-zinc-500 font-body animate-pulse">
            Scanning fixtures with live weather + lineups…
          </p>
        </div>
      )}

      {error && <p className="text-sm text-signal-red font-body">{error}</p>}

      {!loading && data && data.bets.length === 0 && (
        <div className="rounded-xl border border-terminal-border bg-terminal-surface p-8 text-center">
          <p className="text-sm text-zinc-400 font-body">
            No edges above threshold right now — the market and the model agree. Check back after
            team news drops.
          </p>
        </div>
      )}

      {!loading && data && data.bets.map((b, i) => (
        <div
          key={`${b.fixture_id}-${b.market}-${b.selection}-${i}`}
          className="rounded-xl border border-terminal-border bg-terminal-surface p-4 flex items-center gap-4"
        >
          <RatingChip rating={b.rating} />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-display font-semibold text-zinc-100">
              {b.selection} <span className="text-zinc-500 font-normal">· {b.market}</span>
            </p>
            <p className="text-xs text-zinc-500 font-body truncate">
              {b.home_flag} {b.home} vs {b.away_flag} {b.away} · {b.venue}
            </p>
            <p className="text-[10px] text-zinc-600 font-body mt-0.5">{b.note}</p>
          </div>
          <div className="text-right shrink-0">
            <p className="font-mono text-lg text-signal-amber">{Math.round(b.model_prob * 100)}%</p>
            {b.market_prob != null && b.edge_pp != null ? (
              <p className="font-mono text-[10px] text-zinc-500">
                mkt {Math.round(b.market_prob * 100)}% · <span className="text-signal-green">+{b.edge_pp.toFixed(1)}pp</span>
              </p>
            ) : (
              <p className="font-mono text-[10px] text-zinc-600">model conviction</p>
            )}
          </div>
        </div>
      ))}

      {!loading && data && (
        <p className="text-[10px] text-zinc-600 italic">
          {data.generated_with}. Probabilities, not promises — bet responsibly.
        </p>
      )}
    </div>
  )
}
