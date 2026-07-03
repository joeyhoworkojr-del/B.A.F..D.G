import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { TeamInfo, NFLPredictResponse, NFLMarketOdds } from '../types'
import { TeamSelect } from '../components/TeamSelect'
import { EdgeReadout } from '../components/EdgeReadout'
import { WhyPanel } from '../components/WhyPanel'
import { ConditionsPanel } from '../components/ConditionsPanel'
import { LineupManager } from '../components/LineupManager'
import { EdgesTable } from '../components/EdgesTable'
import { LineExplorer } from '../components/LineExplorer'

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="rounded-lg border border-terminal-border bg-terminal-surface p-3 text-center">
      <p className="text-[10px] font-display uppercase tracking-widest text-zinc-500">{label}</p>
      <p className={`font-mono text-xl mt-1 ${accent ? 'text-signal-green' : 'text-signal-amber'}`}>{value}</p>
    </div>
  )
}

function NumInput({ label, value, onChange, placeholder, step = '0.5' }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; step?: string
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] font-display uppercase tracking-widest text-zinc-500">{label}</span>
      <input
        type="number"
        step={step}
        placeholder={placeholder}
        value={value}
        onChange={e => onChange(e.target.value)}
        className="rounded-lg border border-terminal-border bg-terminal-muted px-2 py-1.5 font-mono text-sm text-zinc-200 focus:border-signal-amber focus:outline-none w-full"
      />
    </label>
  )
}

