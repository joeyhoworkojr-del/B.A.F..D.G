import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import type { TodayGameOut, PlayByPlayOut, PlayOut, FootballLeague } from '../types'

const pct = (v?: number | null) => (v == null ? '—' : `${Math.round(v * 100)}%`)

/** Stylised football field with the possessing team's half tinted + the live
 *  down/distance called out, echoing a sportsbook live tile. */
function FieldGraphic({ entry }: { entry: TodayGameOut }) {
  const g = entry.game
  const live = g.state === 'in'
  const possHome = g.possession_abbr && g.possession_abbr === g.home_abbr
  const possAway = g.possession_abbr && g.possession_abbr === g.away_abbr
  return (
    <div className="relative overflow-hidden rounded-xl border border-terminal-border">
      <div className="flex h-40 w-full">
        {/* Away endzone side */}
        <div className={`flex w-1/2 items-center justify-start pl-3 ${possAway ? 'bg-signal-green/25' : 'bg-terminal-muted'}`}>
          <span className="text-[11px] font-black uppercase tracking-widest text-zinc-400">{g.away_abbr}</span>
        </div>
        {/* Home endzone side */}
        <div className={`flex w-1/2 items-center justify-end pr-3 ${possHome ? 'bg-signal-green/25' : 'bg-terminal-muted'}`}>
          <span className="text-[11px] font-black uppercase tracking-widest text-zinc-400">{g.home_abbr}</span>
        </div>
      </div>
      {/* Yard lines */}
      <div className="pointer-events-none absolute inset-0 flex items-stretch justify-between px-[12.5%]">
        {[10, 20, 30, 40, 50, 40, 30, 20, 10].map((n, i) => (
          <div key={i} className="flex flex-col items-center justify-between py-2 opacity-30">
            <div className="h-2 w-px bg-zinc-500" />
            <span className="text-[9px] text-zinc-500">{n}</span>
            <div className="h-2 w-px bg-zinc-500" />
          </div>
        ))}
      </div>
      {/* Center callout */}
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-1">
        {live ? (
          <>
            <span className="font-display text-xl font-black italic text-zinc-100">
              {g.down_distance || `Q${g.period ?? ''} ${g.clock ?? ''}`}
            </span>
            <span className="rounded-full bg-terminal-bg/80 px-3 py-1 text-[11px] font-semibold text-signal-green">
              {g.possession_abbr ? `${g.possession_abbr} ball` : 'In progress'}
            </span>
          </>
        ) : (
          <span className="rounded-full bg-terminal-bg/80 px-3 py-1 text-xs font-semibold text-zinc-400">
            {g.state === 'post' ? 'Final' : 'Kickoff pending'}
          </span>
        )}
      </div>
    </div>
  )
}

function PlayRow({ p }: { p: PlayOut }) {
  return (
    <div className={`flex gap-3 border-b border-terminal-border/60 py-2.5 ${p.scoring ? 'bg-signal-green/5' : ''}`}>
      <div className="w-14 shrink-0 text-right">
        <div className="text-[11px] font-mono font-semibold text-zinc-400">{p.period ? `Q${p.period}` : ''}</div>
        <div className="text-[10px] font-mono text-zinc-600">{p.clock}</div>
      </div>
      <div className="min-w-0 flex-1">
        <p className={`text-[13px] leading-snug ${p.scoring ? 'font-semibold text-signal-green' : 'text-zinc-200'}`}>
          {p.scoring && <span className="mr-1">🏈</span>}{p.text}
        </p>
      </div>
      {(p.home_score != null || p.away_score != null) && (
        <div className="w-12 shrink-0 text-right font-mono text-[11px] font-bold text-zinc-400 tabular-nums">
          {p.away_score}-{p.home_score}
        </div>
      )}
    </div>
  )
}

