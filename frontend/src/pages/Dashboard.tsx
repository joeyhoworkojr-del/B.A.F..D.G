import { useState, useEffect, useCallback, useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { DataFreshnessBadge } from '../components/game/DataFreshnessBadge'
import { FaqList } from '../components/faq/FaqList'
import { oddsSourceSentence } from '../components/OddsSource'
import { FAQ, FAQ_PREVIEW_IDS } from '../content/faq'
import { api } from '../api/client'
import type { TodayResponse, TodayGameOut, EdgeOut, AccuracyResponse, FootballLeague } from '../types'

const LEAGUES: { id: FootballLeague; label: string }[] = [
  { id: 'ncaaf', label: 'NCAAF' },
  { id: 'nfl', label: 'NFL' },
]
const LEAGUE_SPORT: Record<string, string> = { ncaaf: 'College Football', nfl: 'NFL' }

const pct = (v?: number | null) => (v == null ? '—' : `${Math.round(v * 100)}%`)
const fmtSpread = (s?: number | null) => (s == null ? '—' : s > 0 ? `+${s}` : `${s}`)
const dec = (a: number) => (a > 0 ? 1 + a / 100 : 1 + 100 / Math.abs(a))
function noVigHome(h?: number | null, a?: number | null): number | null {
  if (h == null || a == null) return null
  const ih = 1 / dec(h), ia = 1 / dec(a)
  return ih / (ih + ia)
}
function fmtKick(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  const day = d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
  const time = d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
  return `${day} • ${time}`
}

type Verdict = 'pick' | 'fade' | 'none'
function pair(p: number | null | undefined, topIsHigh: boolean): [Verdict, Verdict] {
  if (p == null) return ['none', 'none']
  const topPicked = topIsHigh ? p >= 0.5 : p < 0.5
  return [topPicked ? 'pick' : 'fade', topPicked ? 'fade' : 'pick']
}
const pillCls = (v: Verdict) =>
  v === 'pick' ? 'border-signal-green/50 bg-signal-green/15 text-signal-green'
  : v === 'fade' ? 'border-signal-red/40 bg-signal-red/10 text-signal-red'
  : 'border-terminal-border bg-terminal-muted/60 text-zinc-300'

function TeamLogo({ url, abbr }: { url?: string; abbr: string }) {
  return url
    ? <img src={url} alt="" className="h-7 w-7 object-contain" loading="lazy" />
    : <span className="grid h-7 w-7 place-items-center rounded bg-terminal-muted text-xs font-bold text-zinc-400">{abbr.slice(0, 3)}</span>
}

// ─── Header scores strip ──────────────────────────────────────────────────────
function ScoresStrip({ league, games }: { league: FootballLeague; games: TodayGameOut[] }) {
  const ordered = [...games].sort((a, b) => (a.game.state === 'in' ? -1 : 0) - (b.game.state === 'in' ? -1 : 0))
  return (
    <div className="flex items-stretch gap-0 overflow-x-auto border-b border-terminal-border/60 text-sm no-scrollbar">
      <div className="flex shrink-0 items-center gap-1 px-3 font-bold text-zinc-300">
        {league.toUpperCase()} <span className="text-zinc-500">›</span>
      </div>
      {ordered.slice(0, 12).map(({ game: g }) => {
        const live = g.state === 'in'
        return (
          <Link key={g.event_id} to={`/game/${league}/${g.event_id}`} state={{ game: g }}
            className="flex shrink-0 flex-col justify-center border-l border-terminal-border/60 px-3 py-2 hover:bg-terminal-muted/40">
            <span className="flex items-center gap-1.5 whitespace-nowrap font-semibold text-zinc-100">
              {live && <span className="h-1.5 w-1.5 rounded-full bg-signal-green" />}
              {g.away_abbr} {live || g.state === 'post' ? g.away_score ?? 0 : ''}
              <span className="text-zinc-500">{live || g.state === 'post' ? '–' : '@'}</span>
              {live || g.state === 'post' ? `${g.home_score ?? 0} ` : ''}{g.home_abbr}
            </span>
            <span className={`whitespace-nowrap text-xs ${live ? 'text-signal-green' : 'text-zinc-500'}`}>
              {live ? `${g.period ? `Q${g.period} ` : ''}${g.clock || g.detail}` : g.detail}
            </span>
          </Link>
        )
      })}
    </div>
  )
}

// ─── Stat bar ─────────────────────────────────────────────────────────────────
function StatBar({ acc }: { acc: AccuracyResponse | null }) {
  const perf = acc?.performance
  const total = perf?.total_picks ?? 0
  const wr = perf?.win_rate ?? null
  const wins = wr != null ? Math.round(wr * total) : 0
  const record = total > 0 ? `${wins}–${total - wins}` : '0–0'
  const roi = perf?.roi_pct
  const roiStr = roi == null ? '—' : `${roi >= 0 ? '+' : ''}${roi.toFixed(1)}%`
  const acc_ = wr == null ? '—' : `${Math.round(wr * 100)}%`
  const cells: [string, string, string][] = [
    ['Record', record, 'text-zinc-100'],
    ['ROI', roiStr, (roi ?? 0) >= 0 ? 'text-signal-green' : 'text-signal-red'],
    ['Accuracy', acc_, 'text-zinc-100'],
  ]
  return (
    <div className="grid grid-cols-3 overflow-hidden rounded-2xl border border-terminal-border bg-terminal-surface">
      {cells.map(([l, v, c], i) => (
        <div key={l} className={`px-4 py-4 text-center ${i > 0 ? 'border-l border-terminal-border' : ''}`}>
          <p className="text-xs font-bold uppercase tracking-widest text-zinc-500">{l}</p>
          <p className={`mt-1 font-mono text-2xl font-black tabular-nums ${c}`}>{v}</p>
        </div>
      ))}
    </div>
  )
}

// ─── Live model card ──────────────────────────────────────────────────────────
function LiveCard({ league, entry }: { league: FootballLeague; entry: TodayGameOut }) {
  const g = entry.game
  const m = entry.model
  const homeWin = m ? (m.live && m.live_home_win != null ? m.live_home_win : (m.calibrated_home_win ?? m.home_win_prob)) : 0.5
  const favHome = homeWin >= 0.5
  const modelP = favHome ? homeWin : 1 - homeWin
  const mktHome = noVigHome(g.market_home_ml, g.market_away_ml)
  const marketP = mktHome == null ? null : (favHome ? mktHome : 1 - mktHome)
  const edge = marketP == null ? null : modelP - marketP

  return (
    <div className="relative overflow-hidden rounded-2xl border border-signal-green/40 bg-terminal-surface">
      <div className="absolute inset-x-0 top-0 h-0.5 bg-signal-green/70" />
      <div className="flex items-center justify-between px-4 pt-3">
        <span className="inline-flex items-center gap-2 rounded-full bg-signal-green/15 px-2.5 py-1 text-xs font-bold text-signal-green">
          <span className="h-1.5 w-1.5 rounded-full bg-signal-green animate-pulse" /> LIVE
          <span className="text-signal-green/90">{g.period ? `Q${g.period} ` : ''}{g.clock || g.detail}</span>
        </span>
        <span className="text-xs text-zinc-500">{LEAGUE_SPORT[league]}</span>
      </div>
      <div className="flex items-stretch gap-3 p-4">
        <Link to={`/game/${league}/${g.event_id}`} state={{ game: g }} className="min-w-0 flex-1 space-y-3">
          {[['away', g.away, g.away_abbr, g.away_logo, g.away_score], ['home', g.home, g.home_abbr, g.home_logo, g.home_score]].map(
            ([side, name, abbr, logo, score]) => (
              <div key={side as string} className="flex items-center gap-2.5">
                <TeamLogo url={logo as string} abbr={abbr as string} />
                <span className="truncate text-[15px] font-bold text-zinc-100">{name}</span>
                <span className="ml-auto font-mono text-2xl font-black tabular-nums text-zinc-100">{score ?? 0}</span>
              </div>
            ),
          )}
        </Link>
        {m && (
          <div className="w-[42%] shrink-0 border-l border-terminal-border pl-3">
            <div className="space-y-1.5 text-[13px]">
              <Row label="Model" value={pct(modelP)} valueCls="text-signal-green font-black" />
              <Row label="Market" value={pct(marketP)} valueCls="text-zinc-100 font-bold" />
              <Row label="Edge" value={edge == null ? '—' : `${edge >= 0 ? '+' : ''}${Math.round(edge * 100)}%`} valueCls={(edge ?? 0) >= 0 ? 'text-signal-green font-bold' : 'text-signal-red font-bold'} />
            </div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-terminal-muted">
              <div className="h-full rounded-full bg-signal-green" style={{ width: `${Math.round(modelP * 100)}%` }} />
            </div>
            <p className="mt-2 text-right text-xs text-zinc-500">
              {m.time_remaining_pct != null ? `${Math.round(m.time_remaining_pct)}% left` : 'Updated live'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
function Row({ label, value, valueCls }: { label: string; value: string; valueCls: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{label}</span>
      <span className={`font-mono tabular-nums ${valueCls}`}>{value}</span>
    </div>
  )
}

// ─── Top-edge card ────────────────────────────────────────────────────────────
function bestEdge(edges: EdgeOut[]): EdgeOut | null {
  const ab = edges.filter(e => e.rating === 'A' || e.rating === 'B')
  return ab.length ? ab.reduce((x, y) => (y.edge_pp > x.edge_pp ? y : x)) : null
}

function EdgeCard({ league, entry }: { league: FootballLeague; entry: TodayGameOut }) {
  const g = entry.game
  const m = entry.model!
  const e = bestEdge(entry.edges)!
  const spread = g.market_spread
  const ou = g.market_over_under
  const [sprTop, sprBot] = pair(m.home_cover_prob, false) // top=away
  const [ouTop, ouBot] = pair(m.over_prob, true)          // top=Over

  const Pill = ({ v, verdict }: { v: string; verdict: Verdict }) => (
    <div className={`grid h-9 w-[68px] place-items-center rounded-lg border text-[13px] font-bold tabular-nums ${pillCls(verdict)}`}>{v}</div>
  )
  return (
    <div className="rounded-2xl border border-terminal-border bg-terminal-surface p-4">
      <div className="mb-3 flex items-center justify-between text-xs text-zinc-500">
        <span>{fmtKick(g.kickoff)}</span>
        <span>{LEAGUE_SPORT[league]}</span>
      </div>
      <div className="flex items-center gap-3">
        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex items-center gap-2.5"><TeamLogo url={g.away_logo} abbr={g.away_abbr} /><span className="truncate text-[15px] font-bold text-zinc-100">{g.away}</span></div>
          <div className="flex items-center gap-2.5"><TeamLogo url={g.home_logo} abbr={g.home_abbr} /><span className="truncate text-[15px] font-bold text-zinc-100">{g.home}</span></div>
        </div>
        <div className="flex shrink-0 gap-4">
          <div className="space-y-2">
            <p className="text-center text-xs font-semibold uppercase tracking-wide text-zinc-500">Spread</p>
            <Pill v={spread != null ? fmtSpread(-spread) : '—'} verdict={sprTop} />
            <Pill v={spread != null ? fmtSpread(spread) : '—'} verdict={sprBot} />
          </div>
          <div className="space-y-2">
            <p className="text-center text-xs font-semibold uppercase tracking-wide text-zinc-500">Total</p>
            <Pill v={ou != null ? `O ${ou}` : '—'} verdict={ouTop} />
            <Pill v={ou != null ? `U ${ou}` : '—'} verdict={ouBot} />
          </div>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-terminal-border/70 pt-3">
        <Stat label="Model" value={pct(e.model_prob)} />
        <Stat label="Market" value={pct(e.market_prob)} />
        <Stat label="Edge" value={`+${e.edge_pp.toFixed(0)}%`} green />
        <Link to={`/game/${league}/${g.event_id}?market=${e.market.toLowerCase().includes("total") ? "total" : e.market.toLowerCase().includes("spread") ? "spread" : "moneyline"}`} state={{ game: g }}
          className="rounded-lg border border-signal-amber/50 bg-signal-amber/15 px-3 py-1.5 text-[13px] font-bold text-signal-amber">
          {e.rating} · {e.selection} ›
        </Link>
        <Link to={`/game/${league}/${g.event_id}?market=${e.market.toLowerCase().includes("total") ? "total" : e.market.toLowerCase().includes("spread") ? "spread" : "moneyline"}#why`} state={{ game: g }} className="ml-auto whitespace-nowrap text-xs font-semibold text-zinc-400 hover:text-zinc-200">
          Why this edge? ›
        </Link>
      </div>
    </div>
  )
}
function Stat({ label, value, green }: { label: string; value: string; green?: boolean }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{label}</p>
      <p className={`font-mono text-sm font-bold tabular-nums ${green ? 'text-signal-green' : 'text-zinc-100'}`}>{value}</p>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export function Dashboard() {
  const [params, setParams] = useSearchParams()
  const query = params.get('q') ?? ''
  const [league, setLeague] = useState<FootballLeague>('ncaaf')
  const [data, setData] = useState<TodayResponse | null>(null)
  const [acc, setAcc] = useState<AccuracyResponse | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback((lg: FootballLeague) => {
    api.today(lg).then(d => { setData(d); setError('') }).catch(e => setError(e.message)).finally(() => setLoading(false))
  }, [])

  useEffect(() => { api.accuracy().then(setAcc).catch(() => {}) }, [])
  useEffect(() => {
    setLoading(true); setData(null); load(league)
    const iv = setInterval(() => load(league), 30_000)
    return () => clearInterval(iv)
  }, [league, load])

  // Search matches either team's name or abbreviation, so "bama" and "ALA"
  // both find the same game.
  const games = useMemo(() => {
    const all = data?.games ?? []
    const q = query.trim().toLowerCase()
    if (!q) return all
    return all.filter(({ game: g }) =>
      [g.home, g.away, g.home_abbr, g.away_abbr].some(v => v.toLowerCase().includes(q)))
  }, [data, query])

  const liveGames = games.filter(x => x.game.state === 'in')
  const edgeGames = games
    .filter(x => x.game.state === 'pre' && x.mapped && x.model && bestEdge(x.edges))
    .sort((a, b) => (bestEdge(b.edges)!.edge_pp) - (bestEdge(a.edges)!.edge_pp))
    .slice(0, 12)

  return (
    <div className="pb-4">
      {games.length > 0 && <ScoresStrip league={league} games={games} />}

      <div className="mx-auto w-full max-w-[1200px] space-y-5 px-4 pt-4">
        <div>
          <h1 className="font-display text-3xl font-black tracking-tight text-zinc-100">Game Center</h1>
          <p className="mt-0.5 text-sm text-zinc-400">AI-powered projections &amp; market edges</p>
        </div>

        <StatBar acc={acc} />

        {query.trim() && (
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="text-zinc-400">
              Showing games matching <span className="font-bold text-zinc-100">“{query.trim()}”</span>
              {' '}— {games.length} of {data?.games.length ?? 0}
            </span>
            <button
              type="button"
              onClick={() => { const next = new URLSearchParams(params); next.delete('q'); setParams(next) }}
              className="tap inline-flex items-center rounded-full border border-terminal-border px-3 text-xs font-semibold text-zinc-400 hover:text-zinc-100"
            >
              Clear search
            </button>
          </div>
        )}

        {/* Tabs + live badge */}
        <div className="flex items-center gap-2">
          <div className="flex gap-2">
            {LEAGUES.map(l => (
              <button key={l.id} onClick={() => setLeague(l.id)}
                className={`rounded-full px-5 py-1.5 text-sm font-bold transition ${
                  league === l.id
                    ? 'bg-brand text-white shadow-card'
                    : 'bg-terminal-muted text-zinc-400 hover:text-zinc-100'
                }`}>
                {l.label}
              </button>
            ))}
          </div>
          {liveGames.length > 0 && (
            <span className="ml-auto inline-flex items-center gap-1.5 rounded-full bg-signal-green/15 px-3 py-1.5 text-xs font-bold text-signal-green">
              <span className="h-1.5 w-1.5 rounded-full bg-signal-green animate-pulse" /> {liveGames.length} LIVE
            </span>
          )}
        </div>

        {error && <div className="rounded-2xl border border-signal-red/40 bg-terminal-surface p-4 text-sm text-signal-red">Couldn’t load games: {error}</div>}
        {loading && !data && <div className="space-y-4"><div className="skeleton h-40 rounded-2xl" /><div className="skeleton h-44 rounded-2xl" /></div>}

        {liveGames.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-500">Live now</h2>
            <div className="grid gap-3 lg:grid-cols-2">
              {liveGames.map(entry => <LiveCard key={entry.game.event_id} league={league} entry={entry} />)}
            </div>
          </div>
        )}

        {edgeGames.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-500">Top edges</h2>
            <div className="grid gap-3 lg:grid-cols-2">
              {edgeGames.map(entry => <EdgeCard key={entry.game.event_id} league={league} entry={entry} />)}
            </div>
          </div>
        )}

        {!loading && liveGames.length === 0 && edgeGames.length === 0 && !error && (
          <div className="rounded-2xl border border-dashed border-terminal-border bg-terminal-surface p-10 text-center">
            <p className="font-display text-lg font-bold text-zinc-100">No edges on the board</p>
            <p className="mx-auto mt-1 max-w-sm text-sm text-zinc-500">
              {query.trim()
                ? `Nothing in the ${LEAGUE_SPORT[league]} window matches “${query.trim()}”.`
                : `No live games or model edges for ${LEAGUE_SPORT[league]} in today’s window. This fills in automatically on game day.`}
            </p>
          </div>
        )}

        <section aria-labelledby="faq-preview" className="pt-2">
          <div className="mb-2 flex items-end justify-between gap-3">
            <h2 id="faq-preview" className="text-xs font-bold uppercase tracking-widest text-zinc-500">
              Common questions
            </h2>
            <Link to="/faq" className="text-sm font-semibold text-brand hover:underline">
              All questions ›
            </Link>
          </div>
          <FaqList entries={FAQ.filter(e => FAQ_PREVIEW_IDS.includes(e.id))} />
        </section>

        <div className="flex flex-wrap items-center justify-center gap-2 pt-1 text-xs text-zinc-500">
          <span>{oddsSourceSentence(data?.market_source)}</span>
          <span aria-hidden="true">•</span>
          {/* Age comes from the payload's own timestamp — a running poll timer
              is not evidence that the data on screen is current. */}
          <DataFreshnessBadge
            fetchedAt={data?.fetched_at}
            ok={data?.source_ok !== false && !error}
            staleAfterSeconds={90}
          />
        </div>
      </div>
    </div>
  )
}
