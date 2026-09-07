import type { LiveGameOut } from '../../types'
import { GameStatus } from './GameStatus'

function TeamRow({
  name, abbr, logo, score, showScore, winner,
}: {
  name: string; abbr: string; logo?: string
  score?: number | null; showScore: boolean; winner: boolean
}) {
  return (
    <div className="flex items-center gap-3">
      {logo
        ? <img src={logo} alt="" className="h-9 w-9 shrink-0 object-contain" loading="lazy" />
        : <span className="grid h-9 w-9 shrink-0 place-items-center rounded bg-terminal-muted text-xs font-bold text-zinc-300">{abbr.slice(0, 3)}</span>}
      <span className={`min-w-0 flex-1 truncate text-base font-bold ${winner ? 'text-zinc-100' : 'text-zinc-200'}`}>
        {name}
      </span>
      {showScore && (
        <span className="font-mono text-2xl font-black tabular-nums text-zinc-100">{score ?? 0}</span>
      )}
    </div>
  )
}

/**
 * Matchup identity + state. Scores only appear once the game has actually
 * started; before kickoff the teams are separated by "vs." so nothing reads
 * like a 0–0 in progress.
 */
export function GameHeader({ game, leagueLabel }: { game: LiveGameOut; leagueLabel: string }) {
  const started = game.state === 'in' || game.state === 'post'
  const homeWon = started && (game.home_score ?? 0) > (game.away_score ?? 0)
  const awayWon = started && (game.away_score ?? 0) > (game.home_score ?? 0)

  return (
    <header className="rounded-xl border border-terminal-border bg-terminal-surface p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <span className="text-xs font-semibold uppercase tracking-wide text-zinc-400">{leagueLabel}</span>
        <GameStatus game={game} />
      </div>

      <h1 className="sr-only">
        {game.away} {started ? game.away_score ?? 0 : 'vs.'} {started ? game.home_score ?? 0 : ''} {game.home}
      </h1>

      <div className="space-y-2">
        <TeamRow name={game.away} abbr={game.away_abbr} logo={game.away_logo}
                 score={game.away_score} showScore={started} winner={awayWon} />
        {!started && (
          <div className="pl-12 text-xs font-semibold uppercase tracking-wide text-zinc-500">vs.</div>
        )}
        <TeamRow name={game.home} abbr={game.home_abbr} logo={game.home_logo}
                 score={game.home_score} showScore={started} winner={homeWon} />
      </div>
    </header>
  )
}
