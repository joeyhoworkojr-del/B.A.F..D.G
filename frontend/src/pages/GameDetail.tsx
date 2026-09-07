import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useSearchParams, Link, useLocation } from 'react-router-dom'
import type { LiveGameOut, MarketKey, PlayOut } from '../types'
import { useGameDetail } from '../hooks/useGameDetail'
import { GameHeader } from '../components/game/GameHeader'
import { Panel } from '../components/game/Panel'
import { PrimaryEdgeCard } from '../components/game/PrimaryEdgeCard'
import { MarketSelector } from '../components/game/MarketSelector'
import { ProbabilityComparison } from '../components/game/ProbabilityComparison'
import { SportsbookOddsTable } from '../components/game/SportsbookOddsTable'
import { ModelExplanation } from '../components/game/ModelExplanation'
import { LineMovementChart } from '../components/game/LineMovementChart'
import { MakeYourPick } from '../components/picks/MakeYourPick'
import { GameCommunity } from '../components/picks/GameCommunity'
import { useGameCommunity } from '../hooks/useGameCommunity'
import { LiveWinProbabilityChart } from '../components/game/LiveWinProbabilityChart'
import { LockedPremiumPanel } from '../components/game/LockedPremiumPanel'
import type { Point } from '../components/game/MiniChart'

const LEAGUE_LABEL: Record<string, string> = { ncaaf: 'College Football', nfl: 'NFL' }
const MARKET_PANEL_ID = 'market-panel'
const pct1 = (v?: number | null) => (v == null ? '—' : `${(v * 100).toFixed(1)}%`)

function PlayRow({ p }: { p: PlayOut }) {
  return (
    <li className={`flex gap-3 border-b border-terminal-border/60 py-2.5 last:border-0 ${p.scoring ? 'bg-signal-green/5' : ''}`}>
      <div className="w-14 shrink-0 text-right">
        <div className="font-mono text-xs font-semibold text-zinc-300">{p.period ? `Q${p.period}` : ''}</div>
        <div className="font-mono text-xs text-zinc-500">{p.clock}</div>
      </div>
      <p className={`min-w-0 flex-1 text-sm leading-snug ${p.scoring ? 'font-semibold text-signal-green' : 'text-zinc-200'}`}>
        {p.text}
      </p>
      {(p.home_score != null || p.away_score != null) && (
        <span className="w-12 shrink-0 text-right font-mono text-xs font-bold tabular-nums text-zinc-400">
          {p.away_score}-{p.home_score}
        </span>
      )}
    </li>
  )
}

/** Field position — only meaningful while a game is actually being played. */
function FieldPosition({ game }: { game: LiveGameOut }) {
  const possHome = !!game.possession_abbr && game.possession_abbr === game.home_abbr
  const possAway = !!game.possession_abbr && game.possession_abbr === game.away_abbr
  return (
    <div className="relative overflow-hidden rounded-lg border border-terminal-border">
      <div className="flex h-24 w-full" aria-hidden="true">
        <div className={`w-1/2 ${possAway ? 'bg-signal-green/20' : 'bg-terminal-muted'}`} />
        <div className={`w-1/2 ${possHome ? 'bg-signal-green/20' : 'bg-terminal-muted'}`} />
      </div>
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 px-3 text-center">
        <span className="font-display text-lg font-black text-zinc-100">
          {game.down_distance || `Q${game.period ?? ''} ${game.clock ?? ''}`}
        </span>
        <span className="text-xs font-semibold text-signal-green">
          {game.possession_abbr ? `${game.possession_abbr} has the ball` : 'In progress'}
        </span>
      </div>
    </div>
  )
}

