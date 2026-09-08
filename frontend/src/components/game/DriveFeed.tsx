import type { PlayOut } from '../../types'

/**
 * Play-by-play as drives, with the ball moving.
 *
 * A list of sentences tells you what happened; it does not show you a team
 * marching. Each play draws the yards it covered as a bar on a shared field
 * scale, so a 40-yard strike and a stuffed run look different at a glance and
 * a drive reads as progress down the field.
 *
 * Every play still shows its text. The field strip is an addition, and where
 * the feed publishes no position — which happens, especially in college — the
 * play renders as it always did rather than being drawn somewhere it was not.
 */

interface Drive {
  id: string
  team: string
  description: string
  plays: PlayOut[]
}

/** Group consecutive plays into the possession they belong to. */
function toDrives(plays: PlayOut[]): Drive[] {
  const drives: Drive[] = []
  for (const play of plays) {
    const id = play.drive_id || `${play.team_abbr}-${play.period ?? 0}`
    const last = drives[drives.length - 1]
    if (last && last.id === id) {
      last.plays.push(play)
    } else {
      drives.push({
        id,
        team: play.team_abbr ?? '',
        description: play.drive_description ?? '',
        plays: [play],
      })
    }
  }
  return drives
}

const RESULT_TONE: Record<string, string> = {
  touchdown: 'text-signal-green',
  'field goal': 'text-signal-green',
  interception: 'text-signal-red',
  fumble: 'text-signal-red',
  downs: 'text-signal-red',
  punt: 'text-zinc-500',
}

function toneFor(description: string): string {
  const lower = description.toLowerCase()
  const key = Object.keys(RESULT_TONE).find(k => lower.includes(k))
  return key ? RESULT_TONE[key] : 'text-zinc-400'
}

/** One play: where the ball started, where it ended, and how far that was. */
function PlayStrip({ play }: { play: PlayOut }) {
  const start = play.start_yard_line
  const end = play.end_yard_line
  const drawable = typeof start === 'number' && typeof end === 'number'
  const gained = play.yards_gained

  return (
    <li className={`border-b border-terminal-border/50 py-2 last:border-0 ${
      play.scoring ? 'bg-signal-green/5' : ''
    }`}>
      <div className="flex items-baseline gap-2">
        <span className="w-16 shrink-0 font-mono text-xs text-zinc-500">
          {play.period ? `Q${play.period}` : ''} {play.clock}
        </span>
        <p className={`min-w-0 flex-1 text-sm leading-snug ${
          play.scoring ? 'font-semibold text-signal-green' : 'text-zinc-300'
        }`}>
          {play.text}
        </p>
        {gained != null && (
          <span className={`shrink-0 font-mono text-xs font-bold tabular-nums ${
            gained > 0 ? 'text-signal-green' : gained < 0 ? 'text-signal-red' : 'text-zinc-500'
          }`}>
            {gained > 0 ? `+${gained}` : gained}
          </span>
        )}
      </div>

      {drawable && (
        <div className="ml-16 mt-1.5">
          {/* The field, left = own goal, right = the one being attacked. */}
          <div className="relative h-2 overflow-hidden rounded-full bg-terminal-muted">
            <div
              className="absolute inset-y-0 left-0 bg-zinc-700/40"
              style={{ width: `${Math.min(start!, end!)}%` }}
              aria-hidden="true"
            />
            <div
              className={`absolute inset-y-0 ${
                end! >= start! ? 'bg-signal-green' : 'bg-signal-red'
              }`}
              style={{
                left: `${Math.min(start!, end!)}%`,
                width: `${Math.max(Math.abs(end! - start!), 0.8)}%`,
              }}
              aria-hidden="true"
            />
          </div>
          <p className="mt-0.5 text-[11px] text-zinc-500">
            {play.down && play.distance != null && (
              <>{ordinal(play.down)} &amp; {play.distance} · </>
            )}
            {spotLabel(start!)} → {spotLabel(end!)}
          </p>
        </div>
      )}
    </li>
  )
}

function ordinal(n: number): string {
  return { 1: '1st', 2: '2nd', 3: '3rd', 4: '4th' }[n] ?? `${n}th`
}

/** A yard line, phrased the way a commentator would. */
function spotLabel(yardLine: number): string {
  if (yardLine >= 100) return 'the end zone'
  if (yardLine <= 0) return 'their own goal line'
  return yardLine <= 50 ? `own ${yardLine}` : `opp ${100 - yardLine}`
}

export function DriveFeed({ plays }: { plays: PlayOut[] }) {
  // The feed arrives newest first; a drive reads forwards.
  const drives = toDrives([...plays].reverse()).reverse()

  return (
    <div className="max-h-[32rem] space-y-3 overflow-y-auto">
      {drives.map(drive => {
        const first = drive.plays[0]
        const last = drive.plays[drive.plays.length - 1]
        const from = first?.start_yard_line
        const to = last?.end_yard_line
        const netYards =
          typeof from === 'number' && typeof to === 'number' ? to - from : null

        return (
          <section key={drive.id} className="rounded-lg border border-terminal-border">
            <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-terminal-border bg-terminal-muted px-3 py-1.5">
              <span className="text-xs font-bold text-zinc-100">
                {drive.team || 'Drive'}
                <span className="ml-2 font-normal text-zinc-500">
                  {drive.plays.length} play{drive.plays.length === 1 ? '' : 's'}
                  {netYards != null && `, ${netYards >= 0 ? '+' : ''}${netYards} yards`}
                </span>
              </span>
              {drive.description && (
                <span className={`text-xs font-bold uppercase tracking-wide ${toneFor(drive.description)}`}>
                  {drive.description}
                </span>
              )}
            </header>
            <ul className="px-3">
              {drive.plays.map((play, i) => (
                <PlayStrip key={`${drive.id}-${i}`} play={play} />
              ))}
            </ul>
          </section>
        )
      })}
    </div>
  )
}
