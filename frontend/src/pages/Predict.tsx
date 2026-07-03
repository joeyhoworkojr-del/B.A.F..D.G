import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { TeamInfo, SoccerPredictResponse, SoccerMarketOdds } from '../types'
import { TeamSelect } from '../components/TeamSelect'
import { WDLBar } from '../components/WDLBar'
import { EdgeReadout } from '../components/EdgeReadout'
import { TotalsCard } from '../components/TotalsCard'
import { PlayerPropsTable } from '../components/PlayerPropsTable'
import { ScoreHeatmap } from '../components/ScoreHeatmap'
import { WhyPanel } from '../components/WhyPanel'
import { MonteCarloChart } from '../components/MonteCarloChart'
import { ConditionsPanel } from '../components/ConditionsPanel'
import { LineupManager } from '../components/LineupManager'
import { EdgesTable } from '../components/EdgesTable'
import { LineExplorer } from '../components/LineExplorer'

type Tab = 'overview' | 'totals' | 'edge' | 'props' | 'heatmap' | 'simulation' | 'why'

const TABS: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'totals', label: 'Totals' },
  { id: 'edge', label: 'Edge Finder' },
  { id: 'props', label: 'Player Props' },
  { id: 'heatmap', label: 'Scoreline' },
  { id: 'simulation', label: 'Simulation' },
  { id: 'why', label: 'Why?' },
]

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4 space-y-4">
      {title && <h3 className="text-xs font-display uppercase tracking-widest text-zinc-500">{title}</h3>}
      {children}
    </div>
  )
}

function OddsInput({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] font-display uppercase tracking-widest text-zinc-500">{label}</span>
      <input
        type="number"
        step="0.01"
        min="1.01"
        placeholder="1.95"
        value={value}
        onChange={e => onChange(e.target.value)}
        className="rounded-lg border border-terminal-border bg-terminal-muted px-2 py-1.5 font-mono text-sm text-zinc-200 focus:border-signal-amber focus:outline-none w-full"
      />
    </label>
  )
}

