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
from dataclasses import dataclass, field
from typing import Optional

from src.ingest.player_stats import PlayerUsage
from src.predict import distributions

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
# spread of player games. This is the PRIOR — the starting assumption for a
# player whose own game log is too short to say anything. Where a log exists,
# the player's own spread is blended in; see `sigma_for`.
_REL_SIGMA = {
    "pass_yards": 0.30, "pass_attempts": 0.20, "pass_tds": 0.70,
    "rush_yards": 0.45, "carries": 0.28, "rush_tds": 0.95,
    "rec_yards": 0.50, "receptions": 0.35, "rec_tds": 1.00,
}

# ── Anytime touchdown ──
#
# A different kind of market from the yardage props: no line to go over, a yes
# or no priced like a moneyline. So the question is not "what shape sits around
# this mean" but "what is the chance of at least one rare event", which is a
# Poisson on the player's touchdown rate.
#
# The rate is shrunk toward a base before the Poisson is taken, because a rate
# off five games swings wildly and a player who has not scored yet does not
# have a rate of zero. Measured on 14,361 player-games across 2022-2026:
#
#     shrunk Poisson    2.5p     ← used
#     raw Poisson       3.4p
#     his own hit rate  4.4p
#
# Reproduce with `python -m tools.backtest atd`.
#
# A more principled construction was built and measured against this, and lost.
# The argument for it is good: a touchdown is not something a player does on his
# own, it is something his offence does and he takes a share of, so expected
# team touchdowns times his share should respond properly to game script — well
# above his season rate in a game priced 31-13, well below it in a 17-20 grind.
# Implemented with team scoring from the market's own total and spread, and the
# points-to-touchdowns coefficient fitted rather than guessed (0.109, about one
# touchdown per 9.2 points, over 1,792 team-games):
#
#     shrunk Poisson on his own rate      1.4p     ← kept
#     expected team TDs x player share    2.5p
#
# Measured on the same 11,000 player-games. It is worse, and the reason is that
# it compounds three noisy estimates — his share of his team's touchdowns, his
# team's touchdowns while he played, and the market's points converted to
# touchdowns — where the simpler model uses one. Recorded here so the idea is
# not rebuilt on the strength of sounding better than what it replaces.
ANYTIME_TD = "anytime_td"
ATD_BASE_RATE = 0.35        # touchdowns per game for a player with a real role
ATD_SHRINK_GAMES = 6.0
# Below this expected rate there is no meaningful chance to publish, and a
# number like 2% invites a price nobody should take.
ATD_MIN_RATE = 0.06

