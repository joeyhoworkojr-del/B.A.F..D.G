import type { LiveGameOut } from '../../types'
import { GameStatus } from './GameStatus'

function kickoffParts(iso: string): [string, string] {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ['', '']
  return [
    d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }),
    d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }),
  ]
}

function Side({
  name, abbr, logo, record, score, showScore, winner, align,
}: {
  name: string; abbr: string; logo?: string; record?: string
  score?: number | null; showScore: boolean; winner: boolean
  align: 'left' | 'right'
}) {
  const end = align === 'right'
  return (
    <div className={`flex min-w-0 flex-1 flex-col gap-1.5 ${end ? 'items-end text-right' : 'items-start text-left'}`}>
      {logo
        ? <img src={logo} alt="" className="h-10 w-10 object-contain sm:h-12 sm:w-12" loading="lazy" />
        // Decorative: the abbreviation is spelled out directly below, and a
        // reader announcing "FSU FSU Florida State" helps nobody.
        : <span aria-hidden="true"
                className="grid h-10 w-10 place-items-center rounded-lg bg-terminal-muted text-sm font-bold text-zinc-400 sm:h-12 sm:w-12">
            {abbr.slice(0, 3)}
          </span>}
      <span className={`text-sm font-bold ${winner ? 'text-zinc-100' : 'text-zinc-300'}`}>
        {abbr}
        {/* Absent before a season has any games in it, which is a real state. */}
        {record && <span className="ml-1.5 font-mono text-xs font-normal text-zinc-500">{record}</span>}
      </span>
      {/* The crest and code identify the team on a phone; the full name is a
          nicety that costs a line, and the page heading carries it regardless. */}
      <span className="hidden truncate text-xs text-zinc-500 sm:block" title={name}>{name}</span>
      {showScore && (
        <span className={`font-mono text-4xl font-black tabular-nums ${winner ? 'text-zinc-100' : 'text-zinc-400'}`}>
          {score ?? 0}
        </span>
      )}
    </div>
  )
}

/**
 * The matchup, read left to right: away, when, home.
 *
 * Scores appear only once the game has started — before kickoff the middle
 * column carries the date and time instead, so nothing reads as a 0–0 already
 * in progress.
 */
export function MatchupBanner({
  game, leagueLabel,
}: { game: LiveGameOut; leagueLabel: string }) {
  const started = game.state === 'in' || game.state === 'post'
  const homeWon = started && (game.home_score ?? 0) > (game.away_score ?? 0)
  const awayWon = started && (game.away_score ?? 0) > (game.home_score ?? 0)
  const [day, time] = kickoffParts(game.kickoff)

  return (
    <header className="rounded-card border border-terminal-border bg-terminal-surface px-4 py-3">
      <h1 className="sr-only">
        {game.away} {started ? game.away_score ?? 0 : 'vs.'} {started ? game.home_score ?? 0 : ''} {game.home}
      </h1>

      <div className="flex items-start gap-3">
        <Side name={game.away} abbr={game.away_abbr} logo={game.away_logo} record={game.away_record}
              score={game.away_score} showScore={started} winner={awayWon} align="left" />

        <div className="flex shrink-0 flex-col items-center gap-1 pt-1 text-center">
          <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">{leagueLabel}</span>
          {started
            ? <GameStatus game={game} />
            : (
              <>
                <span className="text-sm font-bold text-zinc-100">{day}</span>
                <span className="text-sm text-zinc-400">{time}</span>
              </>
            )}
          {started && <span className="text-xs text-zinc-500">{day}</span>}
        </div>

        <Side name={game.home} abbr={game.home_abbr} logo={game.home_logo} record={game.home_record}
              score={game.home_score} showScore={started} winner={homeWon} align="right" />
      </div>
    </header>
  )
}
