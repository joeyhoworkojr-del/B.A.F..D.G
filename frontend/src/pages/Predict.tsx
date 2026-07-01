import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { TeamInfo, SoccerPredictResponse } from '../types'
import { TeamSelect } from '../components/TeamSelect'
import { WDLBar } from '../components/WDLBar'
import { EdgeReadout } from '../components/EdgeReadout'
import { TotalsCard } from '../components/TotalsCard'
import { PlayerPropsTable } from '../components/PlayerPropsTable'
import { ScoreHeatmap } from '../components/ScoreHeatmap'
import { WhyPanel } from '../components/WhyPanel'
import { MonteCarloChart } from '../components/MonteCarloChart'
import { WeatherWidget } from '../components/WeatherWidget'

// Map fixture IDs to venues for weather
const FIXTURE_VENUES: Record<string, string> = {
  r16_1: "MetLife Stadium, NJ",
  r16_2: "AT&T Stadium, Dallas",
  r16_3: "Estadio Azteca, CDMX",
  r16_4: "Estadio Azteca, CDMX",
  r16_5: "SoFi Stadium, LA",
  r16_6: "Rose Bowl, Pasadena",
  r16_7: "Hard Rock Stadium, Miami",
  r16_8: "BC Place, Vancouver",
  r16_9: "Levi's Stadium, SF",
  r16_10: "AT&T Stadium, Dallas",
  r16_11: "Lincoln Financial Field, Philly",
  r16_12: "Gillette Stadium, Boston",
  r16_13: "Mercedes-Benz Stadium, Atlanta",
  r16_14: "State Farm Stadium, Glendale",
  r16_15: "BMO Field, Toronto",
}

type Tab = 'overview' | 'totals' | 'props' | 'heatmap' | 'simulation' | 'why'

const TABS: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'totals', label: 'Totals' },
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

export function Predict() {
  const [teams, setTeams] = useState<TeamInfo[]>([])
  const [home, setHome] = useState('')
  const [away, setAway] = useState('')
  const [knockout, setKnockout] = useState(false)
  const [neutral, setNeutral] = useState(true)
  const [dampener, setDampener] = useState(1.0)
  const [result, setResult] = useState<SoccerPredictResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('overview')

  // Find venue for weather widget based on live fixture
  const [fixtures, setFixtures] = useState<Array<{id: string; home: {code: string}; away: {code: string}; venue: string}>>([])
  useEffect(() => {
    api.r16Fixtures().then(f => setFixtures(f as typeof fixtures)).catch(() => {})
  }, [])

  const matchedFixture = fixtures.find(
    f => f.home.code === home && f.away.code === away
  )
  const venueForWeather = matchedFixture?.venue
    ? Object.values(FIXTURE_VENUES).find(v => matchedFixture.venue.includes(v.split(',')[0]))
    : undefined

  useEffect(() => {
    api.soccerTeams().then(setTeams).catch(() => {})
  }, [])

  async function handlePredict() {
    if (!home || !away) return
    if (home === away) { setError('Pick two different teams.'); return }
    setError(null)
    setLoading(true)
    try {
      const data = await api.predictSoccer(home, away, {
        knockout,
        neutral,
        defensiveDampener: dampener,
      })
      setResult(data)
      setActiveTab('overview')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-100">
          Match Predictor — <span className="text-signal-amber">World Cup 2026</span>
        </h1>
        <p className="text-sm text-zinc-500 mt-1 font-body">
          Elo-Poisson model, calibrated to SportRadar. 50k Monte Carlo simulations.
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

          <div className="flex items-center gap-2 ml-auto">
            <label className="text-xs text-zinc-500 font-display uppercase tracking-widest">
              Def. dampener
            </label>
            <input
              type="range"
              min={0.6}
              max={1.4}
              step={0.05}
              value={dampener}
              onChange={e => setDampener(Number(e.target.value))}
              className="w-24 accent-signal-amber"
            />
            <span className="font-mono text-xs text-signal-amber w-8">{dampener.toFixed(2)}</span>
          </div>
        </div>

        <button
          onClick={handlePredict}
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
          {/* Live weather for the venue */}
          {venueForWeather && (
            <div className="space-y-1">
              <p className="text-[10px] font-display uppercase tracking-widest text-zinc-600">Live venue weather</p>
              <WeatherWidget venue={venueForWeather} />
            </div>
          )}
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
              {/* Blended headline */}
              {result.has_sr_data && (
                <div className="text-xs text-zinc-500 font-body">
                  Blended: 40% Elo model + 60% SportRadar
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

              <div className="grid grid-cols-2 gap-3 border-t border-terminal-border pt-3">
                <div className="font-mono text-center">
                  <div className="text-xs text-zinc-500">xG {result.home_team.flag}</div>
                  <div className="text-xl text-signal-amber">{result.blended_probs.home_xg.toFixed(2)}</div>
                </div>
                <div className="font-mono text-center">
                  <div className="text-xs text-zinc-500">xG {result.away_team.flag}</div>
                  <div className="text-xl text-signal-amber">{result.blended_probs.away_xg.toFixed(2)}</div>
                </div>
              </div>

              {result.totals.under_2_5 >= 0.65 && (
                <div className="rounded-lg border border-signal-amber/30 bg-signal-amber/5 px-3 py-2">
                  <p className="text-sm font-display font-medium text-signal-amber">
                    Sharp edge: <strong>Under 2.5</strong> at {Math.round(result.totals.under_2_5 * 100)}%
                  </p>
                </div>
              )}
              {result.totals.over_2_5 >= 0.65 && (
                <div className="rounded-lg border border-signal-green/30 bg-signal-green/5 px-3 py-2">
                  <p className="text-sm font-display font-medium text-signal-green">
                    Sharp edge: <strong>Over 2.5</strong> at {Math.round(result.totals.over_2_5 * 100)}%
                  </p>
                </div>
              )}

              <p className="text-[10px] text-zinc-600 italic">{result.data_warning}</p>
            </Card>
          )}

          {activeTab === 'totals' && (
            <Card title="">
              <TotalsCard
                totals={result.totals}
                homeLabel={result.home_team.name}
                awayLabel={result.away_team.name}
              />
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
