import type { TotalsOut } from '../types'

interface Props {
  totals: TotalsOut
  homeLabel: string
  awayLabel: string
}

function Row({ label, prob, best }: { label: string; prob: number; best?: boolean }) {
  const pct = Math.round(prob * 100)
  const color = pct >= 65 ? 'text-signal-green' : pct <= 35 ? 'text-signal-red' : 'text-signal-amber'
  return (
    <div className={`flex justify-between items-center py-1 border-b border-terminal-muted/40 ${best ? 'bg-terminal-muted/30 -mx-2 px-2 rounded' : ''}`}>
      <span className="text-xs font-body text-zinc-400">{label}</span>
      <div className="flex items-center gap-3">
        <div className="w-24 h-1.5 rounded-full bg-terminal-muted overflow-hidden">
          <div className="h-full rounded-full bg-signal-amber" style={{ width: `${pct}%` }} />
        </div>
        <span className={`font-mono text-sm w-10 text-right ${color}`}>{pct}%</span>
      </div>
    </div>
  )
}

export function TotalsCard({ totals, homeLabel, awayLabel }: Props) {
  const [hs, as] = totals.expected_scoreline
  const sharpLine = totals.over_2_5 >= 0.55 ? 'Over 2.5' : totals.under_2_5 >= 0.60 ? 'Under 2.5' : null

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between pb-2">
        <p className="text-xs font-display uppercase tracking-widest text-zinc-500">
          Totals & Over/Under
        </p>
        <span className="font-mono text-sm text-zinc-300">
          {homeLabel} {hs}–{as} {awayLabel} <span className="text-zinc-600">(expected)</span>
        </span>
      </div>

      {sharpLine && (
        <div className="mb-3 px-3 py-2 rounded-lg border border-signal-amber/30 bg-signal-amber-dim/20">
          <p className="text-xs font-display text-signal-amber">
            Sharp edge: <strong>{sharpLine}</strong> —{' '}
            {sharpLine === 'Over 2.5'
              ? `${Math.round(totals.over_2_5 * 100)}% probability`
              : `${Math.round(totals.under_2_5 * 100)}% probability`}
          </p>
        </div>
      )}

      <Row label="Over 1.5 goals" prob={totals.over_1_5} />
      <Row label="Under 1.5 goals" prob={totals.under_1_5} />
      <Row label="Over 2.5 goals" prob={totals.over_2_5} best={totals.over_2_5 > 0.55} />
      <Row label="Under 2.5 goals" prob={totals.under_2_5} best={totals.under_2_5 > 0.6} />
      <Row label="Over 3.5 goals" prob={totals.over_3_5} />
      <Row label="Under 3.5 goals" prob={totals.under_3_5} />
      <Row label="Both Teams To Score" prob={totals.btts} />
      <Row label="BTTS — No" prob={totals.btts_no} />

      <div className="mt-3 grid grid-cols-2 gap-4 pt-2 border-t border-terminal-border">
        <div>
          <p className="text-[10px] font-display uppercase tracking-widest text-zinc-600 mb-1">{homeLabel} goals</p>
          <Row label="Over 0.5" prob={totals.home_over_0_5} />
          <Row label="Over 1.5" prob={totals.home_over_1_5} />
          <Row label="Over 2.5" prob={totals.home_over_2_5} />
        </div>
        <div>
          <p className="text-[10px] font-display uppercase tracking-widest text-zinc-600 mb-1">{awayLabel} goals</p>
          <Row label="Over 0.5" prob={totals.away_over_0_5} />
          <Row label="Over 1.5" prob={totals.away_over_1_5} />
          <Row label="Over 2.5" prob={totals.away_over_2_5} />
        </div>
      </div>
    </div>
  )
}
