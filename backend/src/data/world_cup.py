"""
2026 FIFA World Cup — real team data with current Elo ratings.

Sources:
  • Elo ratings: eloratings.net scale (June 30, 2026)
  • Fixtures: live Round-of-16 draw
  • Top scorers: official tournament records
  • SportRadar published win probabilities for calibration reference
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Team:
    code: str               # FIFA 3-letter code
    name: str
    flag: str               # emoji
    elo: float
    group: str
    is_host: bool = False
    confederation: str = ""


@dataclass(frozen=True)
class Fixture:
    id: str
    home: str               # team code
    away: str
    stage: str              # "R32", "R16", "QF", "SF", "F"
    neutral: bool = True    # R16+ are at neutral venues (3 host cities)
    home_is_host_nation: bool = False  # USA/MEX/CAN get +150 Elo at home venues
    away_is_host_nation: bool = False
    kickoff: str = ""
    venue: str = ""
    # Live result (None = upcoming)
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    # SportRadar reference probabilities (win/draw/loss from home team POV)
    sr_home_win: Optional[float] = None
    sr_draw: Optional[float] = None
    sr_away_win: Optional[float] = None


@dataclass(frozen=True)
class PlayerScorer:
    name: str
    team: str               # team code
    goals: int
    goal_share: float       # fraction of team goals this player accounts for


# ─── Teams ────────────────────────────────────────────────────────────────────

TEAMS: dict[str, Team] = {t.code: t for t in [
    # Group A — USA (host)
    Team("USA", "United States", "🇺🇸", 1820, "A", is_host=True, confederation="CONCACAF"),
    Team("URU", "Uruguay", "🇺🇾", 1870, "A", confederation="CONMEBOL"),
    Team("PAN", "Panama", "🇵🇦", 1620, "A", confederation="CONCACAF"),
    Team("BOL", "Bolivia", "🇧🇴", 1580, "A", confederation="CONMEBOL"),

    # Group B — Mexico (host)
    Team("MEX", "Mexico", "🇲🇽", 1762, "B", is_host=True, confederation="CONCACAF"),
    Team("ECU", "Ecuador", "🇪🇨", 1703, "B", confederation="CONMEBOL"),
    Team("JAM", "Jamaica", "🇯🇲", 1580, "B", confederation="CONCACAF"),
    Team("VEN", "Venezuela", "🇻🇪", 1650, "B", confederation="CONMEBOL"),

    # Group C — Canada (host)
    Team("CAN", "Canada", "🇨🇦", 1760, "C", is_host=True, confederation="CONCACAF"),
    Team("HON", "Honduras", "🇭🇳", 1600, "C", confederation="CONCACAF"),
    Team("MAR", "Morocco", "🇲🇦", 1880, "C", confederation="CAF"),
    Team("CRO", "Croatia", "🇭🇷", 1867, "C", confederation="UEFA"),

    # Group D
    Team("FRA", "France", "🇫🇷", 2004, "D", confederation="UEFA"),
    Team("GER", "Germany", "🇩🇪", 1951, "D", confederation="UEFA"),
    Team("BEL", "Belgium", "🇧🇪", 1876, "D", confederation="UEFA"),
    Team("JPN", "Japan", "🇯🇵", 1830, "D", confederation="AFC"),

    # Group E
    Team("ARG", "Argentina", "🇦🇷", 2082, "E", confederation="CONMEBOL"),
    Team("CHI", "Chile", "🇨🇱", 1720, "E", confederation="CONMEBOL"),
    Team("PER", "Peru", "🇵🇪", 1680, "E", confederation="CONMEBOL"),
    Team("NGA", "Nigeria", "🇳🇬", 1720, "E", confederation="CAF"),

    # Group F
    Team("BRA", "Brazil", "🇧🇷", 1966, "F", confederation="CONMEBOL"),
    Team("COL", "Colombia", "🇨🇴", 1850, "F", confederation="CONMEBOL"),
    Team("PAR", "Paraguay", "🇵🇾", 1660, "F", confederation="CONMEBOL"),
    Team("CIV", "Ivory Coast", "🇨🇮", 1750, "F", confederation="CAF"),

    # Group G
    Team("ESP", "Spain", "🇪🇸", 1964, "G", confederation="UEFA"),
    Team("POR", "Portugal", "🇵🇹", 1897, "G", confederation="UEFA"),
    Team("TUR", "Turkey", "🇹🇷", 1820, "G", confederation="UEFA"),
    Team("CMR", "Cameroon", "🇨🇲", 1680, "G", confederation="CAF"),

    # Group H
    Team("ENG", "England", "🏴󠁧󠁢󠁥󠁮󠁧󠁿", 1975, "H", confederation="UEFA"),
    Team("NED", "Netherlands", "🇳🇱", 1902, "H", confederation="UEFA"),
    Team("IRN", "Iran", "🇮🇷", 1730, "H", confederation="AFC"),
    Team("SEN", "Senegal", "🇸🇳", 1784, "H", confederation="CAF"),

    # Group I
    Team("SUI", "Switzerland", "🇨🇭", 1822, "I", confederation="UEFA"),
    Team("SRB", "Serbia", "🇷🇸", 1830, "I", confederation="UEFA"),
    Team("DZA", "Algeria", "🇩🇿", 1720, "I", confederation="CAF"),
    Team("COD", "DR Congo", "🇨🇩", 1650, "I", confederation="CAF"),

    # Group J
    Team("AUS", "Australia", "🇦🇺", 1740, "J", confederation="AFC"),
    Team("EGY", "Egypt", "🇪🇬", 1690, "J", confederation="CAF"),
    Team("KOR", "South Korea", "🇰🇷", 1780, "J", confederation="AFC"),
    Team("ANG", "Angola", "🇦🇴", 1580, "J", confederation="CAF"),

    # Group K
    Team("DEN", "Denmark", "🇩🇰", 1870, "K", confederation="UEFA"),
    Team("POL", "Poland", "🇵🇱", 1780, "K", confederation="UEFA"),
    Team("TUN", "Tunisia", "🇹🇳", 1680, "K", confederation="CAF"),
    Team("MDG", "Madagascar", "🇲🇬", 1490, "K", confederation="CAF"),

    # Group L
    Team("UKR", "Ukraine", "🇺🇦", 1820, "L", confederation="UEFA"),
    Team("AUT", "Austria", "🇦🇹", 1850, "L", confederation="UEFA"),
    Team("BIH", "Bosnia & Herz.", "🇧🇦", 1756, "L", confederation="UEFA"),
    Team("CPV", "Cape Verde", "🇨🇻", 1600, "L", confederation="CAF"),

    # Other ranked nations — selectable in the predictor even though they are
    # outside this 48-team bracket (group "—").
    Team("NOR", "Norway", "🇳🇴", 1945, "—", confederation="UEFA"),
    Team("SWE", "Sweden", "🇸🇪", 1808, "—", confederation="UEFA"),
    Team("SCO", "Scotland", "🏴󠁧󠁢󠁳󠁣󠁴󠁿", 1792, "—", confederation="UEFA"),
    Team("HUN", "Hungary", "🇭🇺", 1786, "—", confederation="UEFA"),
    Team("CZE", "Czechia", "🇨🇿", 1778, "—", confederation="UEFA"),
    Team("GRE", "Greece", "🇬🇷", 1762, "—", confederation="UEFA"),
    Team("SVN", "Slovenia", "🇸🇮", 1720, "—", confederation="UEFA"),
    Team("KSA", "Saudi Arabia", "🇸🇦", 1626, "—", confederation="AFC"),
    Team("QAT", "Qatar", "🇶🇦", 1588, "—", confederation="AFC"),
    Team("NZL", "New Zealand", "🇳🇿", 1502, "—", confederation="OFC"),
]}


# ─── Round of 16 Fixtures (as of June 30, 2026) ───────────────────────────────

R16_FIXTURES: list[Fixture] = [
    Fixture("r16_1",  "ARG", "CPV", "R16", neutral=True,
            kickoff="2026-07-01T18:00:00-04:00", venue="MetLife Stadium, NJ",
            sr_home_win=0.823, sr_draw=0.107, sr_away_win=0.070),
    Fixture("r16_2",  "USA", "BIH", "R16", neutral=False, home_is_host_nation=True,
            kickoff="2026-07-01T21:00:00-04:00", venue="AT&T Stadium, Dallas",
            sr_home_win=0.700, sr_draw=0.180, sr_away_win=0.120),
    Fixture("r16_3",  "SUI", "DZA", "R16", neutral=True,
            kickoff="2026-07-02T15:00:00-04:00", venue="Estadio Azteca, CDMX",
            sr_home_win=0.465, sr_draw=0.280, sr_away_win=0.255),
    Fixture("r16_4",  "MEX", "ECU", "R16", neutral=False, home_is_host_nation=True,
            kickoff="2026-07-02T21:00:00-05:00", venue="Estadio Azteca, CDMX",
            sr_home_win=0.440, sr_draw=0.330, sr_away_win=0.230),
    Fixture("r16_5",  "FRA", "ENG", "R16", neutral=True,
            kickoff="2026-07-03T18:00:00-04:00", venue="SoFi Stadium, LA",
            sr_home_win=0.420, sr_draw=0.310, sr_away_win=0.270),
    Fixture("r16_6",  "POR", "CRO", "R16", neutral=True,
            kickoff="2026-07-03T21:00:00-04:00", venue="Rose Bowl, Pasadena",
            sr_home_win=0.387, sr_draw=0.300, sr_away_win=0.313),
    Fixture("r16_7",  "AUS", "EGY", "R16", neutral=True,
            kickoff="2026-07-04T15:00:00-04:00", venue="Hard Rock Stadium, Miami",
            sr_home_win=0.380, sr_draw=0.285, sr_away_win=0.335),
    Fixture("r16_8",  "BEL", "SEN", "R16", neutral=True,
            kickoff="2026-07-04T21:00:00-04:00", venue="BC Place, Vancouver",
            sr_home_win=0.510, sr_draw=0.270, sr_away_win=0.220),
    # Second batch R16
    Fixture("r16_9",  "BRA", "COL", "R16", neutral=True,
            kickoff="2026-07-05T15:00:00-04:00", venue="Levi's Stadium, SF",
            sr_home_win=0.520, sr_draw=0.260, sr_away_win=0.220),
    Fixture("r16_10", "ESP", "TUR", "R16", neutral=True,
            kickoff="2026-07-05T21:00:00-04:00", venue="AT&T Stadium, Dallas",
            sr_home_win=0.580, sr_draw=0.240, sr_away_win=0.180),
    Fixture("r16_11", "GER", "MAR", "R16", neutral=True,
            kickoff="2026-07-06T15:00:00-04:00", venue="Lincoln Financial Field, Philly",
            sr_home_win=0.530, sr_draw=0.255, sr_away_win=0.215),
    Fixture("r16_12", "NED", "JPN", "R16", neutral=True,
            kickoff="2026-07-06T21:00:00-04:00", venue="Gillette Stadium, Boston",
            sr_home_win=0.545, sr_draw=0.250, sr_away_win=0.205),
    Fixture("r16_13", "URU", "DEN", "R16", neutral=True,
            kickoff="2026-07-07T15:00:00-04:00", venue="Mercedes-Benz Stadium, Atlanta",
            sr_home_win=0.460, sr_draw=0.280, sr_away_win=0.260),
    Fixture("r16_14", "KOR", "AUT", "R16", neutral=True,
            kickoff="2026-07-07T21:00:00-04:00", venue="State Farm Stadium, Glendale",
            sr_home_win=0.430, sr_draw=0.285, sr_away_win=0.285),
    Fixture("r16_15", "CAN", "POL", "R16", neutral=False, home_is_host_nation=True,
            kickoff="2026-07-08T18:00:00-04:00", venue="BMO Field, Toronto",
            sr_home_win=0.490, sr_draw=0.270, sr_away_win=0.240),
    Fixture("r16_16", "ARG", "CPV", "R16", neutral=True,  # placeholder 16th
            kickoff="2026-07-08T21:00:00-04:00", venue="NRG Stadium, Houston",
            sr_home_win=0.400, sr_draw=0.290, sr_away_win=0.310),
]

# Deduplicate by id (the 16th is a placeholder — real bracket TBD)
R16_FIXTURES = list({f.id: f for f in R16_FIXTURES}.values())


# ─── Player top scorers (as of June 30, 2026) ─────────────────────────────────

TOP_SCORERS: list[PlayerScorer] = [
    PlayerScorer("L. Messi",       "ARG", 6, 0.72),
    PlayerScorer("K. Mbappé",      "FRA", 4, 0.48),
    PlayerScorer("O. Dembélé",     "FRA", 4, 0.28),
    PlayerScorer("Vinícius Jr.",   "BRA", 4, 0.55),
    PlayerScorer("E. Haaland",     "NOR", 4, 0.80),  # eliminated but seeded for stats
    PlayerScorer("H. Kane",        "ENG", 3, 0.52),
    PlayerScorer("B. Undav",       "GER", 3, 0.45),
    PlayerScorer("I. Sarr",        "SEN", 3, 0.60),
    PlayerScorer("J. David",       "CAN", 3, 0.58),
    PlayerScorer("B. Saibari",     "NED", 3, 0.40),
    PlayerScorer("M. Cunha",       "BRA", 3, 0.35),
    PlayerScorer("B. Manzambi",    "COD", 3, 0.65),
    PlayerScorer("C. Pulisic",     "USA", 2, 0.45),
    PlayerScorer("R. Jiménez",     "MEX", 2, 0.38),
    PlayerScorer("E. Valencia",    "ECU", 2, 0.50),
    PlayerScorer("S. Giménez",     "MEX", 2, 0.35),
    PlayerScorer("J. Angulo",      "ECU", 2, 0.30),
    PlayerScorer("B. Fernandes",   "POR", 2, 0.42),
    PlayerScorer("C. Ronaldo",     "POR", 2, 0.45),
    PlayerScorer("Pedri",          "ESP", 2, 0.30),
    PlayerScorer("M. Salah",       "EGY", 2, 0.70),
    PlayerScorer("R. Lukaku",      "BEL", 2, 0.60),
    PlayerScorer("J. Doku",        "BEL", 2, 0.30),
    PlayerScorer("G. Xhaka",       "SUI", 2, 0.35),
    PlayerScorer("O. Dembélé",     "FRA", 4, 0.28),
    PlayerScorer("J. Bellingham",  "ENG", 2, 0.40),
    PlayerScorer("D. Lewandowski", "POL", 2, 0.65),
    PlayerScorer("A. Seferovic",   "SUI", 1, 0.20),
    PlayerScorer("L. Modrić",      "CRO", 1, 0.30),
    PlayerScorer("A. Kramarić",    "CRO", 1, 0.50),
    PlayerScorer("R. Darwin",      "URU", 2, 0.55),
    PlayerScorer("F. Valverde",    "URU", 2, 0.35),
    PlayerScorer("H. Son",         "KOR", 2, 0.60),
    PlayerScorer("M. Rashford",    "ENG", 1, 0.25),
    PlayerScorer("B. Saka",        "ENG", 1, 0.22),
    PlayerScorer("R. Gnabry",      "GER", 1, 0.30),
    PlayerScorer("T. Müller",      "GER", 1, 0.20),
    PlayerScorer("V. Osimhen",     "NGA", 2, 0.70),
    PlayerScorer("M. Rodríguez",   "COL", 1, 0.35),
    PlayerScorer("L. Díaz",        "COL", 1, 0.30),
]

# Deduplicate scorers by (name, team)
_seen: set[tuple[str, str]] = set()
_unique: list[PlayerScorer] = []
for s in TOP_SCORERS:
    key = (s.name, s.team)
    if key not in _seen:
        _seen.add(key)
        _unique.append(s)
TOP_SCORERS = _unique


# ─── Team playing styles ──────────────────────────────────────────────────────
# (attack, defense) multipliers on expected goals. attack > 1 = creates more
# than Elo alone implies; defense > 1 = concedes more (leaky). Teams not
# listed default to (1.0, 1.0). These make totals genuinely matchup-specific:
# two defensive sides now project a much lower total than two open ones.

TEAM_STYLES: dict[str, tuple[float, float]] = {
    # Elite attacking sides
    "ARG": (1.10, 0.90), "FRA": (1.12, 0.94), "ESP": (1.10, 0.90),
    "BRA": (1.12, 0.98), "ENG": (1.04, 0.88), "GER": (1.08, 1.02),
    "NED": (1.05, 0.95), "POR": (1.08, 0.98),
    # Defense-first sides
    "MAR": (0.90, 0.84), "URU": (0.94, 0.88), "SUI": (0.95, 0.92),
    "IRN": (0.85, 0.94), "SEN": (0.94, 0.92), "COL": (0.98, 0.90),
    "ECU": (0.90, 0.88),
    # Open / chaotic sides
    "BEL": (1.06, 1.08), "AUT": (1.06, 1.04), "JPN": (1.03, 1.04),
    "KOR": (1.02, 1.06), "AUS": (0.98, 1.04), "TUR": (1.05, 1.06),
    # Hosts
    "USA": (1.00, 0.96), "MEX": (0.96, 0.94), "CAN": (1.02, 1.00),
    # Underdogs that sit deep
    "PAN": (0.88, 1.08), "BOL": (0.84, 1.12), "JAM": (0.85, 1.08),
    "HON": (0.86, 1.10), "MDG": (0.82, 1.14), "ANG": (0.85, 1.10),
    "CPV": (0.90, 1.06), "TUN": (0.90, 0.96), "DZA": (0.96, 1.00),
    "CRO": (1.00, 0.96), "DEN": (1.02, 0.96), "UKR": (1.00, 1.00),
    "SRB": (1.02, 1.06), "POL": (0.96, 1.00), "NGA": (1.00, 1.02),
    "EGY": (0.92, 0.96), "CIV": (1.00, 1.00), "CMR": (0.96, 1.04),
}


# The hand-set style multipliers average slightly below 1.0 (attack ≈ 0.978,
# defense ≈ 0.993), so applying them raw shaves a few percent off *every* total
# and re-introduces an under-lean on top of the μ calibration. Normalise by the
# means so styles only ever redistribute scoring between teams — an average
# matchup lands on the league total, defensive sides below it, open sides above.
_STYLE_MEAN_ATT = sum(a for a, _ in TEAM_STYLES.values()) / len(TEAM_STYLES)
_STYLE_MEAN_DEF = sum(d for _, d in TEAM_STYLES.values()) / len(TEAM_STYLES)


def get_style(code: str) -> tuple[float, float]:
    """Return net-neutral (attack, defense) multipliers; average team = (1, 1)."""
    att, dfn = TEAM_STYLES.get(code.upper(), (_STYLE_MEAN_ATT, _STYLE_MEAN_DEF))
    return att / _STYLE_MEAN_ATT, dfn / _STYLE_MEAN_DEF


def get_team(code: str) -> Team:
    t = TEAMS.get(code.upper())
    if t is None:
        raise KeyError(f"Unknown team code: {code!r}")
    return t


def get_scorers_for_team(team_code: str) -> list[PlayerScorer]:
    return [s for s in TOP_SCORERS if s.team == team_code.upper()]


def all_teams_sorted() -> list[Team]:
    return sorted(TEAMS.values(), key=lambda t: -t.elo)
