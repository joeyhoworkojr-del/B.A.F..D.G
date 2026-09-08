import { useEffect, useMemo, useState } from 'react'
import { api } from '../../api/client'
import { useSession } from '../../session/SessionProvider'
import type { TeamInfo } from '../../types'

const LEAGUES = [
  { id: 'nfl' as const, label: 'NFL' },
  { id: 'ncaaf' as const, label: 'College' },
]

// Enough to follow a conference, few enough that the homepage stays a homepage
// rather than a second full board.
const MAX_TEAMS = 12

/**
 * Pick the teams you follow.
 *
 * Stored as `league:CODE` so a college and an NFL team sharing an abbreviation
 * stay distinct — several do.
 */
export function FavouriteTeams() {
  const { user, applySession } = useSession()
  const [league, setLeague] = useState<'nfl' | 'ncaaf'>('nfl')
  const [teams, setTeams] = useState<Record<string, TeamInfo[]>>({})
  const [selected, setSelected] = useState<string[]>(user?.favourite_teams ?? [])
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('')

  useEffect(() => {
    if (teams[league]) return
    let alive = true
    api.leagueTeams(league)
      .then(list => { if (alive) setTeams(prev => ({ ...prev, [league]: list })) })
      .catch(() => { if (alive) setError('That team list could not be loaded.') })
    return () => { alive = false }
  }, [league, teams])

  const visible = useMemo(() => {
    const list = teams[league] ?? []
    const q = filter.trim().toLowerCase()
    if (!q) return list
    return list.filter(t => t.name.toLowerCase().includes(q) || t.code.toLowerCase().includes(q))
  }, [teams, league, filter])

  const toggle = (code: string) => {
    const key = `${league}:${code}`
    setSaved(false)
    setSelected(prev => {
      if (prev.includes(key)) return prev.filter(k => k !== key)
      if (prev.length >= MAX_TEAMS) return prev
      return [...prev, key]
    })
  }

  const save = async () => {
    setSaving(true); setError(''); setSaved(false)
    try {
      applySession(await api.updateProfile({ favourite_teams: selected }))
      setSaved(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'That could not be saved.')
    } finally {
      setSaving(false)
    }
  }

  const atLimit = selected.length >= MAX_TEAMS

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        {LEAGUES.map(l => (
          <button
            key={l.id}
            type="button"
            onClick={() => setLeague(l.id)}
            aria-pressed={league === l.id}
            className={`tap rounded-full border px-3 text-sm font-semibold transition ${
              league === l.id
                ? 'border-brand bg-brand-soft text-brand'
                : 'border-terminal-border bg-terminal-surface text-zinc-400 hover:text-zinc-100'
            }`}
          >
            {l.label}
          </button>
        ))}
        <label htmlFor="team-filter" className="sr-only">Filter teams</label>
        <input
          id="team-filter"
          value={filter}
          onChange={e => setFilter(e.target.value)}
          placeholder="Filter…"
          className="ml-auto w-32 rounded-lg border border-terminal-border bg-terminal-bg px-3 py-1.5 text-sm text-zinc-100 placeholder:text-zinc-600"
        />
      </div>

      <div className="mt-3 max-h-64 overflow-y-auto rounded-lg border border-terminal-border p-2">
        {!teams[league] && <p className="p-2 text-sm text-zinc-500">Loading teams…</p>}
        {teams[league] && visible.length === 0 && (
          <p className="p-2 text-sm text-zinc-500">No team matches “{filter}”.</p>
        )}
        <div className="flex flex-wrap gap-1.5">
          {visible.map(t => {
            const key = `${league}:${t.code}`
            const on = selected.includes(key)
            return (
              <button
                key={key}
                type="button"
                onClick={() => toggle(t.code)}
                aria-pressed={on}
                disabled={!on && atLimit}
                className={`tap rounded-full border px-2.5 text-sm font-semibold transition disabled:opacity-40 ${
                  on
                    ? 'border-brand bg-brand-soft text-brand'
                    : 'border-terminal-border bg-terminal-surface text-zinc-400 hover:text-zinc-100'
                }`}
              >
                {t.name}
              </button>
            )
          })}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={save}
          disabled={saving}
          className="tap inline-flex items-center rounded-lg bg-brand px-4 text-sm font-semibold text-white hover:bg-brand-strong disabled:opacity-60"
        >
          {saving ? 'Saving…' : 'Save teams'}
        </button>
        <span className="text-xs text-zinc-500">
          {selected.length} of {MAX_TEAMS} selected
          {atLimit && ' — remove one to add another'}
        </span>
        {saved && <span className="text-sm font-semibold text-signal-green">Saved</span>}
        {error && <span role="alert" className="text-sm text-signal-red">{error}</span>}
      </div>
    </div>
  )
}
