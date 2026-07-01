import type { TeamInfo } from '../types'

interface Props {
  teams: TeamInfo[]
  value: string
  onChange: (code: string) => void
  label: string
  placeholder?: string
}

export function TeamSelect({ teams, value, onChange, label, placeholder = 'Select team…' }: Props) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-display uppercase tracking-widest text-zinc-400">{label}</label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="
          w-full rounded-lg border border-terminal-border bg-terminal-surface
          px-3 py-2.5 font-body text-sm text-zinc-100
          focus:border-signal-amber focus:outline-none focus:ring-1 focus:ring-signal-amber/40
          appearance-none cursor-pointer
        "
      >
        <option value="">{placeholder}</option>
        {teams.map(t => (
          <option key={t.code} value={t.code}>
            {t.flag} {t.name} {t.elo ? `(Elo ${t.elo.toFixed(0)})` : ''}
          </option>
        ))}
      </select>
    </div>
  )
}
