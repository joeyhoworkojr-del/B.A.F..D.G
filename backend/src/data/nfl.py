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


def get_nfl_team(code: str) -> NFLTeam:
    t = NFL_TEAMS.get(code.upper())
    if t is None:
        raise KeyError(f"Unknown NFL team code: {code!r}")
    return t


def all_nfl_teams_sorted() -> list[NFLTeam]:
    return sorted(NFL_TEAMS.values(), key=lambda t: -t.elo)
