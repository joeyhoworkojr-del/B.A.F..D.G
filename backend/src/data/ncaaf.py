"""
NCAA FBS college football teams with Elo-based power ratings.

College football has ~135 FBS teams and enormous talent gaps, so hand-maintained
priors can never cover the whole board accurately. This module therefore does
two things:

  1. Seeds the well-known programs with sensible Elo priors (blue bloods high,
     Group-of-5 lower) so ranked matchups and no-line games have a real prior.
  2. Falls back to a neutral baseline for any team ESPN returns that we don't
     recognise — `get_ncaaf_team()` never raises. In the live model those
     unknown teams are anchored to the market line (see the ncaaf branch in the
     slate scanner), which is the sharpest available estimate anyway.

The result is a *market-first* college model: the betting line is the backbone,
static priors fill in when there's no line, and the self-correcting ratings
sharpen everything as real results land.
"""
from __future__ import annotations

from dataclasses import dataclass

# FBS scoring environment: more possessions and points than the NFL.
LEAGUE_AVG_PPG = 27.5
NCAAF_HOME_EDGE = 55.0   # Elo points — college home field is worth more

DEFAULT_ELO = 1475.0     # unknown / Group-of-5 baseline


@dataclass(frozen=True)
class NCAAFTeam:
    code: str
    name: str
    conference: str
    elo: float
    flag: str = "🏈"


# ESPN-style abbreviations. Priors are rough season-open power ratings; the
# self-correcting module reconciles them against real results as games grade.
NCAAF_TEAMS: dict[str, NCAAFTeam] = {t.code: t for t in [
    # National title contenders / blue bloods
    NCAAFTeam("GA",   "Georgia",         "SEC",      1920),
    NCAAFTeam("OSU",  "Ohio State",      "Big Ten",  1910),
    NCAAFTeam("TEX",  "Texas",           "SEC",      1895),
    NCAAFTeam("ORE",  "Oregon",          "Big Ten",  1885),
    NCAAFTeam("ALA",  "Alabama",         "SEC",      1875),
    NCAAFTeam("PSU",  "Penn State",      "Big Ten",  1860),
    NCAAFTeam("ND",   "Notre Dame",      "Ind",      1855),
    NCAAFTeam("MICH", "Michigan",        "Big Ten",  1830),
    NCAAFTeam("LSU",  "LSU",             "SEC",      1825),
    NCAAFTeam("CLEM", "Clemson",         "ACC",      1820),
    NCAAFTeam("TENN", "Tennessee",       "SEC",      1800),
    NCAAFTeam("MISS", "Ole Miss",        "SEC",      1790),
    NCAAFTeam("USC",  "USC",             "Big Ten",  1775),
    NCAAFTeam("MIA",  "Miami",           "ACC",      1770),
    NCAAFTeam("OU",   "Oklahoma",        "SEC",      1765),
    NCAAFTeam("FSU",  "Florida State",   "ACC",      1720),
    NCAAFTeam("UGA",  "Georgia",         "SEC",      1920),   # alt abbr
    # Strong programs
    NCAAFTeam("UTAH", "Utah",            "Big 12",   1710),
    NCAAFTeam("KSU",  "Kansas State",    "Big 12",   1705),
    NCAAFTeam("MO",   "Missouri",        "SEC",      1700),
    NCAAFTeam("SC",   "South Carolina",  "SEC",      1695),
    NCAAFTeam("TAMU", "Texas A&M",       "SEC",      1690),
    NCAAFTeam("IOWA", "Iowa",            "Big Ten",  1685),
    NCAAFTeam("WISC", "Wisconsin",       "Big Ten",  1660),
    NCAAFTeam("KU",   "Kansas",          "Big 12",   1655),
    NCAAFTeam("OKST", "Oklahoma State",  "Big 12",   1650),
    NCAAFTeam("TCU",  "TCU",             "Big 12",   1645),
    NCAAFTeam("LOU",  "Louisville",      "ACC",      1640),
    NCAAFTeam("UNC",  "North Carolina",  "ACC",      1600),
    NCAAFTeam("NCST", "NC State",        "ACC",      1610),
    NCAAFTeam("WVU",  "West Virginia",   "Big 12",   1605),
    NCAAFTeam("BAY",  "Baylor",          "Big 12",   1600),
    NCAAFTeam("ARK",  "Arkansas",        "SEC",      1615),
    NCAAFTeam("AUB",  "Auburn",          "SEC",      1620),
    NCAAFTeam("FLA",  "Florida",         "SEC",      1630),
    NCAAFTeam("NEB",  "Nebraska",        "Big Ten",  1600),
    NCAAFTeam("WASH", "Washington",      "Big Ten",  1670),
    NCAAFTeam("UCLA", "UCLA",            "Big Ten",  1560),
    NCAAFTeam("CAL",  "California",       "ACC",      1545),
    NCAAFTeam("PITT", "Pittsburgh",      "ACC",      1560),
    NCAAFTeam("VT",   "Virginia Tech",   "ACC",      1555),
    NCAAFTeam("TTU",  "Texas Tech",      "Big 12",   1640),
    NCAAFTeam("ILL",  "Illinois",        "Big Ten",  1640),
    NCAAFTeam("IU",   "Indiana",         "Big Ten",  1700),
    NCAAFTeam("MINN", "Minnesota",       "Big Ten",  1600),
    NCAAFTeam("DUKE", "Duke",            "ACC",      1560),
    NCAAFTeam("GT",   "Georgia Tech",    "ACC",      1580),
    NCAAFTeam("SMU",  "SMU",             "ACC",      1620),
    # Group of 5 risers
    NCAAFTeam("BOIS", "Boise State",     "MWC",      1600),
    NCAAFTeam("BSU",  "Boise State",     "MWC",      1600),
    NCAAFTeam("MEM",  "Memphis",         "AAC",      1520),
    NCAAFTeam("TULN", "Tulane",          "AAC",      1530),
    NCAAFTeam("UNLV", "UNLV",            "MWC",      1500),
    NCAAFTeam("HAW",  "Hawai'i",         "MWC",      1420),
    NCAAFTeam("LT",   "Louisiana Tech",  "CUSA",     1420),
    NCAAFTeam("WKU",  "Western Kentucky","CUSA",     1450),
    NCAAFTeam("NEV",  "Nevada",          "MWC",      1440),
    NCAAFTeam("CMU",  "Central Michigan","MAC",      1440),
    NCAAFTeam("UNM",  "New Mexico",      "MWC",      1440),
    NCAAFTeam("JMU",  "James Madison",   "SBC",      1560),
]}

