"""
NFL teams with Elo-based power ratings.
Ratings calibrated to end-of-2025 season standings.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class NFLTeam:
    code: str
    name: str
    city: str
    conference: str   # "AFC" | "NFC"
    division: str     # "North" | "South" | "East" | "West"
    elo: float
    flag: str = "🏈"


NFL_TEAMS: dict[str, NFLTeam] = {t.code: t for t in [
    # AFC North
    NFLTeam("BAL", "Ravens",    "Baltimore",   "AFC", "North", 1680),
    NFLTeam("CIN", "Bengals",   "Cincinnati",  "AFC", "North", 1560),
    NFLTeam("CLE", "Browns",    "Cleveland",   "AFC", "North", 1480),
    NFLTeam("PIT", "Steelers",  "Pittsburgh",  "AFC", "North", 1550),
    # AFC South
    NFLTeam("HOU", "Texans",    "Houston",     "AFC", "South", 1600),
    NFLTeam("IND", "Colts",     "Indianapolis","AFC", "South", 1510),
    NFLTeam("JAX", "Jaguars",   "Jacksonville","AFC", "South", 1490),
    NFLTeam("TEN", "Titans",    "Tennessee",   "AFC", "South", 1460),
    # AFC East
    NFLTeam("BUF", "Bills",     "Buffalo",     "AFC", "East",  1660),
    NFLTeam("MIA", "Dolphins",  "Miami",       "AFC", "East",  1580),
    NFLTeam("NE",  "Patriots",  "New England", "AFC", "East",  1470),
    NFLTeam("NYJ", "Jets",      "New York",    "AFC", "East",  1490),
    # AFC West
    NFLTeam("KC",  "Chiefs",    "Kansas City", "AFC", "West",  1720),
    NFLTeam("LAC", "Chargers",  "Los Angeles", "AFC", "West",  1540),
    NFLTeam("LV",  "Raiders",   "Las Vegas",   "AFC", "West",  1470),
    NFLTeam("DEN", "Broncos",   "Denver",      "AFC", "West",  1510),
    # NFC North
    NFLTeam("CHI", "Bears",     "Chicago",     "NFC", "North", 1520),
    NFLTeam("DET", "Lions",     "Detroit",     "NFC", "North", 1650),
    NFLTeam("GB",  "Packers",   "Green Bay",   "NFC", "North", 1590),
    NFLTeam("MIN", "Vikings",   "Minnesota",   "NFC", "North", 1570),
    # NFC South
    NFLTeam("ATL", "Falcons",   "Atlanta",     "NFC", "South", 1530),
    NFLTeam("CAR", "Panthers",  "Carolina",    "NFC", "South", 1430),
    NFLTeam("NO",  "Saints",    "New Orleans", "NFC", "South", 1510),
    NFLTeam("TB",  "Buccaneers","Tampa Bay",   "NFC", "South", 1560),
    # NFC East
    NFLTeam("DAL", "Cowboys",   "Dallas",      "NFC", "East",  1600),
    NFLTeam("NYG", "Giants",    "New York",    "NFC", "East",  1450),
    NFLTeam("PHI", "Eagles",    "Philadelphia","NFC", "East",  1640),
    NFLTeam("WSH", "Commanders","Washington",  "NFC", "East",  1530),
    # NFC West
    NFLTeam("ARI", "Cardinals", "Arizona",     "NFC", "West",  1470),
    NFLTeam("LA",  "Rams",      "Los Angeles", "NFC", "West",  1590),
    NFLTeam("SF",  "49ers",     "San Francisco","NFC","West",  1680),
    NFLTeam("SEA", "Seahawks",  "Seattle",     "NFC", "West",  1540),
]}

# Home-field advantage in Elo points
NFL_HOME_EDGE = 48.0

# League scoring environment (points per team per game)
LEAGUE_AVG_PPG = 22.3

# ─── Offense / defense point ratings ─────────────────────────────────────────
# off = expected points scored per game vs an average defense.
# def = expected points allowed per game vs an average offense (lower = better).
# Defaults derive from Elo; overrides capture style (e.g. a team can be good
# via defense with a mediocre offense). These drive matchup-specific totals.

_OFF_COEF = 0.045   # points of offense per Elo point above 1500
_DEF_COEF = 0.035   # points of defense per Elo point above 1500
# (off+def)/2 per Elo point = 0.04 → margin ≈ elo_diff / 25, the standard scale

_STYLE_OVERRIDES: dict[str, tuple[float, float]] = {
    # code: (off_delta, def_delta) applied on top of the Elo-derived baseline
    "BAL": (+0.5, -1.5),   # elite defense
    "DET": (+2.5, +1.5),   # high-powered offense, leaky defense
    "KC":  (+1.0, -0.5),
    "SF":  (+0.5, -1.0),
    "BUF": (+1.5, +0.5),
    "PIT": (-1.5, -1.5),   # defense-first, low-scoring
    "CLE": (-2.0, -1.0),
    "NYJ": (-1.5, -1.0),
    "MIA": (+1.5, +1.0),   # fast offense, soft defense
    "CIN": (+1.5, +1.0),
    "PHI": (+0.5, -0.5),
    "GB":  (+1.0, +0.5),
    "DAL": (+1.0, +0.5),
    "NE":  (-1.5, -0.5),
    "DEN": (-0.5, -1.0),
    "CAR": (-1.0, +1.0),
}


def get_nfl_ratings(code: str, elo: float | None = None) -> tuple[float, float]:
    """Return (offense_ppg, defense_ppg_allowed) for a team.

    `elo` overrides the static prior (e.g. the self-correcting rating).
    """
    t = get_nfl_team(code)
    rating = t.elo if elo is None else elo
    off = LEAGUE_AVG_PPG + (rating - 1500) * _OFF_COEF
    dfn = LEAGUE_AVG_PPG - (rating - 1500) * _DEF_COEF
    d_off, d_def = _STYLE_OVERRIDES.get(t.code, (0.0, 0.0))
    return off + d_off, dfn + d_def


def get_nfl_team(code: str) -> NFLTeam:
    t = NFL_TEAMS.get(code.upper())
    if t is None:
        raise KeyError(f"Unknown NFL team code: {code!r}")
    return t


def all_nfl_teams_sorted() -> list[NFLTeam]:
    return sorted(NFL_TEAMS.values(), key=lambda t: -t.elo)
