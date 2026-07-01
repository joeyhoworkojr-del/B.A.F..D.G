import { useState, useEffect } from 'react'
import type { HistoryEntry } from '../types'

const STORAGE_KEY = 'statedge_history'

function brierScore(predictedHomeWin: number, outcome: 'home' | 'draw' | 'away'): number {
  const actual = outcome === 'home' ? 1 : 0
  return (predictedHomeWin - actual) ** 2
}

function loadHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as HistoryEntry[]) : []
  } catch {
    return []
  }
}

function saveHistory(entries: HistoryEntry[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries))
}

export function History() {
  const [entries, setEntries] = useState<HistoryEntry[]>(loadHistory)
  const [form, setForm] = useState({
    sport: 'soccer',
    homeCode: '',
    awayCode: '',
    homeName: '',
    awayName: '',
    predictedHomeWin: '',
    actualOutcome: 'home' as 'home' | 'draw' | 'away',
    homeGoals: '',
    awayGoals: '',
  })

  useEffect(() => {
    saveHistory(entries)
  }, [entries])

  function addEntry() {
    const pred = parseFloat(form.predictedHomeWin)
    if (!form.homeCode || !form.awayCode || isNaN(pred)) return
    const entry: HistoryEntry = {
      id: crypto.randomUUID(),
      sport: form.sport,
      home_code: form.homeCode.toUpperCase(),
      away_code: form.awayCode.toUpperCase(),
      home_name: form.homeName || form.homeCode,
      away_name: form.awayName || form.awayCode,
      predicted_home_win: pred,
      actual_outcome: form.actualOutcome,
      home_goals_actual: form.homeGoals ? parseInt(form.homeGoals) : undefined,
      away_goals_actual: form.awayGoals ? parseInt(form.awayGoals) : undefined,
      brier_score: brierScore(pred, form.actualOutcome),
      logged_at: new Date().toISOString(),
    }
    setEntries(prev => [entry, ...prev])
    setForm(f => ({ ...f, predictedHomeWin: '', homeGoals: '', awayGoals: '' }))
  }

  function removeEntry(id: string) {
    setEntries(prev => prev.filter(e => e.id !== id))
  }

  // Stats
  const n = entries.length
  const avgBrier = n > 0 ? entries.reduce((s, e) => s + (e.brier_score ?? 0), 0) / n : null
  const hitRate = n > 0
    ? entries.filter(e => {
        const pred = e.predicted_home_win >= 0.5 ? 'home' : 'away'
        return pred === e.actual_outcome
      }).length / n
    : null

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-100">History & Tracking</h1>
        <p className="text-sm text-zinc-500 mt-1 font-body">
          Log actual results and track your Brier score over time.
        </p>
      </div>

      {/* Stats */}
      {n > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4 text-center">
            <p className="text-[10px] font-display uppercase tracking-widest text-zinc-500">Games logged</p>
            <p className="font-mono text-2xl text-signal-amber mt-1">{n}</p>
          </div>
          <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4 text-center">
            <p className="text-[10px] font-display uppercase tracking-widest text-zinc-500">Hit rate</p>
            <p className="font-mono text-2xl text-signal-green mt-1">
              {hitRate != null ? `${Math.round(hitRate * 100)}%` : '—'}
            </p>
          </div>
          <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4 text-center">
            <p className="text-[10px] font-display uppercase tracking-widest text-zinc-500">Avg Brier</p>
            <p className={`font-mono text-2xl mt-1 ${avgBrier != null && avgBrier < 0.25 ? 'text-signal-green' : 'text-signal-red'}`}>
              {avgBrier != null ? avgBrier.toFixed(3) : '—'}
            </p>
          </div>
        </div>
      )}

      {/* Log form */}
      <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4 space-y-4">
        <h3 className="text-xs font-display uppercase tracking-widest text-zinc-500">Log a result</h3>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-[10px] font-display uppercase tracking-widest text-zinc-500">Home team</label>
            <input
              className="mt-1 w-full rounded-lg border border-terminal-border bg-terminal-bg px-3 py-2 text-sm font-body text-zinc-100 focus:border-signal-amber focus:outline-none"
              placeholder="e.g. ARG"
              value={form.homeCode}
              onChange={e => setForm(f => ({ ...f, homeCode: e.target.value }))}
            />
          </div>
          <div>
            <label className="text-[10px] font-display uppercase tracking-widest text-zinc-500">Away team</label>
            <input
              className="mt-1 w-full rounded-lg border border-terminal-border bg-terminal-bg px-3 py-2 text-sm font-body text-zinc-100 focus:border-signal-amber focus:outline-none"
              placeholder="e.g. CPV"
              value={form.awayCode}
              onChange={e => setForm(f => ({ ...f, awayCode: e.target.value }))}
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="text-[10px] font-display uppercase tracking-widest text-zinc-500">My home-win prob.</label>
            <input
              type="number" min={0} max={1} step={0.01}
              className="mt-1 w-full rounded-lg border border-terminal-border bg-terminal-bg px-3 py-2 text-sm font-mono text-zinc-100 focus:border-signal-amber focus:outline-none"
              placeholder="0.00–1.00"
              value={form.predictedHomeWin}
              onChange={e => setForm(f => ({ ...f, predictedHomeWin: e.target.value }))}
            />
          </div>
          <div>
            <label className="text-[10px] font-display uppercase tracking-widest text-zinc-500">Home goals</label>
            <input
              type="number" min={0}
              className="mt-1 w-full rounded-lg border border-terminal-border bg-terminal-bg px-3 py-2 text-sm font-mono text-zinc-100 focus:border-signal-amber focus:outline-none"
              placeholder="e.g. 2"
              value={form.homeGoals}
              onChange={e => setForm(f => ({ ...f, homeGoals: e.target.value }))}
            />
          </div>
          <div>
            <label className="text-[10px] font-display uppercase tracking-widest text-zinc-500">Away goals</label>
            <input
              type="number" min={0}
              className="mt-1 w-full rounded-lg border border-terminal-border bg-terminal-bg px-3 py-2 text-sm font-mono text-zinc-100 focus:border-signal-amber focus:outline-none"
              placeholder="e.g. 0"
              value={form.awayGoals}
              onChange={e => setForm(f => ({ ...f, awayGoals: e.target.value }))}
            />
          </div>
        </div>

        <div>
          <label className="text-[10px] font-display uppercase tracking-widest text-zinc-500">Actual outcome</label>
          <div className="flex gap-3 mt-2">
            {(['home', 'draw', 'away'] as const).map(o => (
              <label key={o} className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="outcome"
                  value={o}
                  checked={form.actualOutcome === o}
                  onChange={() => setForm(f => ({ ...f, actualOutcome: o }))}
                  className="accent-signal-amber"
                />
                <span className="text-sm font-body capitalize text-zinc-300">{o === 'home' ? `${form.homeCode || 'Home'} win` : o === 'away' ? `${form.awayCode || 'Away'} win` : 'Draw'}</span>
              </label>
            ))}
          </div>
        </div>

        <button
          onClick={addEntry}
          className="w-full rounded-lg bg-signal-amber px-4 py-2 font-display font-semibold text-terminal-bg hover:bg-amber-400 transition-colors"
        >
          Log Result
        </button>
      </div>

      {/* Entry list */}
      {entries.length > 0 && (
        <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4 space-y-2">
          <h3 className="text-xs font-display uppercase tracking-widest text-zinc-500 pb-2">Past results</h3>
          {entries.map(e => {
            const correct = (e.predicted_home_win >= 0.5 ? 'home' : 'away') === e.actual_outcome
            return (
              <div key={e.id} className="flex items-center gap-3 py-2 border-b border-terminal-muted/40">
                <span className={`w-2 h-2 rounded-full ${correct ? 'bg-signal-green' : 'bg-signal-red'}`} />
                <span className="flex-1 text-sm font-body text-zinc-300">
                  {e.home_code} vs {e.away_code}
                  {e.home_goals_actual != null && ` — ${e.home_goals_actual}–${e.away_goals_actual}`}
                </span>
                <span className="font-mono text-xs text-zinc-500">
                  pred {(e.predicted_home_win * 100).toFixed(0)}%
                </span>
                <span className={`font-mono text-xs ${e.brier_score != null && e.brier_score < 0.25 ? 'text-signal-green' : 'text-signal-red'}`}>
                  B={e.brier_score?.toFixed(3)}
                </span>
                <button
                  onClick={() => removeEntry(e.id)}
                  className="text-zinc-600 hover:text-signal-red text-xs transition-colors ml-1"
                >
                  ✕
                </button>
              </div>
            )
          })}
        </div>
      )}

      <p className="text-[10px] text-zinc-600 italic">
        History stored locally in your browser. Brier score: 0 = perfect, 1 = worst. A calibrated model scores ~0.20–0.25 on soccer.
      </p>
    </div>
  )
}