# off = expected points scored vs an average defense; def = points allowed vs an
# average offense (lower = better). Symmetric coefficients keep the standard
# scale: margin ≈ elo_diff / 25.
_OFF_COEF = 0.050
_DEF_COEF = 0.030


def get_ncaaf_team(code: str) -> NCAAFTeam:
    """Return a team, synthesising a neutral-baseline team for unknown codes.

    Never raises — the college board is far too large to enumerate, and unknown
    teams are carried by the market line in the live model.
    """
    t = NCAAF_TEAMS.get(code.upper())
    if t is not None:
        return t
    return NCAAFTeam(code=code.upper(), name=code.upper(), conference="", elo=DEFAULT_ELO)


def get_ncaaf_ratings(code: str, elo: float | None = None) -> tuple[float, float]:
    """Return (offense_ppg, defense_ppg_allowed) for a team.

    `elo` overrides the static prior (e.g. the self-correcting rating).
    """
    t = get_ncaaf_team(code)
    rating = t.elo if elo is None else elo
    off = LEAGUE_AVG_PPG + (rating - 1500) * _OFF_COEF
    dfn = LEAGUE_AVG_PPG - (rating - 1500) * _DEF_COEF
    return off, dfn


def all_ncaaf_teams_sorted() -> list[NCAAFTeam]:
    return sorted(NCAAF_TEAMS.values(), key=lambda t: -t.elo)
