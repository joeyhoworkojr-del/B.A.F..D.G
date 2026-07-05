"""
MLB teams with run-scoring power ratings.

Ratings calibrated to the 2025 season. League scoring environment:
~4.40 runs per team per game. Park factors scale BOTH teams' expected
runs when playing in that park (Coors inflates everything).
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class MLBTeam:
    code: str
    name: str
    city: str
    league: str       # "AL" | "NL"
    division: str     # "East" | "Central" | "West"
    elo: float
    flag: str = "⚾"


MLB_TEAMS: dict[str, MLBTeam] = {t.code: t for t in [
    # AL East
    MLBTeam("NYY", "Yankees",     "New York",      "AL", "East",    1590),
    MLBTeam("BOS", "Red Sox",     "Boston",        "AL", "East",    1545),
    MLBTeam("TOR", "Blue Jays",   "Toronto",       "AL", "East",    1560),
    MLBTeam("TB",  "Rays",        "Tampa Bay",     "AL", "East",    1520),
    MLBTeam("BAL", "Orioles",     "Baltimore",     "AL", "East",    1515),
    # AL Central
    MLBTeam("DET", "Tigers",      "Detroit",       "AL", "Central", 1575),
    MLBTeam("CLE", "Guardians",   "Cleveland",     "AL", "Central", 1540),
    MLBTeam("KC",  "Royals",      "Kansas City",   "AL", "Central", 1525),
    MLBTeam("MIN", "Twins",       "Minnesota",     "AL", "Central", 1500),
    MLBTeam("CHW", "White Sox",   "Chicago",       "AL", "Central", 1425),
    # AL West
    MLBTeam("HOU", "Astros",      "Houston",       "AL", "West",    1555),
    MLBTeam("SEA", "Mariners",    "Seattle",       "AL", "West",    1565),
    MLBTeam("TEX", "Rangers",     "Texas",         "AL", "West",    1520),
    MLBTeam("LAA", "Angels",      "Los Angeles",   "AL", "West",    1455),
    MLBTeam("ATH", "Athletics",   "Sacramento",    "AL", "West",    1470),
    # NL East
    MLBTeam("PHI", "Phillies",    "Philadelphia",  "NL", "East",    1585),
    MLBTeam("NYM", "Mets",        "New York",      "NL", "East",    1570),
    MLBTeam("ATL", "Braves",      "Atlanta",       "NL", "East",    1540),
    MLBTeam("WSH", "Nationals",   "Washington",    "NL", "East",    1465),
    MLBTeam("MIA", "Marlins",     "Miami",         "NL", "East",    1460),
    # NL Central
    MLBTeam("MIL", "Brewers",     "Milwaukee",     "NL", "Central", 1580),
    MLBTeam("CHC", "Cubs",        "Chicago",       "NL", "Central", 1565),
    MLBTeam("STL", "Cardinals",   "St. Louis",     "NL", "Central", 1505),
    MLBTeam("CIN", "Reds",        "Cincinnati",    "NL", "Central", 1510),
    MLBTeam("PIT", "Pirates",     "Pittsburgh",    "NL", "Central", 1470),
    # NL West
    MLBTeam("LAD", "Dodgers",     "Los Angeles",   "NL", "West",    1625),
    MLBTeam("SD",  "Padres",      "San Diego",     "NL", "West",    1570),
    MLBTeam("SF",  "Giants",      "San Francisco", "NL", "West",    1525),
    MLBTeam("ARI", "Diamondbacks","Arizona",       "NL", "West",    1530),
    MLBTeam("COL", "Rockies",     "Colorado",      "NL", "West",    1400),
]}

# League scoring environment (runs per team per game)
MLB_LEAGUE_AVG_RPG = 4.40

_OFF_COEF = 0.0045   # runs of offense per Elo point above 1500
_DEF_COEF = 0.0035

_STYLE_OVERRIDES: dict[str, tuple[float, float]] = {
    # code: (off_delta, def_delta) — runs per game vs the Elo baseline
    "LAD": (+0.30, -0.10),
    "NYY": (+0.35, +0.10),   # bombers: hit a ton, pitching merely good
    "MIL": (-0.15, -0.35),   # run prevention first
    "DET": (-0.10, -0.30),   # Skubal and friends
    "PHI": (+0.10, -0.15),
    "SEA": (-0.20, -0.30),   # pitcher's park, elite rotation
    "COL": (+0.10, +0.55),   # bad pitching amplified by altitude
    "CHW": (-0.30, +0.30),
    "ATL": (+0.15, +0.05),
    "BOS": (+0.20, +0.10),
}

# Park factor: multiplies BOTH teams' expected runs at that home park
PARK_FACTORS: dict[str, float] = {
    "COL": 1.24,   # Coors Field
    "CIN": 1.08,
    "BOS": 1.06,
    "TEX": 1.03,
    "ARI": 1.03,
    "NYY": 1.02,
    "SEA": 0.92,   # T-Mobile Park
    "SF":  0.94,
    "SD":  0.95,
    "NYM": 0.96,
    "TB":  0.96,
    "MIA": 0.96,
    "STL": 0.97,
}


def get_mlb_team(code: str) -> MLBTeam:
    t = MLB_TEAMS.get(code.upper())
    if t is None:
        raise KeyError(f"Unknown MLB team code: {code!r}")
    return t


def get_mlb_ratings(code: str, elo: float | None = None) -> tuple[float, float]:
    """Return (runs_scored_pg, runs_allowed_pg) vs league-average opposition.

    `elo` overrides the static prior (e.g. the self-correcting rating).
    """
    t = get_mlb_team(code)
    rating = t.elo if elo is None else elo
    off = MLB_LEAGUE_AVG_RPG + (rating - 1500) * _OFF_COEF
    dfn = MLB_LEAGUE_AVG_RPG - (rating - 1500) * _DEF_COEF
    d_off, d_def = _STYLE_OVERRIDES.get(t.code, (0.0, 0.0))
    return off + d_off, dfn + d_def


def get_park_factor(home_code: str) -> float:
    return PARK_FACTORS.get(home_code.upper(), 1.0)


def all_mlb_teams_sorted() -> list[MLBTeam]:
    return sorted(MLB_TEAMS.values(), key=lambda t: -t.elo)
