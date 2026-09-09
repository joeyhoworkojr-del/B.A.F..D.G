import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { DataFreshnessBadge } from '../components/game/DataFreshnessBadge'
import { PropsStrip } from '../components/props/PropsStrip'
import { NewsStrip } from '../components/news/NewsStrip'
import { FaqList } from '../components/faq/FaqList'
import { oddsSourceSentence } from '../components/OddsSource'
import { FAQ, FAQ_PREVIEW_IDS } from '../content/faq'
import { api } from '../api/client'
import { useSession } from '../session/SessionProvider'
import type { BoardDay, BoardEntry, BoardResponse, EdgeOut, AccuracyResponse } from '../types'

const LEAGUE_LABEL: Record<string, string> = { ncaaf: 'NCAAF', nfl: 'NFL' }

/** Cards rendered before the list offers to show the rest. A college Saturday
 *  is two hundred games; a homepage that dumps all of them is not a homepage. */
const VISIBLE_STEP = 24

const pct = (v?: number | null) => (v == null ? '—' : `${Math.round(v * 100)}%`)
const fmtSpread = (s?: number | null) => (s == null ? '—' : s > 0 ? `+${s}` : `${s}`)
const dec = (a: number) => (a > 0 ? 1 + a / 100 : 1 + 100 / Math.abs(a))
function noVigHome(h?: number | null, a?: number | null): number | null {
  if (h == null || a == null) return null
  const ih = 1 / dec(h), ia = 1 / dec(a)
  return ih / (ih + ia)
}
function fmtTime(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
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

function LeagueTag({ league }: { league: string }) {
  return (
    <span className="rounded border border-terminal-border px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-zinc-500">
      {LEAGUE_LABEL[league] ?? league.toUpperCase()}
    </span>
  )
}

// ─── Header scores strip ──────────────────────────────────────────────────────
function ScoresStrip({ games }: { games: BoardEntry[] }) {
  if (games.length === 0) return null
  return (
    <div className="flex items-stretch gap-0 overflow-x-auto border-b border-terminal-border/60 text-sm no-scrollbar">
      {games.slice(0, 14).map(({ game: g, league }) => {
        const live = g.state === 'in'
        const done = g.state === 'post'
        return (
          <Link key={`${league}-${g.event_id}`} to={`/game/${league}/${g.event_id}`} state={{ game: g }}
            className="flex shrink-0 flex-col justify-center border-l border-terminal-border/60 px-3 py-2 first:border-l-0 hover:bg-terminal-muted/40">
            <span className="flex items-center gap-1.5 whitespace-nowrap font-semibold text-zinc-100">
              {live && <span className="h-1.5 w-1.5 rounded-full bg-signal-green" />}
              {g.away_abbr} {live || done ? g.away_score ?? 0 : ''}
              <span className="text-zinc-500">{live || done ? '–' : '@'}</span>
              {live || done ? `${g.home_score ?? 0} ` : ''}{g.home_abbr}
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
        <div key={l} className={`px-4 py-3 text-center ${i > 0 ? 'border-l border-terminal-border' : ''}`}>
          <p className="text-xs font-bold uppercase tracking-widest text-zinc-500">{l}</p>
          <p className={`mt-0.5 font-mono text-2xl font-black tabular-nums ${c}`}>{v}</p>
        </div>
      ))}
    </div>
  )
}

// ─── Live model card ──────────────────────────────────────────────────────────
function LiveCard({ entry }: { entry: BoardEntry }) {
  const { game: g, model: m, league } = entry
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
        <LeagueTag league={league} />
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
      {/* Who has it and where. The live projection reads this, so showing it
          here is what makes a probability move legible from the board. */}
      {(g.possession_abbr || g.down_distance) && (
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-terminal-border px-4 py-2 text-xs">
          {g.possession_abbr && (
            <span className="rounded-full bg-signal-green/15 px-2 py-0.5 font-bold text-signal-green">
              {g.possession_abbr} ball
            </span>
          )}
          {g.down_distance && <span className="text-zinc-400">{g.down_distance}</span>}
          {m?.red_zone && (
            <span className="rounded-full bg-signal-red-dim px-2 py-0.5 font-bold text-signal-red">
              Red zone
            </span>
          )}
        </div>
      )}
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

// ─── Pre-game card ────────────────────────────────────────────────────────────
function bestEdge(edges: EdgeOut[]): EdgeOut | null {
  const ab = edges.filter(e => e.rating === 'A' || e.rating === 'B')
  return ab.length ? ab.reduce((x, y) => (y.edge_pp > x.edge_pp ? y : x)) : null
}

function marketKey(market: string): string {
  const m = market.toLowerCase()
  return m.includes('total') ? 'total' : m.includes('spread') ? 'spread' : 'moneyline'
}

function EdgeCard({ entry }: { entry: BoardEntry }) {
  const { game: g, model: m, league } = entry
  // Not every game has an edge worth naming, and a followed team's game is
  // shown whether it does or not. The non-null assertions here used to crash
  // the whole board on the first game without one.
  const e = bestEdge(entry.edges)
  const spread = g.market_spread
  const ou = g.market_over_under
  // An unmapped game has no model at all, which is a real state on the board.
  const [sprTop, sprBot] = pair(m?.home_cover_prob ?? null, false) // top=away
  const [ouTop, ouBot] = pair(m?.over_prob ?? null, true)          // top=Over

  const Pill = ({ v, verdict }: { v: string; verdict: Verdict }) => (
    <div className={`grid h-9 w-[68px] place-items-center rounded-lg border text-[13px] font-bold tabular-nums ${pillCls(verdict)}`}>{v}</div>
  )
  return (
    <div className="rounded-2xl border border-terminal-border bg-terminal-surface p-4">
      <div className="mb-3 flex items-center justify-between gap-2 text-xs text-zinc-500">
        <span>{g.state === 'post' ? g.detail : fmtTime(g.kickoff)}</span>
        <LeagueTag league={league} />
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
        {e ? (
          <>
            <Stat label="Model" value={pct(e.model_prob)} />
            <Stat label="Market" value={pct(e.market_prob)} />
            <Stat label="Edge" value={`+${e.edge_pp.toFixed(0)}%`} green />
            <Link to={`/game/${league}/${g.event_id}?market=${marketKey(e.market)}`} state={{ game: g }}
              className="rounded-lg border border-signal-amber/50 bg-signal-amber/15 px-3 py-1.5 text-[13px] font-bold text-signal-amber">
              {e.rating} · {e.selection} ›
            </Link>
            <Link to={`/game/${league}/${g.event_id}?market=${marketKey(e.market)}#why`} state={{ game: g }} className="ml-auto whitespace-nowrap text-xs font-semibold text-zinc-400 hover:text-zinc-200">
              Why this edge? ›
            </Link>
          </>
        ) : (
          <>
            {/* Beyond the board's projection cap the model has not been run on
                this game at all, which is a different thing from having run and
                found nothing. Saying "no edge" for either would be a claim the
                model never made. */}
            <span className="text-xs text-zinc-500">
              {entry.projected
                ? 'The model and the market agree on this one — no edge is claimed.'
                : 'Not projected yet — opening the game runs the model on it.'}
            </span>
            <Link to={`/game/${league}/${g.event_id}`} state={{ game: g }} className="ml-auto whitespace-nowrap text-xs font-semibold text-zinc-400 hover:text-zinc-200">
              View game ›
            </Link>
          </>
        )}
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

/**
 * A game that has already been played.
 *
 * Deliberately not the pre-game card: spread and total pills read as picks,
 * and offering a pick on a game that finished two hours ago is a claim about
 * something already decided. The graded result lives on Results; here it is
 * the score and a way in.
 */
function FinalCard({ entry }: { entry: BoardEntry }) {
  const { game: g, league } = entry
  const homeWon = (g.home_score ?? 0) > (g.away_score ?? 0)
  return (
    <Link
      to={`/game/${league}/${g.event_id}`}
      state={{ game: g }}
      className="block rounded-2xl border border-terminal-border bg-terminal-surface p-4 hover:border-zinc-500"
    >
      <div className="mb-3 flex items-center justify-between gap-2 text-xs text-zinc-500">
        <span className="font-semibold uppercase tracking-wide">Final</span>
        <LeagueTag league={league} />
      </div>
      <div className="space-y-3">
        {[[g.away, g.away_abbr, g.away_logo, g.away_score, !homeWon],
          [g.home, g.home_abbr, g.home_logo, g.home_score, homeWon]].map(
          ([name, abbr, logo, score, won]) => (
            <div key={abbr as string} className="flex items-center gap-2.5">
              <TeamLogo url={logo as string} abbr={abbr as string} />
              <span className={`truncate text-[15px] font-bold ${won ? 'text-zinc-100' : 'text-zinc-500'}`}>
                {name}
              </span>
              <span className={`ml-auto font-mono text-2xl font-black tabular-nums ${won ? 'text-zinc-100' : 'text-zinc-500'}`}>
                {score ?? 0}
              </span>
            </div>
          ),
        )}
      </div>
    </Link>
  )
}

function GameCard({ entry }: { entry: BoardEntry }) {
  if (entry.game.state === 'in') return <LiveCard entry={entry} />
  if (entry.game.state === 'post') return <FinalCard entry={entry} />
  return <EdgeCard entry={entry} />
}

/** Live first, then the biggest claimed edge, then kickoff order. */
function boardOrder(a: BoardEntry, b: BoardEntry): number {
  // In progress, then still to come, then already played. A finished game is
  // the least useful thing on a board about what to watch, but it is what
  // someone looking for this afternoon's score came for, so it stays.
  const rank = (e: BoardEntry) => (e.game.state === 'in' ? 0 : e.game.state === 'pre' ? 1 : 2)
  const liveA = rank(a)
  const liveB = rank(b)
  if (liveA !== liveB) return liveA - liveB
  const ea = bestEdge(a.edges)?.edge_pp ?? -1
  const eb = bestEdge(b.edges)?.edge_pp ?? -1
  if (ea !== eb) return eb - ea
  return (a.game.kickoff || '').localeCompare(b.game.kickoff || '')
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export function Dashboard() {
  const [params, setParams] = useSearchParams()
  const query = params.get('q') ?? ''
  const { user } = useSession()
  const [data, setData] = useState<BoardResponse | null>(null)
  const [acc, setAcc] = useState<AccuracyResponse | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [dayDate, setDayDate] = useState<string | null>(null)
  const [visible, setVisible] = useState(VISIBLE_STEP)
  const hasLive = useRef(false)

  const load = useCallback(() => {
    api.board()
      .then(d => { setData(d); setError('') })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { api.accuracy().then(setAcc).catch(() => {}) }, [])
  useEffect(() => {
    load()
    // A running clock needs refreshing near the rate it changes; a board with
    // nothing in progress does not.
    const iv = setInterval(load, hasLive.current ? 15_000 : 60_000)
    return () => clearInterval(iv)
  }, [load])

  // Search matches either team's name or abbreviation, so "bama" and "ALA"
  // both find the same game. It searches the whole window, not one day.
  const days: BoardDay[] = useMemo(() => {
    const all = data?.days ?? []
    const q = query.trim().toLowerCase()
    if (!q) return all
    return all
      .map(d => ({
        ...d,
        games: d.games.filter(({ game: g }) =>
          [g.home, g.away, g.home_abbr, g.away_abbr].some(v => v.toLowerCase().includes(q))),
      }))
      .filter(d => d.games.length > 0)
  }, [data, query])

  // The first day with anything on it. On a Wednesday in September that is
  // Thursday, and the board opens there rather than on an empty Today.
  const day = useMemo(
    () => days.find(d => d.date === dayDate) ?? days[0] ?? null,
    [days, dayDate],
  )
  useEffect(() => { setVisible(VISIBLE_STEP) }, [day?.date, query])

  const dayGames = useMemo(() => [...(day?.games ?? [])].sort(boardOrder), [day])
  const liveGames = useMemo(
    () => days.flatMap(d => d.games).filter(e => e.game.state === 'in'),
    [days],
  )
  hasLive.current = liveGames.length > 0

  // Games involving a team this person follows, pulled to the top. Stored as
  // `league:CODE` so a college and an NFL team sharing an abbreviation stay
  // distinct — several do.
  const followedKeys = useMemo(
    () => new Set((user?.favourite_teams ?? []).map(k => k.toLowerCase())),
    [user],
  )
  const isFollowed = useCallback(
    (e: BoardEntry) =>
      followedKeys.has(`${e.league}:${(e.game.home_abbr || '').toLowerCase()}`) ||
      followedKeys.has(`${e.league}:${(e.game.away_abbr || '').toLowerCase()}`),
    [followedKeys],
  )
  const followed = useMemo(() => dayGames.filter(isFollowed), [dayGames, isFollowed])
  const rest = useMemo(() => dayGames.filter(e => !isFollowed(e)), [dayGames, isFollowed])

  // Props go under the game they belong to. The live game if there is one,
  // otherwise the first thing on the selected day.
  const featured = liveGames[0] ?? dayGames[0] ?? null

  return (
    <div className="pb-4">
      <ScoresStrip games={liveGames.length > 0 ? liveGames : dayGames} />

      <div className="mx-auto w-full max-w-[1200px] space-y-4 px-4 pt-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="font-display text-3xl font-black tracking-tight text-zinc-100">Game Center</h1>
            <p className="mt-0.5 text-sm text-zinc-400">
              NFL and college football on one board, with the model’s number beside the market’s.
            </p>
          </div>
          {liveGames.length > 0 && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-signal-green/15 px-3 py-1.5 text-xs font-bold text-signal-green">
              <span className="h-1.5 w-1.5 rounded-full bg-signal-green animate-pulse" /> {liveGames.length} LIVE
            </span>
          )}
        </div>

        <StatBar acc={acc} />

        {query.trim() && (
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="text-zinc-400">
              Showing games matching <span className="font-bold text-zinc-100">“{query.trim()}”</span>
              {' '}— {days.reduce((n, d) => n + d.games.length, 0)} of {data?.total_games ?? 0}
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

        {/* One row of days rather than two league tabs. A day with nothing on
            it is not offered at all, which is why the board never opens empty. */}
        {days.length > 0 && (
          <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar" role="tablist" aria-label="Days with games">
            {days.map(d => (
              <button
                key={d.date}
                type="button"
                role="tab"
                aria-selected={d.date === day?.date}
                onClick={() => setDayDate(d.date)}
                className={`tap shrink-0 rounded-full px-4 text-sm font-bold transition ${
                  d.date === day?.date
                    ? 'bg-brand text-white shadow-card'
                    : 'bg-terminal-muted text-zinc-400 hover:text-zinc-100'
                }`}
              >
                {d.label}
                <span className={`ml-1.5 font-mono text-xs ${d.date === day?.date ? 'text-white/70' : 'text-zinc-500'}`}>
                  {d.games.length}
                </span>
              </button>
            ))}
          </div>
        )}

        {error && <div className="rounded-2xl border border-signal-red/40 bg-terminal-surface p-4 text-sm text-signal-red">Couldn’t load games: {error}</div>}
        {loading && !data && <div className="space-y-4"><div className="skeleton h-40 rounded-2xl" /><div className="skeleton h-44 rounded-2xl" /></div>}

        {followed.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-500">Your teams</h2>
            <div className="grid gap-3 lg:grid-cols-2">
              {followed.map(entry => <GameCard key={`fav-${entry.league}-${entry.game.event_id}`} entry={entry} />)}
            </div>
          </div>
        )}

        {/* Signed in, teams chosen, none playing on this day — worth saying,
            because an absent section reads as a broken setting. */}
        {user && (user.favourite_teams?.length ?? 0) > 0 && followed.length === 0 && !loading && day && (
          <p className="text-sm text-zinc-500">
            None of the teams you follow are playing {day.label.toLowerCase()}.
          </p>
        )}

        {rest.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-500">
              {day?.label ?? 'On the board'}
              {day && Object.entries(day.by_league).some(([, n]) => n > 0) && (
                <span className="ml-2 font-normal normal-case tracking-normal text-zinc-600">
                  {Object.entries(day.by_league)
                    .filter(([, n]) => n > 0)
                    .map(([lg, n]) => `${n} ${LEAGUE_LABEL[lg] ?? lg.toUpperCase()}`)
                    .join(' · ')}
                </span>
              )}
            </h2>
            <div className="grid gap-3 lg:grid-cols-2">
              {rest.slice(0, visible).map(entry => (
                <GameCard key={`${entry.league}-${entry.game.event_id}`} entry={entry} />
              ))}
            </div>
            {rest.length > visible && (
              <button
                type="button"
                onClick={() => setVisible(v => v + VISIBLE_STEP)}
                className="tap w-full rounded-2xl border border-terminal-border bg-terminal-surface py-3 text-sm font-bold text-zinc-300 hover:text-zinc-100"
              >
                Show {Math.min(VISIBLE_STEP, rest.length - visible)} more of {rest.length}
              </button>
            )}
          </div>
        )}

        {!loading && dayGames.length === 0 && !error && (
          <div className="rounded-2xl border border-dashed border-terminal-border bg-terminal-surface p-10 text-center">
            <p className="font-display text-lg font-bold text-zinc-100">Nothing on the board</p>
            <p className="mx-auto mt-1 max-w-sm text-sm text-zinc-500">
              {query.trim()
                ? `No NFL or college game in the next week matches “${query.trim()}”.`
                : data?.note || 'No NFL or college football scheduled in the next week. This fills in automatically as the schedule is released.'}
            </p>
          </div>
        )}

        {featured && (
          <PropsStrip league={featured.league} eventId={featured.game.event_id} />
        )}

        <NewsStrip />

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