export function GameDetail() {
  const { league = 'nfl', eventId } = useParams<{ league: string; eventId: string }>()
  const [params, setParams] = useSearchParams()
  const location = useLocation()
  const seedState = location.state as { game?: LiveGameOut } | null
  const { data, pbp, loading, refreshing, error } = useGameDetail(league, eventId)
  const { community, refreshCommunity } = useGameCommunity(league, eventId)

  // Render the matchup immediately when we arrived from a board that already
  // had it, so the header never waits on a round trip.
  const seed = seedState?.game
  const game = data?.game ?? seed ?? null
  const status = data?.status ?? seed?.state ?? 'pre'
  const live = status === 'in'

  const markets = useMemo(() => data?.markets ?? [], [data])
  const requested = params.get('market') as MarketKey | null
  const [active, setActive] = useState<MarketKey>(requested ?? 'spread')

  // Keep the selected market valid for whatever the book actually posts.
  useEffect(() => {
    if (!markets.length) return
    if (!markets.some(m => m.key === active)) setActive(markets[0].key)
  }, [markets, active])

  const selectMarket = (key: MarketKey) => {
    setActive(key)
    const next = new URLSearchParams(params)
    next.set('market', key)
    setParams(next, { replace: true })
  }

  // "Why this edge?" deep-links to the market *and* its explanation.
  const whyRef = useRef<HTMLDivElement>(null)
  const explain = (key: string) => {
    selectMarket(key as MarketKey)
    whyRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  useEffect(() => {
    if (location.hash === '#why' && data) {
      whyRef.current?.scrollIntoView({ block: 'start' })
    }
  }, [data, location.hash])

  // Sample live win probability while the page is open (no server history yet).
  const [wpPoints, setWpPoints] = useState<Point[]>([])
  const homeWin = data?.model?.live_home_win ?? data?.model?.calibrated_home_win ?? data?.model?.home_win_prob
  useEffect(() => {
    if (!live || homeWin == null) return
    setWpPoints(prev => {
      const last = prev[prev.length - 1]
      if (last && Math.abs(last.v - homeWin) < 1e-6) return prev
      return [...prev, { t: Date.now(), v: homeWin }].slice(-120)
    })
  }, [live, homeWin])

  const activeMarket = markets.find(m => m.key === active) ?? markets[0]
  const snap = data?.snapshot

  // Real observed line movement: the snapshotted line vs the current one.
  const linePoints = useMemo<Point[]>(() => {
    if (!data) return []
    const cur = activeMarket?.key === 'total' ? data.game.market_over_under : data.game.market_spread
    const snapped = activeMarket?.key === 'total' ? snap?.market_total : snap?.market_spread
    const pts: Point[] = []
    if (snapped != null) pts.push({ t: 0, v: snapped })
    if (cur != null) pts.push({ t: 1, v: cur })
    return pts
  }, [data, activeMarket, snap])

  if (!game) {
    return (
      <div className="mx-auto w-full max-w-[1200px] px-4 py-6">
        <Link to="/" className="text-sm font-semibold text-zinc-300 hover:text-zinc-100">← Scores</Link>
        {loading
          ? <div className="mt-4 space-y-3"><div className="skeleton h-28 rounded-xl" /><div className="skeleton h-40 rounded-xl" /></div>
          : <p role="alert" className="mt-4 text-sm text-signal-red">{error || 'Game not found on the current board.'}</p>}
      </div>
    )
  }

  return (
    <div className="mx-auto w-full max-w-[1200px] px-4 py-6">
      <Link to="/" className="text-sm font-semibold text-zinc-300 hover:text-zinc-100">← Scores</Link>

      <div className="mt-3 space-y-4">
        <GameHeader game={game} leagueLabel={LEAGUE_LABEL[league] ?? league.toUpperCase()} />

        {error && data && (
          <p role="status" className="rounded-lg border border-signal-amber/40 bg-signal-amber/10 px-3 py-2 text-sm text-signal-amber">
            Live feed hiccup — showing the last good data. {error}
          </p>
        )}
        {error && !data && (
          <p role="alert" className="rounded-lg border border-signal-red/40 bg-terminal-surface px-3 py-2 text-sm text-signal-red">
            Couldn’t load the model for this game. {error}
          </p>
        )}

        {/* Desktop: insight and context side by side; mobile: stacked. */}
        <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
          <div className="min-w-0 space-y-4">
            {data?.mapped === false ? (
              <Panel title="Best available edge" state="empty"
                     emptyMessage="This matchup isn’t mapped to the model yet, so no edge is claimed for it." />
            ) : (
              <PrimaryEdgeCard
                edge={data?.best_edge}
                gradeScale={data?.grade_scale ?? []}
                fetchedAt={data?.fetched_at}
                sourceOk={data?.source_ok ?? true}
                onExplain={explain}
              />
            )}

            <Panel
              title="Markets"
              subtitle="Model, sportsbook (vig removed) and prediction-market crowd on the same market."
              state={loading && !data ? 'loading' : markets.length ? 'ready' : 'empty'}
              emptyMessage="No lines are posted for this game yet, so there is nothing to compare."
              refreshing={refreshing}
              fetchedAt={data?.fetched_at}
              source={data?.source}
              sourceOk={data?.source_ok}
              actions={markets.length > 0 && (
                <MarketSelector markets={markets} active={active} onChange={selectMarket} panelId={MARKET_PANEL_ID} />
              )}
            >
              {activeMarket && (
                <div id={MARKET_PANEL_ID} role="tabpanel" aria-labelledby={`market-tab-${activeMarket.key}`} tabIndex={0}
                     className="space-y-6 focus:outline-none">
                  <ProbabilityComparison market={activeMarket} />
                  <SportsbookOddsTable market={activeMarket} />
                </div>
              )}
            </Panel>

            <div ref={whyRef} />
            <Panel
              id="why"
              title="Why this edge?"
              subtitle={activeMarket ? `Explaining the ${activeMarket.label.toLowerCase()} market.` : undefined}
              state={activeMarket ? 'ready' : 'empty'}
              emptyMessage="Nothing to explain until a line is posted."
            >
              {activeMarket && (
                <ModelExplanation
                  market={activeMarket}
                  model={data?.model}
                  gradeScale={data?.grade_scale ?? []}
                  modelVersion={data?.model_version ?? '—'}
                />
              )}
            </Panel>

            {game && (
              <MakeYourPick
                league={league}
                game={game}
                existing={community?.your_picks}
                onSubmitted={refreshCommunity}
              />
            )}

            <GameCommunity
              data={community}
              homeAbbr={game?.home_abbr ?? 'HOME'}
              awayAbbr={game?.away_abbr ?? 'AWAY'}
            />
          </div>

          <div className="min-w-0 space-y-4">
            {live && (
              <Panel title="Live win probability" refreshing={refreshing}
                     fetchedAt={data?.fetched_at} source={data?.source} sourceOk={data?.source_ok}
                     staleAfterSeconds={45}>
                <div className="space-y-4">
                  <div className="flex items-baseline justify-between">
                    <span className="text-sm text-zinc-300">{game.home_abbr} (home)</span>
                    <span className="font-mono text-2xl font-black tabular-nums text-signal-green">{pct1(homeWin)}</span>
                  </div>
                  <LiveWinProbabilityChart points={wpPoints} teamLabel={game.home_abbr} />
                  <FieldPosition game={game} />
                </div>
              </Panel>
            )}

            {status === 'pre' && (
              <Panel title="Projected score"
                     subtitle="Model projection before kickoff — not a live score."
                     state={data?.model ? 'ready' : loading ? 'loading' : 'empty'}
                     emptyMessage="No projection until this matchup is mapped to the model."
                     fetchedAt={data?.fetched_at} source={data?.source} sourceOk={data?.source_ok}>
                {data?.model && (
                  <div className="space-y-3">
                    <p className="font-mono text-3xl font-black tabular-nums text-zinc-100">
                      {data.model.proj_away_score ?? '—'} – {data.model.proj_home_score ?? '—'}
                    </p>
                    <p className="text-xs text-zinc-400">{game.away_abbr} at {game.home_abbr}</p>
                    <dl className="grid grid-cols-2 gap-3 border-t border-terminal-border/70 pt-3 text-sm">
                      <div>
                        <dt className="text-xs text-zinc-400">Win probability ({game.home_abbr})</dt>
                        <dd className="font-mono font-bold tabular-nums text-zinc-100">
                          {pct1(data.model.calibrated_home_win ?? data.model.home_win_prob)}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs text-zinc-400">Projected total</dt>
                        <dd className="font-mono font-bold tabular-nums text-zinc-100">
                          {data.model.total_estimate?.toFixed(1) ?? '—'}
                        </dd>
                      </div>
                    </dl>
                  </div>
                )}
              </Panel>
            )}

            {status === 'post' && (
              <Panel title="Result vs the pre-game call"
                     subtitle="The frozen prediction, judged against the closing line."
                     state={snap ? 'ready' : 'empty'}
                     emptyMessage="No pre-game snapshot was stored for this game, so there is nothing to grade.">
                {snap && (
                  <dl className="space-y-2 text-sm">
                    <div className="flex justify-between gap-3">
                      <dt className="text-zinc-400">Final</dt>
                      <dd className="font-mono font-bold text-zinc-100">{game.away_score}–{game.home_score}</dd>
                    </div>
                    <div className="flex justify-between gap-3">
                      <dt className="text-zinc-400">Model said ({game.home_abbr} win)</dt>
                      <dd className="font-mono font-bold text-zinc-100">{pct1(snap.model_home_prob)}</dd>
                    </div>
                    <div className="flex justify-between gap-3">
                      <dt className="text-zinc-400">Closing spread</dt>
                      <dd className="font-mono font-bold text-zinc-100">{snap.closing_spread ?? '—'}</dd>
                    </div>
                    <div className="flex justify-between gap-3">
                      <dt className="text-zinc-400">Result</dt>
                      <dd className={`font-bold ${
                        snap.graded
                          ? ((snap.model_home_prob ?? 0.5) >= 0.5) === (snap.home_won === 1)
                            ? 'text-signal-green' : 'text-signal-red'
                          : 'text-zinc-400'
                      }`}>
                        {snap.graded
                          ? ((snap.model_home_prob ?? 0.5) >= 0.5) === (snap.home_won === 1) ? 'Model correct' : 'Model wrong'
                          : 'Awaiting grading'}
                      </dd>
                    </div>
                    <p className="border-t border-terminal-border/70 pt-2 text-xs text-zinc-500">
                      Snapshotted {snap.snapshot_at ?? 'pre-kickoff'} by model{' '}
                      <span className="font-mono">{snap.model_version ?? 'unknown'}</span>.
                    </p>
                  </dl>
                )}
              </Panel>
            )}

            <LockedPremiumPanel
              title="Line movement"
              description="Track how this line has moved since it opened, and where the sharp money went."
              requires="line_movement_history"
            >
              <Panel title="Line movement"
                     subtitle={activeMarket ? `${activeMarket.label} line since our first snapshot.` : undefined}>
                <LineMovementChart
                  points={linePoints}
                  label={activeMarket?.label ?? 'Line'}
                  emptyMessage="Only the current line is known — line history isn’t recorded server-side yet."
                />
              </Panel>
            </LockedPremiumPanel>

            <Panel
              title="Play-by-play"
              subtitle={live ? 'Updates automatically every 10 seconds.' : undefined}
              state={status === 'pre' ? 'empty' : (pbp?.plays.length ? 'ready' : loading ? 'loading' : 'empty')}
              emptyMessage={status === 'pre'
                ? 'Play-by-play begins at kickoff.'
                : 'No plays have been published for this game yet.'}
              refreshing={refreshing}
              fetchedAt={pbp?.fetched_at}
              source="ESPN"
              sourceOk={pbp?.ok ?? true}
              staleAfterSeconds={45}
            >
              <ul className="max-h-[28rem] overflow-y-auto">
                {(pbp?.plays ?? []).map((p, i) => <PlayRow key={i} p={p} />)}
              </ul>
            </Panel>
          </div>
        </div>
      </div>
    </div>
  )
}
