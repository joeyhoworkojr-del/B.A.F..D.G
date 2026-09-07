import type { PropProjectionOut } from '../../types'

const num = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1))

/**
 * Player projections for one team.
 *
 * The "vs season" column is the point of the table: it shows whether the model
 * expects this game to be busier or quieter than the player's normal, which is
 * the only thing a projection adds over a plain season average.
 */
export function PropsTable({
  teamAbbr, teamName, rows,
}: { teamAbbr: string; teamName: string; rows: PropProjectionOut[] }) {
  if (rows.length === 0) return null
  const anyActual = rows.some(r => r.actual)

  return (
    <section
      aria-labelledby={`props-${teamAbbr}`}
      className="min-w-0 rounded-card border border-terminal-border bg-terminal-surface"
    >
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-terminal-border px-4 py-3">
        <h3 id={`props-${teamAbbr}`} className="text-sm font-bold text-zinc-100">
          <span className="mr-2 rounded bg-terminal-muted px-1.5 py-0.5 text-xs font-bold text-zinc-400">
            {teamAbbr}
          </span>
          {teamName}
        </h3>
        <span className="text-xs font-semibold text-zinc-500">
          {anyActual ? 'Actual — game in progress' : 'Projected'}
        </span>
      </header>

      <div className="w-full max-w-full overflow-x-auto">
        <table className="w-full min-w-[30rem] text-sm">
          <caption className="sr-only">
            {anyActual
              ? `Actual player statistics so far for ${teamName}`
              : `Projected player statistics for ${teamName}`}
          </caption>
          <thead>
            <tr className="border-b border-terminal-border text-xs uppercase tracking-wide text-zinc-500">
              <th scope="col" className="px-4 py-2 text-left font-semibold">Player</th>
              <th scope="col" className="px-4 py-2 text-left font-semibold">Market</th>
              <th scope="col" className="px-4 py-2 text-right font-semibold">
                {anyActual ? 'Actual' : 'Projection'}
              </th>
              <th scope="col" className="px-4 py-2 text-right font-semibold">Season avg</th>
              <th scope="col" className="px-4 py-2 text-right font-semibold">vs season</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => {
              const delta = r.projection - r.season_avg
              const pct = r.season_avg > 0 ? (delta / r.season_avg) * 100 : 0
              return (
                <tr key={`${r.athlete_id}:${r.market}`} className="border-b border-terminal-border/60 last:border-0">
                  <th scope="row" className="px-4 py-2.5 text-left font-semibold text-zinc-100">
                    {r.player}
                    {r.position && <span className="ml-1.5 text-xs font-normal text-zinc-500">{r.position}</span>}
                  </th>
                  <td className="px-4 py-2.5 text-zinc-400">{r.label}</td>
                  <td className="px-4 py-2.5 text-right font-mono font-bold tabular-nums text-zinc-100">
                    {num(r.projection)}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-zinc-500">
                    {r.actual ? '—' : num(r.season_avg)}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums">
                    {r.actual ? (
                      <span className="text-zinc-500">—</span>
                    ) : Math.abs(pct) < 0.5 ? (
                      <span className="text-zinc-500">even</span>
                    ) : (
                      // Direction only — the model expecting more volume than
                      // normal is not a claim of value against a price.
                      <span className={pct > 0 ? 'text-signal-green' : 'text-zinc-400'}>
                        {pct > 0 ? '+' : ''}{pct.toFixed(0)}%
                      </span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
