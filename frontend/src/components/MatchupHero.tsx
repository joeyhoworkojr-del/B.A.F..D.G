import type { SoccerPredictResponse } from '../types'
import { PitchBackdrop, SoccerBall } from './PitchBackdrop'

const pct = (v: number) => Math.round(v * 100)

function TeamBadge({
  flag, name, elo, win, align,
}: { flag: string; name: string; elo: number; win: number; align: 'left' | 'right' }) {
  return (
    <div className={`flex min-w-0 flex-1 flex-col ${align === 'right' ? 'items-end text-right' : 'items-start text-left'}`}>
      <div className="grid h-16 w-16 place-items-center rounded-full border border-terminal-border bg-white text-4xl shadow-sm">
        {flag}
      </div>
      <div className="mt-2 max-w-full truncate font-display text-base font-bold text-zinc-100">{name}</div>
      <div className="font-mono text-[11px] text-zinc-500">Elo {Math.round(elo)}</div>
      <div className="mt-1 font-mono text-2xl font-bold text-signal-blue">{pct(win)}%</div>
    </div>
  )
}

/** Rich, art-forward header for a soccer prediction: pitch backdrop, circular
 *  crests, and the win/draw/win split as one clean bar. */
export function MatchupHero({ result }: { result: SoccerPredictResponse }) {
  const p = result.blended_probs
  return (
    <div className="relative overflow-hidden rounded-2xl border border-terminal-border bg-terminal-surface card-lift">
      <PitchBackdrop className="pointer-events-none absolute inset-0 h-full w-full" />
      <div className="relative px-5 py-6">
        <div className="flex items-stretch justify-between gap-4">
          <TeamBadge flag={result.home_team.flag} name={result.home_team.name}
            elo={result.home_team.elo} win={p.home_win} align="left" />

          <div className="flex shrink-0 flex-col items-center justify-center px-1">
            <SoccerBall className="h-9 w-9 text-signal-blue" />
            <span className="mt-1 font-display text-[11px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
              vs
            </span>
            <span className="mt-1 rounded-full bg-signal-amber-dim px-2 py-0.5 font-mono text-[10px] font-semibold text-signal-blue">
              {pct(p.draw)}% draw
            </span>
          </div>

          <TeamBadge flag={result.away_team.flag} name={result.away_team.name}
            elo={result.away_team.elo} win={p.away_win} align="right" />
        </div>

        {/* Win / draw / win split */}
        <div className="mt-5 flex h-2.5 overflow-hidden rounded-full ring-1 ring-terminal-border">
          <div style={{ width: `${pct(p.home_win)}%` }} className="bg-signal-blue" />
          <div style={{ width: `${pct(p.draw)}%` }} className="bg-zinc-400" />
          <div style={{ width: `${pct(p.away_win)}%` }} className="bg-signal-red" />
        </div>
        <div className="mt-1.5 flex justify-between font-mono text-[11px]">
          <span className="text-signal-blue">{result.home_team.name} {pct(p.home_win)}%</span>
          <span className="text-signal-red">{pct(p.away_win)}% {result.away_team.name}</span>
        </div>

        {/* xG strip */}
        <div className="mt-4 flex items-center justify-center gap-2 border-t border-terminal-border pt-3 font-mono text-sm">
          <span className="text-signal-blue font-semibold">{p.home_xg.toFixed(2)}</span>
          <span className="text-[10px] uppercase tracking-widest text-zinc-500">expected goals</span>
          <span className="text-signal-red font-semibold">{p.away_xg.toFixed(2)}</span>
        </div>
      </div>
    </div>
  )
}
