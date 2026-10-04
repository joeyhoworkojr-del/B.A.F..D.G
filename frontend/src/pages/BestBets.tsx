import { useState, useEffect, useCallback, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { DataFreshnessBadge } from '../components/game/DataFreshnessBadge'
import { oddsSourceSentence } from '../components/OddsSource'
import type { EdgeRow, EdgesResponse } from '../types'

const pct = (v?: number | null) => (v == null ? '—' : `${(v * 100).toFixed(1)}%`)
const signedPct = (v: number) => `${v >= 0 ? '+' : ''}${(v * 100).toFixed(1)}%`
const american = (v: number) => (v > 0 ? `+${Math.round(v)}` : `${Math.round(v)}`)

const MARKET_LABEL: Record<EdgeRow['market'], string> = {
  moneyline: 'Moneyline', spread: 'Spread', total: 'Total',
}

const CONFIDENCE_TONE: Record<EdgeRow['confidence'], string> = {
  high: 'text-brand', medium: 'text-zinc-300', low: 'text-zinc-500',
}

function kickoff(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  return d.toLocaleString(undefined, {
    weekday: 'short', hour: 'numeric', minute: '2-digit',
  })
}

/** A labelled select. Filters are the page, so they are not hidden in a drawer. */
function Filter<T extends string>({ label, value, onChange, options }: {
  label: string
  value: T
  onChange: (v: T) => void
  options: [T, string][]
}) {
  const id = `filter-${label.toLowerCase().replace(/\s+/g, '-')}`
  return (
    <label htmlFor={id} className="flex min-w-0 flex-col gap-1">
      <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <select
        id={id}
        value={value}
        onChange={e => onChange(e.target.value as T)}
        className="tap rounded-lg border border-terminal-border bg-terminal-surface px-2.5 py-2 text-sm font-semibold text-zinc-100"
      >
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </label>
  )
}

/**
 * One row of the terminal.
 *
 * Every number that decides whether a bet is worth taking is its own column.
 * The temptation is to collapse them into a single score out of a hundred, and
 * that is exactly what makes a page like this untrustworthy: "82%" invites the
 * reading "82% chance of winning", which is not what any of these numbers say.
 */
function EdgeRowItem({ row }: { row: EdgeRow }) {
  const beatsBreakEven =
    row.break_even_prob != null && row.model_prob > row.break_even_prob

  return (
    <li className="border-t border-terminal-border/70 px-3 py-3 first:border-t-0 sm:px-4">
      <div className="flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
        <span className="rounded border border-terminal-border px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-zinc-500">
          {row.league.toUpperCase()}
        </span>
        <Link
          to={`/game/${row.league}/${row.event_id}?market=${row.market}`}
          className="text-[15px] font-bold text-zinc-100 hover:underline"
        >
          {row.selection}
        </Link>
        <span className="font-mono text-xs tabular-nums text-zinc-400">
          {american(row.price_american)}
          {row.assumed_price && <span className="text-zinc-500" title="ESPN publishes no price for this market; priced at the standard -110">*</span>}
        </span>
        <span className="text-xs text-zinc-500">{MARKET_LABEL[row.market]}</span>
        <span className="ml-auto font-mono text-base font-black tabular-nums text-brand">
          {signedPct(row.ev_per_unit)}
        </span>
      </div>

      <div className="mt-1 text-xs text-zinc-500">
        {row.away} at {row.home} · {kickoff(row.kickoff)}
      </div>

      {/* The four numbers, never merged. */}
      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs sm:grid-cols-4">
        <div className="flex justify-between gap-2">
          <dt className="text-zinc-500">Win prob</dt>
          <dd className="font-mono tabular-nums text-zinc-200">{pct(row.model_prob)}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-zinc-500">Break-even</dt>
          <dd className={`font-mono tabular-nums ${beatsBreakEven ? 'text-zinc-200' : 'text-signal-red'}`}>
            {pct(row.break_even_prob)}
          </dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-zinc-500">Expected value</dt>
          <dd className="font-mono tabular-nums text-zinc-200">{signedPct(row.ev_per_unit)}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-zinc-500">Model confidence</dt>
          <dd className={`font-semibold capitalize ${CONFIDENCE_TONE[row.confidence]}`}>
            {row.confidence}
          </dd>
        </div>
      </dl>

      {(row.edge_points != null || row.fair_label) && (
        <p className="mt-2 font-mono text-xs tabular-nums text-zinc-400">
          {row.fair_label && <>StatEdge {row.fair_label}</>}
          {row.market_label_spread && <> · market {row.market_label_spread}</>}
          {row.edge_points != null && (
            <span className="text-brand"> · {row.edge_points.toFixed(1)} pts</span>
          )}
        </p>
      )}

      {row.why.length > 0 && (
        <p className="mt-1.5 text-xs leading-relaxed text-zinc-500">
          {row.why.join(' · ')}{' '}
          <Link
            to={`/game/${row.league}/${row.event_id}?market=${row.market}#why`}
            className="font-semibold text-brand hover:underline"
          >
            Why ›
          </Link>
        </p>
      )}
    </li>
  )
}

/**
 * Best Edges.
 *
 * Ranked by expected value, not by probability. A 90% favourite priced at 92%
 * is a worse bet than a 55% call at even money, and ranking by probability
 * puts the bad one on top — which is how a page like this ends up
 * recommending heavy favourites all season and calling it a hit rate.
 */
export function BestBets() {
  const [data, setData] = useState<EdgesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [league, setLeague] = useState('all')
  const [market, setMarket] = useState('all')
  const [minEv, setMinEv] = useState('0')
  const [confidence, setConfidence] = useState('low')
  const [hours, setHours] = useState('0')

  const load = useCallback(() => {
    setLoading(true)
    api.edges({
      league, market, minEv: Number(minEv),
      confidence, hours: Number(hours), limit: 50,
    })
      .then(d => { setData(d); setError('') })
      .catch(e => setError(e instanceof Error ? e.message : 'Scan failed'))
      .finally(() => setLoading(false))
  }, [league, market, minEv, confidence, hours])

  useEffect(() => { load() }, [load])

  const assumed = useMemo(
    () => (data?.edges ?? []).some(e => e.assumed_price),
    [data],
  )

  return (
    <div className="mx-auto max-w-3xl space-y-5 px-4 py-6">
      <header>
        <h1 className="font-display text-2xl font-bold text-zinc-100">Best edges</h1>
        <p className="mt-1 text-sm leading-relaxed text-zinc-400">
          Where StatEdge disagrees with the market, ranked by expected value on a
          one-unit stake — not by how likely a pick is to win.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        <Filter label="League" value={league} onChange={setLeague}
          options={[['all', 'NFL + college'], ['nfl', 'NFL'], ['ncaaf', 'College']]} />
        <Filter label="Market" value={market} onChange={setMarket}
          options={[['all', 'All markets'], ['spread', 'Spread'], ['moneyline', 'Moneyline'], ['total', 'Total']]} />
        <Filter label="Min EV" value={minEv} onChange={setMinEv}
          options={[['0', 'Any'], ['0.02', '+2%'], ['0.05', '+5%'], ['0.08', '+8%']]} />
        <Filter label="Confidence" value={confidence} onChange={setConfidence}
          options={[['low', 'Any'], ['medium', 'Medium+'], ['high', 'High only']]} />
        <Filter label="Kick-off" value={hours} onChange={setHours}
          options={[['0', 'Anytime'], ['6', 'Next 6h'], ['24', 'Next 24h'], ['72', 'Next 3 days']]} />
      </div>

      {loading && !data && (
        <p className="py-10 text-center text-sm text-zinc-500">Scanning the board…</p>
      )}

      {error && (
        <div role="alert" className="rounded-2xl border border-signal-red/40 bg-signal-red-dim p-4 text-sm text-signal-red">
          {error}
        </div>
      )}

      {data && (
        <>
          <p className="text-xs text-zinc-500">
            {data.total_matching === 0
              ? data.note
              : `${data.total_matching} of ${data.scanned} market sides clear these filters.`}
          </p>

          {data.edges.length > 0 && (
            <ol className="overflow-hidden rounded-2xl border border-terminal-border bg-terminal-surface">
              {data.edges.map(row => (
                <EdgeRowItem key={`${row.league}-${row.event_id}-${row.market}-${row.side}`} row={row} />
              ))}
            </ol>
          )}

          <div className="space-y-1.5 text-xs leading-relaxed text-zinc-500">
            {/* The EV on a spread or total is only as good as the price we had
                to assume, and that is said rather than buried. */}
            {assumed && (
              <p>
                * ESPN publishes spread and total lines without a price, so those
                rows are priced at the standard −110. Their expected value is
                only as good as that assumption.
              </p>
            )}
            <p>
              Win probability is the model's; break-even is what the price alone
              needs; model confidence is how much of the model's input this game
              had, not the chance a bet wins.
            </p>
            <p className="flex flex-wrap items-center gap-2">
              <span>{oddsSourceSentence(data.market_source)}</span>
              <span aria-hidden="true">•</span>
              <DataFreshnessBadge
                fetchedAt={data.fetched_at}
                ok={data.source_ok !== false && !error}
                staleAfterSeconds={120}
              />
            </p>
          </div>
        </>
      )}
    </div>
  )
}