MARKET_LABELS = {
    ANYTIME_TD: "Anytime TD",
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

# ── Recent form against the season ──
# How many recent games count as "form", and how much weight they take off the
# season average at full strength. A role changes mid-season — a back splitting
# carries in September can be carrying the offence by November — and a season
# average dilutes that with games the player no longer resembles. It is capped
# well under 1.0 because recency is also where overreaction lives: three games
# is a small sample and a single garbage-time blowout can own it.
FORM_WINDOW = 4
FORM_MAX_WEIGHT = 0.45

# ── Per-player spread ──
# How many of a player's own games it takes for their observed spread to be
# trusted over the market-wide prior. Below this the two are blended in
# proportion, so a two-game sample barely moves it and a twelve-game one
# mostly owns it.
SIGMA_SHRINK_GAMES = 6.0

# A spread cannot be allowed to collapse to nothing on a lucky run of
# consistent games, or the over/under probability goes to a near certainty off
# four data points. Floored and capped as a fraction of the projection.
SIGMA_REL_FLOOR, SIGMA_REL_CEILING = 0.12, 1.20

# ── Opponent ──
# How much of the opponent's defensive rating reaches a player's line, and the
# bounds. A defence a touchdown better than average does not take a touchdown
# off one receiver's yardage: the effect is real, shared across an offence, and
# smaller than the team-level number suggests.
OPPONENT_SENSITIVITY = 0.35
OPPONENT_FLOOR, OPPONENT_CEILING = 0.88, 1.12


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
    # ── What went into the number, so it can be audited rather than trusted ──
    # The average over the recent window, where there was one to take.
    recent_avg: Optional[float] = None
    form_weight: float = 0.0
    # The spread used for the over/under probability, and where it came from.
    # "player" means the athlete's own game-to-game variation carried most of
    # the weight; "market" means the log was too short and the league-wide
    # prior stood.
    sigma: Optional[float] = None
    sigma_source: str = "market"
    sigma_games: int = 0
    # Multipliers actually applied, so a reader can see why a projection sits
    # above or below the season average.
    environment_mult: float = 1.0
    opponent_mult: float = 1.0
    opponent_abbr: str = ""
    opponent_note: str = ""
    # Oldest first. The evidence behind everything above.
    game_log: list = field(default_factory=list)
    # Binary markets only (anytime touchdown): the chance of it happening at
    # all. `projection` carries the expected count behind it. None for every
    # over/under market, where the question is a line and not a yes or no.
    yes_prob: Optional[float] = None


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


def anytime_td_rate(samples: list[float]) -> Optional[float]:
    """
    Expected touchdowns this game, from the player's own log shrunk to a base.

    `samples` is rushing plus receiving touchdowns per game, oldest first — a
    passing touchdown is not scored by the quarterback and is not in it.
    """
    clean = [float(v) for v in samples if v is not None]
    if not clean:
        return None
    total = sum(clean)
    return (total + ATD_BASE_RATE * ATD_SHRINK_GAMES) / (len(clean) + ATD_SHRINK_GAMES)


def anytime_td_probability(samples: list[float]) -> Optional[float]:
    """P(at least one touchdown) = 1 - e^-rate, on the shrunk rate."""
    rate = anytime_td_rate(samples)
    if rate is None or rate <= 0:
        return None
    return round(1.0 - math.exp(-rate), 4)


def _sample_sd(values: list[float]) -> Optional[float]:
    """Sample standard deviation, or None below two observations."""
    clean = [float(v) for v in values if v is not None]
    if len(clean) < 2:
        return None
    mean = sum(clean) / len(clean)
    var = sum((v - mean) ** 2 for v in clean) / (len(clean) - 1)
    return math.sqrt(var)


def sigma_for(
    projection: float, market: str, samples: Optional[list[float]] = None,
) -> tuple[Optional[float], str, int]:
    """
    The spread to put around a projection, and where it came from.

    A single league-wide spread per market says a possession receiver who
    catches five every week and a deep threat who alternates between two and
    nine are the same bet. They are not, and the over/under probability comes
    entirely out of this number, so that error goes straight into the output.

    So the player's own game-to-game spread is used — blended toward the
    market-wide prior in proportion to how many games it rests on, because a
    standard deviation off three games is itself mostly noise. Floored and
    capped, so a lucky run of consistent games cannot collapse the spread and
    turn a coin flip into a near certainty.

    Returns (sigma, source, games) where source is "player" once the athlete's
    own log carries most of the weight, and "market" while the prior does.
    """
    rel = _REL_SIGMA.get(market)
    if rel is None or projection <= 0:
        return None, "none", 0

    prior = projection * rel
    observed = _sample_sd(samples or [])
    games = len([v for v in (samples or []) if v is not None])

    if observed is None:
        sigma, source = prior, "market"
    else:
        # Shrinkage: the player's own spread earns weight with each game.
        weight = games / (games + SIGMA_SHRINK_GAMES)
        sigma = weight * observed + (1.0 - weight) * prior
        source = "player" if weight >= 0.5 else "market"

    sigma = max(projection * SIGMA_REL_FLOOR, min(projection * SIGMA_REL_CEILING, sigma))
    return max(sigma, 0.5), source, games


def over_probability(
    projection: float, line: float, market: str,
    samples: Optional[list[float]] = None,
    sigma: Optional[float] = None,
) -> Optional[float]:
    """
    Probability the player goes over `line`.

    The shape around the projection is chosen per market from measured
    calibration, not assumed — see `distributions`. This used a symmetric
    normal for everything, which overstated the over at every probability
    above 30% because rushing and receiving production is skewed: measured
    across four seasons, "53%" happened 44% of the time. Mean absolute
    calibration error fell from 8.1 points to 2.0 by fixing the shape alone.

    Pass `sigma` when it has already been computed for this projection, so the
    number shown beside the probability is the number the probability used.
    """
    if sigma is None:
        sigma, _, _ = sigma_for(projection, market, samples)
    if sigma is None or projection <= 0:
        return None
    p = distributions.over_probability(market, line, projection, sigma)
    return round(p, 4) if p is not None else None


def opponent_multiplier(league: str, opponent_code: str) -> tuple[float, str]:
    """
    How much easier or harder this opponent is than an average one.

    Uses the same play-by-play ratings the game model runs on, so a prop and
    the spread cannot disagree about who the defence is. Returns exactly 1.0
    and says why whenever there is no rating — a missing feed must not quietly
    become an average opponent, because that is a claim we did not make.
    """
    if not opponent_code:
        return 1.0, "opponent unknown"

    from src.predict import priors

    rank = priors.team_rank(league, opponent_code)
    if rank is None:
        return 1.0, (
            "no play-by-play rating for this opponent, so no adjustment"
            if league == "nfl"
            else "opponent strength is not modelled for college props"
        )

    # `points` is the team's margin against an average side: positive is a
    # better team, which for a defence means a harder matchup.
    raw = 1.0 - (rank["points"] / 100.0) * OPPONENT_SENSITIVITY
    mult = max(OPPONENT_FLOOR, min(OPPONENT_CEILING, raw))
    direction = "tougher than average" if mult < 1.0 else "softer than average"
    return mult, (
        f"{opponent_code} rated {rank['rank']} of {rank['of']} "
        f"({rank['points']:+.1f} pts/g) — {direction}"
    )


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


def _form_blend(
    season_avg: float, samples: list[float],
) -> tuple[float, Optional[float], float]:
    """
    Pull the season average toward recent form, by as much as the window earns.

    A role changes mid-season: a back splitting carries in September can be
    carrying the offence by November, and a season average dilutes that with
    games the player no longer resembles. The weight is capped well under 1.0
    because recency is also where overreaction lives — three games is a small
    sample, and one garbage-time blowout should not own a projection.

    Returns (blended, recent_avg, weight). `recent_avg` is None when there was
    no window to take, in which case the season average stands untouched.
    """
    recent = [v for v in samples[-FORM_WINDOW:] if v is not None]
    if not recent:
        return season_avg, None, 0.0
    recent_avg = sum(recent) / len(recent)
    weight = FORM_MAX_WEIGHT * min(1.0, len(recent) / FORM_WINDOW)
    return (
        (1.0 - weight) * season_avg + weight * recent_avg,
        recent_avg,
        round(weight, 3),
    )


def project_player(
    usage: PlayerUsage,
    league: str,
    projected_team_points: Optional[float],
    *,
    opponent_abbr: str = "",
    logs: Optional[dict] = None,
) -> list[PropProjection]:
    """
    Every publishable market for one player. Empty when usage is too thin.

    `logs` maps a market to the player's game-by-game values for it, oldest
    first. Where one is present it does three things the season average alone
    cannot: it supplies recent form, it supplies the player's own spread for
    the over/under probability, and it is the evidence a reader can check.
    """
    logs = logs or {}

    # An actual box-score line is reported as-is: it already happened, so there
    # is nothing to project and nothing to scale.
    if usage.actual:
        env_mult = 1.0
        opp_mult, opp_note = 1.0, ""
    else:
        if usage.games_played and usage.games_played < MIN_GAMES:
            return []
        env_mult = environment_multiplier(league, projected_team_points)
        opp_mult, opp_note = opponent_multiplier(league, opponent_abbr)

    out: list[PropProjection] = []
    for market, season_avg in _fields_for(usage):
        if season_avg is None or season_avg <= 0:
            continue

        log = logs.get(market) or []
        samples = [g.value for g in log]

        if usage.actual:
            base, recent_avg, form_weight = season_avg, None, 0.0
        else:
            base, recent_avg, form_weight = _form_blend(season_avg, samples)

        projection = round(base * env_mult * opp_mult, 1)
        if projection < _MIN_PUBLISHABLE.get(market, 0.0):
            continue

        sigma, sigma_source, sigma_games = sigma_for(projection, market, samples)
        out.append(PropProjection(  # noqa: E501 — field list reads better long
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
            recent_avg=round(recent_avg, 1) if recent_avg is not None else None,
            form_weight=form_weight,
            sigma=round(sigma, 2) if sigma is not None else None,
            sigma_source=sigma_source,
            sigma_games=sigma_games,
            environment_mult=round(env_mult, 3),
            opponent_mult=round(opp_mult, 3),
            opponent_abbr=opponent_abbr,
            opponent_note=opp_note,
            game_log=[
                {"season": g.season, "week": g.week,
                 "opponent": g.opponent, "value": g.value}
                for g in log
            ],
        ))

    atd = _anytime_td(usage, logs, env_mult, opp_mult, opp_note, opponent_abbr)
    if atd is not None:
        out.append(atd)
    return out


def _anytime_td(
    usage: PlayerUsage, logs: dict, env_mult: float, opp_mult: float,
    opp_note: str, opponent_abbr: str,
) -> Optional[PropProjection]:
    """
    The player's chance of scoring at all, as its own market.

    Built from the combined rushing and receiving touchdown log where there is
    one, and from the published per-game rates otherwise. A quarterback is
    included because he can run one in; his passing touchdowns are not, because
    he does not score those.

    An actual is left alone: once the game is under way "did he score" is a
    fact on the scoreboard, not a probability.
    """
    log = logs.get(ANYTIME_TD) or []
    samples = [g.value for g in log]

    if not samples:
        # No weekly log — fall back to the published per-game rates, repeated
        # across the games they were measured over, which is the same
        # information in the shape the shrinkage expects.
        rate = (usage.rush_tds_pg or 0.0) + (usage.rec_tds_pg or 0.0)
        games = max(int(usage.games_played or 0), 0)
        if rate <= 0 or games <= 0:
            return None
        samples = [rate] * games

    rate = anytime_td_rate(samples)
    probability = anytime_td_probability(samples)
    if rate is None or probability is None or rate < ATD_MIN_RATE:
        return None

    if usage.actual:
        scored = sum(samples[-1:]) if log else 0.0
        return PropProjection(
            athlete_id=usage.athlete_id, player=usage.name,
            team_abbr=usage.team_abbr, position=usage.position,
            market=ANYTIME_TD, label=MARKET_LABELS[ANYTIME_TD],
            projection=round(scored, 1), season_avg=round(rate, 2),
            games_played=usage.games_played, actual=True,
        )

    # Touchdown rate responds to the same two things a yardage line does: how
    # busy the offence is projected to be, and who it is facing.
    adjusted = [v * env_mult * opp_mult for v in samples]
    rate = anytime_td_rate(adjusted) or rate
    probability = anytime_td_probability(adjusted) or probability

    return PropProjection(
        athlete_id=usage.athlete_id, player=usage.name,
        team_abbr=usage.team_abbr, position=usage.position,
        market=ANYTIME_TD, label=MARKET_LABELS[ANYTIME_TD],
        # The expected count, with the probability of at least one beside it.
        projection=round(rate, 2),
        season_avg=round(anytime_td_rate(samples) or rate, 2),
        games_played=usage.games_played,
        actual=False,
        yes_prob=probability,
        environment_mult=round(env_mult, 3),
        opponent_mult=round(opp_mult, 3),
        opponent_abbr=opponent_abbr,
        opponent_note=opp_note,
        sigma_games=len(samples),
        sigma_source="player" if log else "market",
        game_log=[
            {"season": g.season, "week": g.week,
             "opponent": g.opponent, "value": g.value}
            for g in log
        ],
    )


def project_game(
    players: list[PlayerUsage],
    league: str,
    home_abbr: str,
    away_abbr: str,
    home_points: Optional[float],
    away_points: Optional[float],
    logs: Optional[dict] = None,
) -> list[PropProjection]:
    """
    Projections for every player in a game, each scaled by their own team's
    projected score and by the defence they are facing.

    `logs` maps an athlete id to a per-market game log. Players with no log
    still project off their season average; they simply carry the market-wide
    spread rather than their own, and say so.
    """
    logs = logs or {}
    out: list[PropProjection] = []
    for usage in players:
        if usage.team_abbr and usage.team_abbr == home_abbr:
            team_points, opponent = home_points, away_abbr
        elif usage.team_abbr and usage.team_abbr == away_abbr:
            team_points, opponent = away_points, home_abbr
        else:
            # Unknown team — no scaling and no opponent. The season average
            # stands rather than being adjusted by a guess.
            team_points, opponent = None, ""
        out.extend(project_player(
            usage, league, team_points,
            opponent_abbr=opponent,
            logs=logs.get(usage.athlete_id) or {},
        ))

    order = {"pass_yards": 0, "rush_yards": 1, "rec_yards": 2, ANYTIME_TD: 4}
    # Anytime touchdown is ranked by its probability, not by its expected
    # count — the count is a tenth of a touchdown and sorts meaninglessly.
    out.sort(key=lambda p: (
        order.get(p.market, 3),
        -(p.yes_prob if p.yes_prob is not None else p.projection),
    ))
    return out
