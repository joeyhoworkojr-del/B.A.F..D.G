import type { NFLPredictResponse, GridironLeague } from '../types'
import { fieldBackdrop, SportGlyph, type Sport } from './SportArt'

const pct = (v: number) => Math.round(v * 100)

function Side({
  code, name, elo, pts, win, unit, align,
}: { code: string; name: string; elo: number; pts: number; win: number; unit: string; align: 'left' | 'right' }) {
  return (
    <div className={`flex min-w-0 flex-1 flex-col ${align === 'right' ? 'items-end text-right' : 'items-start text-left'}`}>
      <div className="grid h-14 w-14 place-items-center rounded-2xl border border-terminal-border bg-white font-display text-lg font-bold text-zinc-100 shadow-sm">
        {code}
      </div>
      <div className="mt-2 max-w-full truncate font-display text-sm font-bold text-zinc-100">{name}</div>
      <div className="font-mono text-[11px] text-zinc-500">Elo {Math.round(elo)}</div>
      <div className="mt-1 flex items-baseline gap-1.5">
        <span className="font-mono text-2xl font-bold text-signal-blue">{pct(win)}%</span>
        <span className="font-mono text-[11px] text-zinc-500">{pts.toFixed(1)} {unit}</span>
      </div>
    </div>
  )
}

/** Art-forward matchup header for gridiron/baseball predictions. */
export function GridironMatchup({ result, league, unit }: { result: NFLPredictResponse; league: GridironLeague; unit: string }) {
  const h = result.home_team, a = result.away_team
  return (
    <div className="relative overflow-hidden rounded-2xl border border-terminal-border bg-terminal-surface card-lift">
      {fieldBackdrop(league as Sport, 'pointer-events-none absolute inset-0 h-full w-full')}
      <div className="relative px-5 py-6">
        <div className="flex items-stretch justify-between gap-4">
          <Side code={h.code} name={h.name} elo={h.elo} pts={result.home_expected_pts} win={result.home_win_prob} unit={unit} align="left" />
          <div className="flex shrink-0 flex-col items-center justify-center px-1">
            <SportGlyph sport={league as Sport} className="h-9 w-9 text-signal-blue" />
            <span className="mt-1 font-display text-[11px] font-semibold uppercase tracking-[0.2em] text-zinc-500">@</span>
          </div>
          <Side code={a.code} name={a.name} elo={a.elo} pts={result.away_expected_pts} win={result.away_win_prob} unit={unit} align="right" />
        </div>

        {/* win split */}
        <div className="mt-5 flex h-2.5 overflow-hidden rounded-full ring-1 ring-terminal-border">
          <div style={{ width: `${pct(result.home_win_prob)}%` }} className="bg-signal-blue" />
          <div style={{ width: `${pct(result.away_win_prob)}%` }} className="bg-signal-red" />
        </div>
        <div className="mt-1.5 flex justify-between font-mono text-[11px]">
          <span className="text-signal-blue">{h.code} {pct(result.home_win_prob)}%</span>
          <span className="text-signal-red">{pct(result.away_win_prob)}% {a.code}</span>
        </div>

        {/* projected total */}
        <div className="mt-4 flex items-center justify-center gap-2 border-t border-terminal-border pt-3 font-mono text-sm">
          <span className="font-semibold text-zinc-200">{result.total_points_estimate.toFixed(1)}</span>
          <span className="text-[10px] uppercase tracking-widest text-zinc-500">projected total {unit}</span>
        </div>
      </div>
    </div>
  )
}