export function Predict() {
  const [teams, setTeams] = useState<TeamInfo[]>([])
  const [home, setHome] = useState('')
  const [away, setAway] = useState('')
  const [knockout, setKnockout] = useState(false)
  const [neutral, setNeutral] = useState(true)
  const [applyWeather, setApplyWeather] = useState(true)
  const [result, setResult] = useState<SoccerPredictResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('overview')

  // Market odds (decimal) for the edge finder
  const [oddsHome, setOddsHome] = useState('')
  const [oddsDraw, setOddsDraw] = useState('')
  const [oddsAway, setOddsAway] = useState('')
  const [oddsOver, setOddsOver] = useState('')
  const [oddsUnder, setOddsUnder] = useState('')

  useEffect(() => {
    api.soccerTeams().then(setTeams).catch(() => {})
  }, [])

  const buildOdds = useCallback((): SoccerMarketOdds | null => {
    const num = (s: string) => (s.trim() === '' ? null : Number(s))
    const odds: SoccerMarketOdds = {
      format: 'decimal',
      home: num(oddsHome),
      draw: num(oddsDraw),
      away: num(oddsAway),
      over_2_5: num(oddsOver),
      under_2_5: num(oddsUnder),
    }
    const any = [odds.home, odds.draw, odds.away, odds.over_2_5, odds.under_2_5].some(v => v != null)
    return any ? odds : null
  }, [oddsHome, oddsDraw, oddsAway, oddsOver, oddsUnder])

  const runPrediction = useCallback(async (keepTab = false) => {
    if (!home || !away) return
    if (home === away) { setError('Pick two different teams.'); return }
    setError(null)
    setLoading(true)
    try {
      const data = await api.predictSoccer(home, away, {
        knockout,
        neutral,
        applyWeather,
        odds: buildOdds(),
      })
      setResult(data)
      if (!keepTab) setActiveTab('overview')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }, [home, away, knockout, neutral, applyWeather, buildOdds])

  // Re-run silently when team news changes so the numbers stay live
  const onLineupChanged = useCallback(() => {
    if (result) runPrediction(true)
  }, [result, runPrediction])

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-100">
          Match Predictor — <span className="text-signal-amber">World Cup 2026</span>
        </h1>
        <p className="text-sm text-zinc-500 mt-1 font-body">
          Dixon-Coles Elo model with team styles, live weather and team news. 50k Monte Carlo simulations.
        </p>
      </div>

      {/* Setup card */}
      <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <TeamSelect teams={teams} value={home} onChange={setHome} label="Home / Team A" />
          <TeamSelect teams={teams} value={away} onChange={setAway} label="Away / Team B" />
        </div>

        <div className="flex flex-wrap gap-4 items-center">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={knockout}
              onChange={e => setKnockout(e.target.checked)}
              className="rounded border-terminal-border bg-terminal-muted accent-signal-amber"
            />
            <span className="text-sm text-zinc-400 font-body">Knockout (ET + Pens)</span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={neutral}
              onChange={e => setNeutral(e.target.checked)}
              className="rounded border-terminal-border bg-terminal-muted accent-signal-amber"
            />
            <span className="text-sm text-zinc-400 font-body">Neutral venue</span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={applyWeather}
              onChange={e => setApplyWeather(e.target.checked)}
              className="rounded border-terminal-border bg-terminal-muted accent-signal-amber"
            />
            <span className="text-sm text-zinc-400 font-body">🌦 Live weather</span>
          </label>
        </div>

        {/* Live team news — mark players out and the model re-prices */}
        <LineupManager
          sport="soccer"
          homeTeam={home}
          awayTeam={away}
          homeLabel={teams.find(t => t.code === home)?.name}
          awayLabel={teams.find(t => t.code === away)?.name}
          onChanged={onLineupChanged}
        />

        <button
          onClick={() => runPrediction()}
          disabled={!home || !away || loading}
          className="
            w-full rounded-lg bg-signal-amber px-4 py-2.5
            font-display font-semibold text-terminal-bg
            disabled:opacity-40 disabled:cursor-not-allowed
            hover:bg-amber-400 transition-colors
          "
        >
          {loading ? 'Analysing…' : 'Run Prediction'}
        </button>

        {error && <p className="text-sm text-signal-red font-body">{error}</p>}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Match header */}
          <div className="flex items-center justify-center gap-6 py-4">
            <div className="text-center">
              <div className="text-4xl">{result.home_team.flag}</div>
              <div className="font-display font-semibold text-zinc-100 mt-1">{result.home_team.name}</div>
              <div className="font-mono text-xs text-zinc-500">Elo {result.home_team.elo}</div>
            </div>
            <div className="font-display text-2xl text-zinc-600 font-bold">vs</div>
            <div className="text-center">
              <div className="text-4xl">{result.away_team.flag}</div>
              <div className="font-display font-semibold text-zinc-100 mt-1">{result.away_team.name}</div>
              <div className="font-mono text-xs text-zinc-500">Elo {result.away_team.elo}</div>
            </div>
          </div>

          {/* Live conditions actively shaping this prediction */}
          <ConditionsPanel
            conditions={result.conditions}
            weather={result.weather}
            baseProb={result.base_probs?.home_win}
            currentProb={result.model_probs.home_win}
            baseLabel={`${result.home_team.name} win`}
          />

          {/* Tabs */}
          <div className="flex gap-1 border-b border-terminal-border overflow-x-auto">
            {TABS.map(t => (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`
                  px-3 py-2 text-xs font-display uppercase tracking-widest whitespace-nowrap
                  transition-colors border-b-2 -mb-px
                  ${activeTab === t.id
                    ? 'border-signal-amber text-signal-amber'
                    : 'border-transparent text-zinc-500 hover:text-zinc-300'}
                `}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          {activeTab === 'overview' && (
            <Card title="">
              {result.has_sr_data && (
                <div className="text-xs text-zinc-500 font-body">
                  Blended: 40% model + 60% SportRadar
                </div>
              )}
              <WDLBar
                homeWin={result.blended_probs.home_win}
                draw={result.blended_probs.draw}
                awayWin={result.blended_probs.away_win}
                homeLabel={result.home_team.name}
                awayLabel={result.away_team.name}
              />

              <div className="grid grid-cols-3 gap-4 mt-2">
                <EdgeReadout
                  probability={result.blended_probs.home_win}
                  label={`${result.home_team.flag} Win`}
                  color="blue"
                />
                <EdgeReadout
                  probability={result.blended_probs.draw}
                  label="Draw"
                  color="amber"
                />
                <EdgeReadout
                  probability={result.blended_probs.away_win}
                  label={`${result.away_team.flag} Win`}
                  color="red"
                />
              </div>

              <div className="grid grid-cols-3 gap-3 border-t border-terminal-border pt-3">
                <div className="font-mono text-center">
                  <div className="text-xs text-zinc-500">xG {result.home_team.flag}</div>
                  <div className="text-xl text-signal-amber">{result.blended_probs.home_xg.toFixed(2)}</div>
                </div>
                <div className="font-mono text-center">
                  <div className="text-xs text-zinc-500">Fair odds 1X2</div>
                  <div className="text-sm text-zinc-300 mt-1.5">
                    {result.fair_odds.home?.toFixed(2)} / {result.fair_odds.draw?.toFixed(2)} / {result.fair_odds.away?.toFixed(2)}
                  </div>
                </div>
                <div className="font-mono text-center">
                  <div className="text-xs text-zinc-500">xG {result.away_team.flag}</div>
                  <div className="text-xl text-signal-amber">{result.blended_probs.away_xg.toFixed(2)}</div>
                </div>
              </div>

              {result.totals.under_2_5 >= 0.62 && (
                <div className="rounded-lg border border-signal-amber/30 bg-signal-amber/5 px-3 py-2">
                  <p className="text-sm font-display font-medium text-signal-amber">
                    Model signal: <strong>Under 2.5</strong> at {Math.round(result.totals.under_2_5 * 100)}%
                    {' '}(fair {result.fair_odds.under_2_5?.toFixed(2)})
                  </p>
                </div>
              )}
              {result.totals.over_2_5 >= 0.62 && (
                <div className="rounded-lg border border-signal-green/30 bg-signal-green/5 px-3 py-2">
                  <p className="text-sm font-display font-medium text-signal-green">
                    Model signal: <strong>Over 2.5</strong> at {Math.round(result.totals.over_2_5 * 100)}%
                    {' '}(fair {result.fair_odds.over_2_5?.toFixed(2)})
                  </p>
                </div>
              )}

              <p className="text-[10px] text-zinc-600 italic">{result.data_warning}</p>
            </Card>
          )}

          {activeTab === 'totals' && (
            <>
              <Card title="">
                <LineExplorer
                  overByLine={result.totals.over_by_line}
                  unit="goals"
                  initialLine={2.5}
                />
              </Card>
              <Card title="">
                <TotalsCard
                  totals={result.totals}
                  homeLabel={result.home_team.name}
                  awayLabel={result.away_team.name}
                />
              </Card>
            </>
          )}

          {activeTab === 'edge' && (
            <Card title="Edge Finder — your book's odds vs the model">
              <p className="text-xs text-zinc-500 font-body">
                Enter the decimal odds your sportsbook is quoting. The model strips the vig, compares
                fair probabilities, and sizes a quarter-Kelly stake when it finds value.
              </p>
              <div className="grid grid-cols-3 gap-3">
                <OddsInput label={`${result.home_team.name} win`} value={oddsHome} onChange={setOddsHome} />
                <OddsInput label="Draw" value={oddsDraw} onChange={setOddsDraw} />
                <OddsInput label={`${result.away_team.name} win`} value={oddsAway} onChange={setOddsAway} />
                <OddsInput label="Over 2.5" value={oddsOver} onChange={setOddsOver} />
                <OddsInput label="Under 2.5" value={oddsUnder} onChange={setOddsUnder} />
                <div className="flex items-end">
                  <button
                    onClick={() => runPrediction(true)}
                    disabled={loading}
                    className="w-full rounded-lg bg-signal-amber px-3 py-1.5 font-display font-semibold text-sm text-terminal-bg disabled:opacity-40 hover:bg-amber-400 transition-colors"
                  >
                    {loading ? '…' : 'Evaluate'}
                  </button>
                </div>
              </div>

              {result.edges.length > 0 ? (
                <EdgesTable edges={result.edges} />
              ) : (
                <div className="rounded-lg border border-terminal-border bg-terminal-muted/20 px-3 py-3">
                  <p className="text-xs text-zinc-400 font-body">
                    No odds entered yet. Model fair odds:{' '}
                    <span className="font-mono text-signal-amber">
                      {result.home_team.code} {result.fair_odds.home?.toFixed(2)} · X {result.fair_odds.draw?.toFixed(2)} · {result.away_team.code} {result.fair_odds.away?.toFixed(2)} · O2.5 {result.fair_odds.over_2_5?.toFixed(2)} · U2.5 {result.fair_odds.under_2_5?.toFixed(2)}
                    </span>
                    {' '}— anything better than these is value.
                  </p>
                </div>
              )}
            </Card>
          )}

          {activeTab === 'props' && (
            <Card title="">
              <PlayerPropsTable
                props={result.player_props}
                homeCode={result.home_team.code}
                awayCode={result.away_team.code}
                homeFlag={result.home_team.flag}
                awayFlag={result.away_team.flag}
              />
            </Card>
          )}

          {activeTab === 'heatmap' && (
            <Card title="">
              <ScoreHeatmap
                grid={result.scoreline_grid}
                homeLabel={result.home_team.name}
                awayLabel={result.away_team.name}
              />
            </Card>
          )}

          {activeTab === 'simulation' && (
            <Card title="">
              <MonteCarloChart
                sim={result.simulation}
                homeLabel={result.home_team.name}
                awayLabel={result.away_team.name}
                knockout={knockout}
              />
            </Card>
          )}

          {activeTab === 'why' && (
            <Card title="">
              <WhyPanel factors={result.why_factors} />
              <p className="text-[10px] text-zinc-600 italic pt-2">
                Values show change in home-win probability relative to two equal teams at a neutral venue.
              </p>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
