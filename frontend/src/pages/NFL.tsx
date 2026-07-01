import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { TeamInfo, NFLPredictResponse } from '../types'
import { TeamSelect } from '../components/TeamSelect'
import { EdgeReadout } from '../components/EdgeReadout'
import { WhyPanel } from '../components/WhyPanel'

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-terminal-border bg-terminal-surface p-3 text-center">
      <p className="text-[10px] font-display uppercase tracking-widest text-zinc-500">{label}</p>
      <p className="font-mono text-xl text-signal-amber mt-1">{value}</p>
    </div>
  )
}

export function NFL() {
  const [teams, setTeams] = useState<TeamInfo[]>([])
  const [home, setHome] = useState('')
  const [away, setAway] = useState('')
  const [neutral, setNeutral] = useState(false)
  const [result, setResult] = useState<NFLPredictResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.nflTeams().then(setTeams).catch(() => {})
  }, [])

  async function handlePredict() {
    if (!home || !away) return
    if (home === away) { setError('Pick two different teams.'); return }
    setError(null)
    setLoading(true)
    try {
      const data = await api.predictNFL(home, away, neutral)
      setResult(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  const spread = result
    ? result.predicted_spread >= 0
      ? `${result.home_team.name} -${Math.abs(result.predicted_spread).toFixed(1)}`
      : `${result.away_team.name} -${Math.abs(result.predicted_spread).toFixed(1)}`
    : '—'

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-100">
          NFL Predictor — <span className="text-signal-amber">2025 Season</span>
        </h1>
        <p className="text-sm text-zinc-500 mt-1 font-body">
          Elo-based win probability, point spread, and ATS cover probability.
        </p>
      </div>

      {/* Setup */}
      <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <TeamSelect teams={teams} value={home} onChange={setHome} label="Home Team" />
          <TeamSelect teams={teams} value={away} onChange={setAway} label="Away Team" />
        </div>

        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={neutral}
            onChange={e => setNeutral(e.target.checked)}
            className="rounded border-terminal-border bg-terminal-muted accent-signal-amber"
          />
          <span className="text-sm text-zinc-400 font-body">Neutral site (Super Bowl, London, etc.)</span>
        </label>

        <button
          onClick={handlePredict}
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
          {/* Match header */}
          <div className="flex items-center justify-center gap-6 py-4">
            <div className="text-center">
              <div className="text-4xl">🏈</div>
              <div className="font-display font-semibold text-zinc-100 mt-1">{result.home_team.name}</div>
              <div className="font-mono text-xs text-zinc-500">Elo {result.home_team.elo}</div>
            </div>
            <div className="font-display text-2xl text-zinc-600 font-bold">@</div>
            <div className="text-center">
              <div className="text-4xl">🏈</div>
              <div className="font-display font-semibold text-zinc-100 mt-1">{result.away_team.name}</div>
              <div className="font-mono text-xs text-zinc-500">Elo {result.away_team.elo}</div>
            </div>
          </div>

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
          </div>

          {/* Key stats */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Spread" value={spread} />
            <Stat label="Total O/U" value={result.total_points_estimate.toFixed(1)} />
            <Stat label={`${result.home_team.name} ATS`} value={`${Math.round(result.home_cover_prob * 100)}%`} />
            <Stat label={`${result.away_team.name} ATS`} value={`${Math.round(result.away_cover_prob * 100)}%`} />
          </div>

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