export function NFL() {
  const [teams, setTeams] = useState<TeamInfo[]>([])
  const [home, setHome] = useState('')
  const [away, setAway] = useState('')
  const [neutral, setNeutral] = useState(false)
  const [applyWeather, setApplyWeather] = useState(true)
  const [result, setResult] = useState<NFLPredictResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Market inputs
  const [spreadLine, setSpreadLine] = useState('')
  const [totalLine, setTotalLine] = useState('')
  const [mlHome, setMlHome] = useState('')
  const [mlAway, setMlAway] = useState('')
  const [overPrice, setOverPrice] = useState('')
  const [underPrice, setUnderPrice] = useState('')

  useEffect(() => {
    api.nflTeams().then(setTeams).catch(() => {})
  }, [])

  const runPrediction = useCallback(async () => {
    if (!home || !away) return
    if (home === away) { setError('Pick two different teams.'); return }
    setError(null)
    setLoading(true)
    const num = (s: string) => (s.trim() === '' ? null : Number(s))
    const odds: NFLMarketOdds = {
      format: 'american',
      moneyline_home: num(mlHome),
      moneyline_away: num(mlAway),
      over_price: num(overPrice),
      under_price: num(underPrice),
    }
    const hasOdds = [odds.moneyline_home, odds.moneyline_away, odds.over_price, odds.under_price].some(v => v != null)
    try {
      const data = await api.predictNFL(home, away, {
        neutralSite: neutral,
        applyWeather,
        spreadLine: num(spreadLine),
        totalLine: num(totalLine),
        odds: hasOdds ? odds : null,
      })
      setResult(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }, [home, away, neutral, applyWeather, spreadLine, totalLine, mlHome, mlAway, overPrice, underPrice])

  const onLineupChanged = useCallback(() => {
    if (result) runPrediction()
  }, [result, runPrediction])

  const spread = result
    ? result.predicted_spread >= 0
      ? `${result.home_team.code} -${Math.abs(result.predicted_spread).toFixed(1)}`
      : `${result.away_team.code} -${Math.abs(result.predicted_spread).toFixed(1)}`
    : '—'

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-100">
          NFL Predictor — <span className="text-signal-amber">2025 Season</span>
        </h1>
        <p className="text-sm text-zinc-500 mt-1 font-body">
          Expected-points model: win probability, spread cover and over/under at any line,
          adjusted live for stadium weather and inactives.
        </p>
      </div>

      {/* Setup */}
      <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <TeamSelect teams={teams} value={home} onChange={setHome} label="Home Team" />
          <TeamSelect teams={teams} value={away} onChange={setAway} label="Away Team" />
        </div>

        <div className="flex flex-wrap gap-4">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={neutral}
              onChange={e => setNeutral(e.target.checked)}
              className="rounded border-terminal-border bg-terminal-muted accent-signal-amber"
            />
            <span className="text-sm text-zinc-400 font-body">Neutral site (Super Bowl, London, etc.)</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={applyWeather}
              onChange={e => setApplyWeather(e.target.checked)}
              className="rounded border-terminal-border bg-terminal-muted accent-signal-amber"
            />
            <span className="text-sm text-zinc-400 font-body">🌦 Live stadium weather</span>
          </label>
        </div>

        {/* Vegas lines + prices (all optional) */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <NumInput label="Spread (home)" value={spreadLine} onChange={setSpreadLine} placeholder="-3.5" />
          <NumInput label="Total line" value={totalLine} onChange={setTotalLine} placeholder="44.5" />
          <div className="hidden sm:block" />
          <NumInput label="ML home (Amer.)" value={mlHome} onChange={setMlHome} placeholder="-160" step="5" />
          <NumInput label="ML away (Amer.)" value={mlAway} onChange={setMlAway} placeholder="+140" step="5" />
          <div className="grid grid-cols-2 gap-2">
            <NumInput label="Over $" value={overPrice} onChange={setOverPrice} placeholder="-110" step="5" />
            <NumInput label="Under $" value={underPrice} onChange={setUnderPrice} placeholder="-110" step="5" />
          </div>
        </div>

        <LineupManager
          sport="nfl"
          homeTeam={home}
          awayTeam={away}
          homeLabel={teams.find(t => t.code === home)?.name}
          awayLabel={teams.find(t => t.code === away)?.name}
          onChanged={onLineupChanged}
        />

        <button
          onClick={runPrediction}
          disabled={!home || !away || loading}
          className="w-full rounded-lg bg-signal-amber px-4 py-2.5 font-display font-semibold text-terminal-bg disabled:opacity-40 disabled:cursor-not-allowed hover:bg-amber-400 transition-colors"
        >
          {loading ? 'Analysing…' : 'Run Prediction'}
        </button>
        {error && <p className="text-sm text-signal-red font-body">{error}</p>}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Match header with expected score */}
          <div className="flex items-center justify-center gap-6 py-4">
            <div className="text-center">
              <div className="text-4xl">🏈</div>
              <div className="font-display font-semibold text-zinc-100 mt-1">{result.home_team.name}</div>
              <div className="font-mono text-2xl text-signal-amber">{result.home_expected_pts.toFixed(1)}</div>
              <div className="font-mono text-xs text-zinc-500">Elo {result.home_team.elo}</div>
            </div>
            <div className="font-display text-2xl text-zinc-600 font-bold">@</div>
            <div className="text-center">
              <div className="text-4xl">🏈</div>
              <div className="font-display font-semibold text-zinc-100 mt-1">{result.away_team.name}</div>
              <div className="font-mono text-2xl text-signal-amber">{result.away_expected_pts.toFixed(1)}</div>
              <div className="font-mono text-xs text-zinc-500">Elo {result.away_team.elo}</div>
            </div>
          </div>

          {/* Live conditions actively shaping this prediction */}
          <ConditionsPanel
            conditions={result.conditions}
            weather={result.weather}
            baseProb={result.base_home_win_prob}
            currentProb={result.home_win_prob}
            baseLabel={`${result.home_team.name} win`}
          />

          {/* Win probs */}
          <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <EdgeReadout
                probability={result.home_win_prob}
                label={`${result.home_team.name} Win`}
                color="blue"
                size="lg"
              />
              <EdgeReadout
                probability={result.away_win_prob}
                label={`${result.away_team.name} Win`}
                color="red"
                size="lg"
              />
            </div>
            <p className="font-mono text-[11px] text-zinc-600 text-center">
              Fair ML: {result.home_team.code} {result.fair_odds.home_ml?.toFixed(2)} · {result.away_team.code} {result.fair_odds.away_ml?.toFixed(2)}
            </p>
          </div>

          {/* Key stats */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Model spread" value={spread} />
            <Stat
              label={`Over ${result.total_line?.toFixed(1) ?? ''}`}
              value={`${Math.round(result.over_prob * 100)}%`}
              accent={result.over_prob >= 0.55}
            />
            <Stat
              label={`Under ${result.total_line?.toFixed(1) ?? ''}`}
              value={`${Math.round(result.under_prob * 100)}%`}
              accent={result.under_prob >= 0.55}
            />
            <Stat
              label={`${result.home_team.code} cover ${spreadLine || 'model line'}`}
              value={`${Math.round(result.home_cover_prob * 100)}%`}
              accent={result.home_cover_prob >= 0.55 || result.home_cover_prob <= 0.45}
            />
          </div>

          {/* Totals explorer */}
          <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4 space-y-4">
            <LineExplorer
              overByLine={result.over_by_line}
              unit="points"
              title="Game total — over/under any line"
              initialLine={result.total_line ?? undefined}
            />
            <div className="grid grid-cols-2 gap-4 border-t border-terminal-border pt-4">
              <LineExplorer
                overByLine={result.home_team_total_over}
                unit="points"
                title={`${result.home_team.code} team total`}
              />
              <LineExplorer
                overByLine={result.away_team_total_over}
                unit="points"
                title={`${result.away_team.code} team total`}
              />
            </div>
          </div>

          {/* Market edges */}
          {result.edges.length > 0 && (
            <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4 space-y-3">
              <h3 className="text-xs font-display uppercase tracking-widest text-zinc-500">
                Value vs your quoted odds
              </h3>
              <EdgesTable edges={result.edges} />
            </div>
          )}

          {/* Why */}
          <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4 space-y-3">
            <h3 className="text-xs font-display uppercase tracking-widest text-zinc-500">Why</h3>
            <WhyPanel factors={result.why_factors} />
          </div>

          <p className="text-[10px] text-zinc-600 italic">{result.data_warning}</p>
        </div>
      )}
    </div>
  )
}