export function GameDetail() {
  const { league, eventId } = useParams<{ league: string; eventId: string }>()
  const lg = (league ?? 'nfl') as FootballLeague
  const [entry, setEntry] = useState<TodayGameOut | null>(null)
  const [pbp, setPbp] = useState<PlayByPlayOut | null>(null)
  const [tab, setTab] = useState<'model' | 'plays'>('plays')
  const [error, setError] = useState('')

  const load = useCallback(() => {
    if (!eventId) return
    api.today(lg)
      .then(d => {
        const found = d.games.find(x => x.game.event_id === eventId) ?? null
        setEntry(found)
        setError('')
      })
      .catch(e => setError(e.message))
    api.playByPlay(lg, eventId).then(setPbp).catch(() => {})
  }, [lg, eventId])

  useEffect(() => {
    load()
    const iv = setInterval(load, 20_000)
    return () => clearInterval(iv)
  }, [load])

  const g = entry?.game
  const m = entry?.model
  const live = g?.state === 'in'

  return (
    <div className="mx-auto max-w-2xl px-3 py-4 sm:px-4">
      <Link to="/" className="mb-3 inline-flex items-center gap-1 text-sm font-semibold text-zinc-400 hover:text-zinc-100">
        ← Scores
      </Link>

      {error && <div className="rounded-xl border border-signal-red/40 bg-terminal-surface p-4 text-sm text-signal-red">{error}</div>}

      {!entry && !error && <div className="skeleton h-64 rounded-xl" />}

      {g && (
        <>
          {/* Scoreboard header */}
          <div className="mb-4 rounded-xl border border-terminal-border bg-terminal-surface p-4">
            <div className="mb-3 flex items-center justify-center gap-4">
              <div className="flex flex-1 items-center justify-end gap-2 text-right">
                <span className="truncate text-sm font-bold text-zinc-100">{g.away}</span>
                {g.away_logo && <img src={g.away_logo} alt="" className="h-8 w-8 object-contain" />}
              </div>
              <div className="flex items-center gap-3 font-mono text-3xl font-black tabular-nums text-zinc-100">
                <span>{g.away_score ?? 0}</span>
                <span className="text-zinc-600">–</span>
                <span>{g.home_score ?? 0}</span>
              </div>
              <div className="flex flex-1 items-center gap-2">
                {g.home_logo && <img src={g.home_logo} alt="" className="h-8 w-8 object-contain" />}
                <span className="truncate text-sm font-bold text-zinc-100">{g.home}</span>
              </div>
            </div>
            <div className="text-center">
              {live ? (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-signal-green">
                  <span className="h-1.5 w-1.5 rounded-full bg-signal-green animate-pulse" />
                  {g.period ? `Q${g.period} ` : ''}{g.clock || g.detail}
                </span>
              ) : (
                <span className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{g.detail}</span>
              )}
            </div>
          </div>

          {/* Field graphic */}
          <div className="mb-4"><FieldGraphic entry={entry!} /></div>
          {g.last_play && live && (
            <p className="mb-4 rounded-lg border border-terminal-border bg-terminal-surface px-3 py-2 text-[13px] text-zinc-300">
              <span className="font-bold text-signal-green">Last play · </span>{g.last_play}
            </p>
          )}

          {/* Tabs */}
          <div className="mb-3 flex gap-2">
            {(['plays', 'model'] as const).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`rounded-full px-4 py-1.5 text-sm font-bold ${
                  tab === t ? 'bg-zinc-100 text-terminal-bg' : 'bg-terminal-surface text-zinc-400'
                }`}
              >
                {t === 'plays' ? 'Play-by-play' : 'Model'}
              </button>
            ))}
          </div>

          {tab === 'plays' && (
            <div className="rounded-xl border border-terminal-border bg-terminal-surface px-3">
              {pbp && pbp.plays.length > 0 ? (
                pbp.plays.map((p, i) => <PlayRow key={i} p={p} />)
              ) : (
                <p className="py-8 text-center text-sm text-zinc-500">
                  {g.state === 'pre' ? 'Play-by-play appears once the game kicks off.' : 'No plays available yet.'}
                </p>
              )}
            </div>
          )}

          {tab === 'model' && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">Projected score</p>
                  <p className="mt-1 font-mono text-2xl font-black text-zinc-100 tabular-nums">
                    {m?.proj_away_score ?? '—'} – {m?.proj_home_score ?? '—'}
                  </p>
                  <p className="mt-0.5 text-[11px] text-zinc-500">{g.away_abbr} @ {g.home_abbr}</p>
                </div>
                <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">Win probability</p>
                  <p className="mt-1 font-mono text-2xl font-black text-signal-green tabular-nums">
                    {pct(m?.calibrated_home_win ?? m?.home_win_prob)}
                  </p>
                  <p className="mt-0.5 text-[11px] text-zinc-500">{g.home_abbr} (home){m?.market_anchored ? ' · market-anchored' : ''}</p>
                </div>
              </div>

              {entry!.edges.filter(e => e.rating === 'A' || e.rating === 'B').length > 0 ? (
                <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4">
                  <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-zinc-500">Model edges vs the live line</p>
                  <div className="space-y-2">
                    {entry!.edges.filter(e => e.rating === 'A' || e.rating === 'B').map((e, i) => (
                      <div key={i} className="flex items-center gap-2 text-sm">
                        <span className="rounded-full bg-signal-amber-dim px-2 py-0.5 text-[11px] font-bold text-signal-amber">{e.rating}</span>
                        <span className="font-semibold text-zinc-100">{e.selection}</span>
                        <span className="ml-auto font-mono text-[12px] text-zinc-400">+{e.edge_pp.toFixed(1)}pp</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4 text-sm text-zinc-500">
                  {m
                    ? 'Model agrees with the market here — no strong edge. It only flags a play when the disagreement is large.'
                    : 'This matchup isn’t mapped to the model yet.'}
                </div>
              )}
              <p className="text-center text-[10px] text-zinc-600">
                Projected score blends the model with the market spread + total. Win prob is anchored to the live line.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
