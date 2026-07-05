"""
CFL teams with power ratings.

Ratings are a 2026-season prior anchored on 2025 Grey Cup form; they update
implicitly each game because predictions are always evaluated at the live
market line from the ESPN feed. Three-down football scores more than the
NFL: league average ≈ 25.2 points per team.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class CFLTeam:
    code: str
    name: str
    city: str
    division: str     # "East" | "West"
    elo: float
    flag: str = "🍁"


CFL_TEAMS: dict[str, CFLTeam] = {t.code: t for t in [
    # West Division
    CFLTeam("SSK", "Roughriders",   "Saskatchewan", "West", 1660),
    CFLTeam("WPG", "Blue Bombers",  "Winnipeg",     "West", 1620),
    CFLTeam("BC",  "Lions",         "BC",           "West", 1580),
    CFLTeam("CGY", "Stampeders",    "Calgary",      "West", 1560),
    CFLTeam("EDM", "Elks",          "Edmonton",     "West", 1500),
    # East Division
    CFLTeam("MTL", "Alouettes",     "Montreal",     "East", 1630),
    CFLTeam("HAM", "Tiger-Cats",    "Hamilton",     "East", 1590),
    CFLTeam("TOR", "Argonauts",     "Toronto",      "East", 1540),
    CFLTeam("OTT", "Redblacks",     "Ottawa",       "East", 1480),
]}

# League scoring environment (points per team per game) — higher than NFL
CFL_LEAGUE_AVG_PPG = 25.2

_OFF_COEF = 0.045
_DEF_COEF = 0.035

_STYLE_OVERRIDES: dict[str, tuple[float, float]] = {
    # code: (off_delta, def_delta) on top of the Elo-derived baseline
    "SSK": (+0.5, -1.5),   # defense won them the Grey Cup
    "WPG": (+1.0, -0.5),
    "BC":  (+1.5, +1.0),   # Rourke air show, softer defense
    "HAM": (+1.0, +0.5),
    "MTL": (+0.5, -1.0),
    "EDM": (-0.5, +1.0),
    "OTT": (-1.0, +0.5),
}


def get_cfl_team(code: str) -> CFLTeam:
    t = CFL_TEAMS.get(code.upper())
    if t is None:
        raise KeyError(f"Unknown CFL team code: {code!r}")
    return t


def get_cfl_ratings(code: str, elo: float | None = None) -> tuple[float, float]:
    """Return (offense_ppg, defense_ppg_allowed) for a CFL team.

    `elo` overrides the static prior (e.g. the self-correcting rating).
    """
    t = get_cfl_team(code)
    rating = t.elo if elo is None else elo
    off = CFL_LEAGUE_AVG_PPG + (rating - 1500) * _OFF_COEF
    dfn = CFL_LEAGUE_AVG_PPG - (rating - 1500) * _DEF_COEF
    d_off, d_def = _STYLE_OVERRIDES.get(t.code, (0.0, 0.0))
    return off + d_off, dfn + d_def


def all_cfl_teams_sorted() -> list[CFLTeam]:
    return sorted(CFL_TEAMS.values(), key=lambda t: -t.elo)
