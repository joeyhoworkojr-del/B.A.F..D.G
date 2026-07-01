import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { RankingsResponse, RankedTeam } from '../types'

type Sport = 'soccer' | 'nfl'

function TeamRow({ team, sport }: { team: RankedTeam; sport: Sport }) {
  const confBadge = sport === 'nfl' && team.conference
    ? <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-terminal-muted text-zinc-400">{team.conference}</span>
    : team.group
    ? <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-terminal-muted text-zinc-400">Grp {team.group}</span>
    : null

  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-terminal-muted/50 hover:bg-terminal-muted/20 -mx-2 px-2 rounded transition-colors">
      <span className="font-mono text-sm text-zinc-600 w-6 text-right">{team.rank}</span>
      <span className="text-xl">{team.flag}</span>
      <span className="flex-1 font-display text-sm text-zinc-200">{team.name}</span>
      {confBadge}
      <div className="flex items-center gap-2">
        <div className="w-20 h-1.5 rounded-full bg-terminal-muted overflow-hidden">
          <div
            className="h-full rounded-full bg-signal-amber"
            style={{ width: `${((team.elo - 1400) / 800) * 100}%` }}
          />
        </div>
        <span className="font-mono text-sm text-signal-amber w-14 text-right">{team.elo.toFixed(0)}</span>
      </div>
    </div>
  )
}

export function Rankings() {
  const [sport, setSport] = useState<Sport>('soccer')
  const [data, setData] = useState<RankingsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')

  useEffect(() => {
    setLoading(true)
    const fetch = sport === 'soccer' ? api.soccerRankings() : api.nflRankings()
    fetch
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [sport])

  const filtered = (data?.teams ?? []).filter(t =>
    t.name.toLowerCase().includes(search.toLowerCase()) ||
    t.code.toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-100">
          Power Rankings
        </h1>
        <p className="text-sm text-zinc-500 mt-1 font-body">Sorted by Elo rating — higher = stronger.</p>
      </div>

      <div className="flex items-center gap-3">
        {(['soccer', 'nfl'] as Sport[]).map(s => (
          <button
            key={s}
            onClick={() => setSport(s)}
            className={`px-4 py-1.5 rounded-lg text-sm font-display font-medium transition-colors ${
              sport === s
                ? 'bg-signal-amber text-terminal-bg'
                : 'bg-terminal-surface border border-terminal-border text-zinc-400 hover:text-zinc-100'
            }`}
          >
            {s === 'soccer' ? '⚽ World Cup' : '🏈 NFL'}
          </button>
        ))}

        <input
          type="text"
          placeholder="Search team…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="ml-auto w-40 rounded-lg border border-terminal-border bg-terminal-surface px-3 py-1.5 text-sm font-body text-zinc-100 placeholder-zinc-600 focus:border-signal-amber focus:outline-none"
        />
      </div>

      <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4">
        {/* Header */}
        <div className="flex items-center gap-3 pb-2 border-b border-terminal-border text-[10px] font-display uppercase tracking-widest text-zinc-600">
          <span className="w-6 text-right">#</span>
          <span className="w-7" />
          <span className="flex-1">Team</span>
          <span className="w-32 text-right">Elo Rating</span>
        </div>

        {loading ? (
          <div className="py-12 text-center text-zinc-600 font-mono text-sm">Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="py-12 text-center text-zinc-600 font-mono text-sm">No teams found.</div>
        ) : (
          filtered.map(t => <TeamRow key={t.code} team={t} sport={sport} />)
        )}
      </div>

      <p className="text-[10px] text-zinc-600 italic">
        {sport === 'soccer'
          ? 'Elo ratings sourced from eloratings.net scale (June 2026). Hosts USA, MEX, CAN receive +150 home-venue bonus in predictions, not reflected here.'
          : 'Elo ratings calibrated to end-of-2025 NFL season. Home-field advantage (+48 Elo) applied during predictions.'}
      </p>
    </div>
  )
}
