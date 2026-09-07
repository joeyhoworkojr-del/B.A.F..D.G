"""
Player prop projections.

A projection is a player's established per-game usage, rescaled to the game the
team model actually expects. If the model projects a team to score 31 in a fast
game, its passer projects above his season average; if it projects 17 in a
grind, below it.

The scaling is deliberately conservative. Player outcomes are far noisier than
team totals, so the environment multiplier is shrunk and clamped and the season
average stays the anchor.

Nothing here invents a player. Every projection traces to usage ESPN published
for that athlete; a player with no usable stat line gets no projection.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from src.ingest.player_stats import PlayerUsage

# League-average points per team per game, used to turn the model's projected
# score into a "how busy is this offence" multiplier.
LEAGUE_AVG_TEAM_POINTS = {"nfl": 22.5, "ncaaf": 27.5}

# How much of the scoring swing reaches a player's line. A team projected 40%
# above average does not throw for 40% more yards — volume is capped by the
# clock, and a big lead suppresses passing. 0.45 keeps the response real but
# damped.
ENVIRONMENT_SENSITIVITY = 0.45

# Hard bounds, so an extreme team projection cannot produce an absurd line.
MULT_FLOOR, MULT_CEILING = 0.78, 1.28

# Standard deviation as a fraction of the projected mean, from the historical
# spread of player games. Used for the over/under probability.
_REL_SIGMA = {
    "pass_yards": 0.30, "pass_attempts": 0.20, "pass_tds": 0.70,
    "rush_yards": 0.45, "carries": 0.28, "rush_tds": 0.95,
    "rec_yards": 0.50, "receptions": 0.35, "rec_tds": 1.00,
}

MARKET_LABELS = {
    "pass_yards": "Passing yards", "pass_attempts": "Pass attempts",
    "pass_tds": "Passing TDs", "rush_yards": "Rushing yards",
    "carries": "Carries", "rush_tds": "Rushing TDs",
    "rec_yards": "Receiving yards", "receptions": "Receptions",
    "rec_tds": "Receiving TDs",
}

# Markets whose numbers are small counts; a 0.4-TD "projection" is noise, so
# these are only published when the projection clears a floor.
_MIN_PUBLISHABLE = {
    "pass_yards": 60.0, "pass_attempts": 8.0, "pass_tds": 0.6,
    "rush_yards": 15.0, "carries": 4.0, "rush_tds": 0.25,
    "rec_yards": 15.0, "receptions": 1.5, "rec_tds": 0.25,
}

# Minimum games before a season average is trustworthy enough to project from.
MIN_GAMES = 2


@dataclass
class PropProjection:
    athlete_id: str
    player: str
    team_abbr: str
    position: str
    market: str
    label: str
    projection: float
    season_avg: float
    games_played: int
    # True when this is the player's actual line in a game under way, not a
    # forecast. The UI must never label an actual as a projection.
    actual: bool = False


def environment_multiplier(league: str, projected_team_points: Optional[float]) -> float:
    """
    How much busier or quieter this offence is than a league-average one.

    Returns exactly 1.0 when there is no team projection to scale by, so a
    missing model number leaves the season average untouched rather than
    silently biasing every player.
    """
    if projected_team_points is None or projected_team_points <= 0:
        return 1.0
    baseline = LEAGUE_AVG_TEAM_POINTS.get(league.lower(), 25.0)
    raw = projected_team_points / baseline
    damped = 1.0 + (raw - 1.0) * ENVIRONMENT_SENSITIVITY
    return max(MULT_FLOOR, min(MULT_CEILING, damped))


def over_probability(projection: float, line: float, market: str) -> Optional[float]:
    """
    Probability the player goes over `line`, from a normal around the
    projection. None when the market has no calibrated spread.
    """
    rel = _REL_SIGMA.get(market)
    if rel is None or projection <= 0:
        return None
    sigma = max(projection * rel, 0.5)
    z = (projection - line) / (sigma * math.sqrt(2.0))
    return round(0.5 * (1.0 + math.erf(z)), 4)


def _fields_for(usage: PlayerUsage) -> list[tuple[str, Optional[float]]]:
    if usage.role == "passer":
        return [("pass_yards", usage.pass_yards_pg),
                ("pass_attempts", usage.pass_attempts_pg),
                ("pass_tds", usage.pass_tds_pg)]
    if usage.role == "rusher":
        return [("rush_yards", usage.rush_yards_pg),
                ("carries", usage.carries_pg),
                ("rush_tds", usage.rush_tds_pg)]
    return [("rec_yards", usage.rec_yards_pg),
            ("receptions", usage.receptions_pg),
            ("rec_tds", usage.rec_tds_pg)]


def project_player(
    usage: PlayerUsage, league: str, projected_team_points: Optional[float],
) -> list[PropProjection]:
    """Every publishable market for one player. Empty when usage is too thin."""
    # An actual box-score line is reported as-is: it already happened, so there
    # is nothing to project and nothing to scale.
    if usage.actual:
        mult = 1.0
    else:
        if usage.games_played and usage.games_played < MIN_GAMES:
            return []
        mult = environment_multiplier(league, projected_team_points)

    out: list[PropProjection] = []
    for market, season_avg in _fields_for(usage):
        if season_avg is None or season_avg <= 0:
            continue
        projection = round(season_avg * mult, 1)
        if projection < _MIN_PUBLISHABLE.get(market, 0.0):
            continue
        out.append(PropProjection(
            athlete_id=usage.athlete_id,
            player=usage.name,
            team_abbr=usage.team_abbr,
            position=usage.position,
            market=market,
            label=MARKET_LABELS.get(market, market),
            projection=projection,
            season_avg=round(season_avg, 1),
            games_played=usage.games_played,
            actual=usage.actual,
        ))
    return out


def project_game(
    players: list[PlayerUsage],
    league: str,
    home_abbr: str,
    away_abbr: str,
    home_points: Optional[float],
    away_points: Optional[float],
) -> list[PropProjection]:
    """
    Projections for every player in a game, each scaled by their own team's
    projected score. Sorted so the biggest numbers lead.
    """
    out: list[PropProjection] = []
    for usage in players:
        if usage.team_abbr and usage.team_abbr == home_abbr:
            team_points = home_points
        elif usage.team_abbr and usage.team_abbr == away_abbr:
            team_points = away_points
        else:
            team_points = None      # unknown team — no scaling, season average stands
        out.extend(project_player(usage, league, team_points))

    order = {"pass_yards": 0, "rush_yards": 1, "rec_yards": 2}
    out.sort(key=lambda p: (order.get(p.market, 3), -p.projection))
    return out
