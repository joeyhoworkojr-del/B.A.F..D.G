"""
Live lineup / availability layer.

Key players carry an `importance` weight (share of team strength they
represent). Marking a player OUT or DOUBTFUL shifts the prediction:

  Soccer — attacker out lowers his team's xG; defender/GK out raises the
  opponent's xG; midfielders do a bit of both.
  NFL — QB out is a large hit to expected points; skill players smaller;
  defensive stars raise the opponent's expected points.

Status lives in an in-memory store mutable via the API, so predictions
update the moment team news lands. DOUBTFUL applies half the OUT impact.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.data.world_cup import TOP_SCORERS

Status = Literal["fit", "doubtful", "out"]
Sport = Literal["soccer", "nfl", "cfl", "mlb"]

VALID_STATUSES: set[str] = {"fit", "doubtful", "out"}


@dataclass(frozen=True)
class KeyPlayer:
    name: str
    team: str          # team code
    sport: str         # "soccer" | "nfl"
    position: str      # GK/DF/MF/FW  or  QB/RB/WR/DEF
    importance: float  # 0–1 share of team strength this player represents


# ─── Soccer key players ───────────────────────────────────────────────────────
# Attackers are auto-seeded from the tournament top-scorer list (importance =
# share of team goals). Curated spine players (GK/DF/MF) added for top sides.

_CURATED_SOCCER: list[KeyPlayer] = [
    KeyPlayer("E. Martínez",   "ARG", "soccer", "GK", 0.30),
    KeyPlayer("C. Romero",     "ARG", "soccer", "DF", 0.22),
    KeyPlayer("W. Saliba",     "FRA", "soccer", "DF", 0.25),
    KeyPlayer("A. Tchouaméni", "FRA", "soccer", "MF", 0.22),
    KeyPlayer("Rodri",         "ESP", "soccer", "MF", 0.35),
    KeyPlayer("Unai Simón",    "ESP", "soccer", "GK", 0.20),
    KeyPlayer("D. Rice",       "ENG", "soccer", "MF", 0.25),
    KeyPlayer("J. Pickford",   "ENG", "soccer", "GK", 0.20),
    KeyPlayer("Marquinhos",    "BRA", "soccer", "DF", 0.25),
    KeyPlayer("Alisson",       "BRA", "soccer", "GK", 0.28),
    KeyPlayer("A. Rüdiger",    "GER", "soccer", "DF", 0.24),
    KeyPlayer("J. Kimmich",    "GER", "soccer", "MF", 0.26),
    KeyPlayer("V. van Dijk",   "NED", "soccer", "DF", 0.30),
    KeyPlayer("Rúben Dias",    "POR", "soccer", "DF", 0.26),
    KeyPlayer("A. Hakimi",     "MAR", "soccer", "DF", 0.28),
    KeyPlayer("Y. Bounou",     "MAR", "soccer", "GK", 0.24),
    KeyPlayer("R. Araújo",     "URU", "soccer", "DF", 0.26),
    KeyPlayer("E. Militão",    "BRA", "soccer", "DF", 0.20),
    KeyPlayer("K. Koulibaly",  "SEN", "soccer", "DF", 0.24),
    KeyPlayer("M. ter Stegen", "GER", "soccer", "GK", 0.20),
    KeyPlayer("T. Adams",      "USA", "soccer", "MF", 0.22),
    KeyPlayer("M. Robinson",   "USA", "soccer", "DF", 0.18),
    KeyPlayer("E. Álvarez",    "MEX", "soccer", "MF", 0.24),
    KeyPlayer("A. Davies",     "CAN", "soccer", "DF", 0.28),
    KeyPlayer("L. Martínez",   "ARG", "soccer", "FW", 0.30),
    KeyPlayer("J. Musiala",    "GER", "soccer", "MF", 0.28),
]

# Attackers from the top-scorer table: importance = share of team goals.
_SCORER_PLAYERS: list[KeyPlayer] = [
    KeyPlayer(s.name, s.team, "soccer", "FW", min(s.goal_share, 0.85))
    for s in TOP_SCORERS
]


# ─── NFL key players ──────────────────────────────────────────────────────────
# Starting QBs for every franchise (importance ≈ drop-off to the backup),
# plus a handful of game-tilting non-QBs.

_NFL_QBS: list[tuple[str, str, float]] = [
    ("P. Mahomes",     "KC",  0.95), ("J. Allen",      "BUF", 0.95),
    ("L. Jackson",     "BAL", 0.95), ("J. Burrow",     "CIN", 0.90),
    ("J. Goff",        "DET", 0.80), ("J. Hurts",      "PHI", 0.85),
    ("B. Purdy",       "SF",  0.75), ("M. Stafford",   "LA",  0.80),
    ("D. Prescott",    "DAL", 0.80), ("J. Love",       "GB",  0.80),
    ("T. Tagovailoa",  "MIA", 0.75), ("C. Stroud",     "HOU", 0.85),
    ("J. Herbert",     "LAC", 0.85), ("K. Murray",     "ARI", 0.70),
    ("G. Smith",       "SEA", 0.70), ("B. Mayfield",   "TB",  0.75),
    ("J. Daniels",     "WSH", 0.85), ("C. Williams",   "CHI", 0.75),
    ("A. Richardson",  "IND", 0.65), ("T. Lawrence",   "JAX", 0.75),
    ("W. Levis",       "TEN", 0.55), ("D. Watson",     "CLE", 0.55),
    ("R. Wilson",      "PIT", 0.65), ("A. Rodgers",    "NYJ", 0.75),
    ("D. Maye",        "NE",  0.70), ("D. Jones",      "NYG", 0.55),
    ("B. Nix",         "DEN", 0.70), ("G. Minshew",    "LV",  0.55),
    ("K. Cousins",     "ATL", 0.70), ("D. Carr",       "NO",  0.65),
    ("B. Young",       "CAR", 0.60), ("S. Darnold",    "MIN", 0.65),
]

_NFL_STARS: list[KeyPlayer] = [
    KeyPlayer("C. McCaffrey", "SF",  "nfl", "RB",  0.60),
    KeyPlayer("T. Hill",      "MIA", "nfl", "WR",  0.55),
    KeyPlayer("J. Chase",     "CIN", "nfl", "WR",  0.55),
    KeyPlayer("C. Lamb",      "DAL", "nfl", "WR",  0.50),
    KeyPlayer("J. Jefferson", "MIN", "nfl", "WR",  0.60),
    KeyPlayer("A. St. Brown", "DET", "nfl", "WR",  0.50),
    KeyPlayer("T. Kelce",     "KC",  "nfl", "TE",  0.45),
    KeyPlayer("M. Parsons",   "DAL", "nfl", "DEF", 0.55),
    KeyPlayer("T.J. Watt",    "PIT", "nfl", "DEF", 0.60),
    KeyPlayer("M. Garrett",   "CLE", "nfl", "DEF", 0.60),
    KeyPlayer("A. Donald",    "LA",  "nfl", "DEF", 0.50),
    KeyPlayer("S. Barkley",   "PHI", "nfl", "RB",  0.50),
]

# ─── CFL key players ──────────────────────────────────────────────────────────
# Starting QBs (importance ≈ drop-off to the backup). In the CFL the QB is an
# even larger share of team quality than in the NFL.

_CFL_QBS: list[tuple[str, str, float]] = [
    ("T. Harris",    "SSK", 0.90), ("Z. Collaros",  "WPG", 0.90),
    ("D. Alexander", "MTL", 0.85), ("B.L. Mitchell","HAM", 0.85),
    ("N. Rourke",    "BC",  0.90), ("V. Adams Jr.", "CGY", 0.80),
    ("C. Kelly",     "TOR", 0.80), ("T. Ford",      "EDM", 0.75),
    ("D. Brown",     "OTT", 0.70),
]

# ─── MLB key players ──────────────────────────────────────────────────────────
# Staff aces (importance ≈ gap to a spot starter on that day's runs allowed)
# plus a few lineup-tilting bats.

_MLB_ACES: list[tuple[str, str, float]] = [
    ("G. Cole",      "NYY", 0.75), ("G. Crochet",   "BOS", 0.75),
    ("K. Gausman",   "TOR", 0.60), ("S. McClanahan","TB",  0.65),
    ("Z. Eflin",     "BAL", 0.50), ("T. Skubal",    "DET", 0.90),
    ("T. Bibee",     "CLE", 0.60), ("C. Ragans",    "KC",  0.70),
    ("P. López",     "MIN", 0.60), ("S. Cannon",    "CHW", 0.40),
    ("H. Brown",     "HOU", 0.70), ("L. Gilbert",   "SEA", 0.70),
    ("N. Eovaldi",   "TEX", 0.60), ("Y. Kikuchi",   "LAA", 0.55),
    ("JP Sears",     "ATH", 0.45), ("Z. Wheeler",   "PHI", 0.80),
    ("K. Senga",     "NYM", 0.65), ("C. Sale",      "ATL", 0.75),
    ("M. Gore",      "WSH", 0.60), ("S. Alcántara", "MIA", 0.65),
    ("F. Peralta",   "MIL", 0.65), ("S. Imanaga",   "CHC", 0.70),
    ("S. Gray",      "STL", 0.60), ("H. Greene",    "CIN", 0.70),
    ("P. Skenes",    "PIT", 0.90), ("Y. Yamamoto",  "LAD", 0.75),
    ("D. Cease",     "SD",  0.70), ("L. Webb",      "SF",  0.70),
    ("C. Burnes",    "ARI", 0.75), ("K. Freeland",  "COL", 0.40),
]

_MLB_BATS: list[KeyPlayer] = [
    KeyPlayer("S. Ohtani",  "LAD", "mlb", "DH", 0.60),
    KeyPlayer("A. Judge",   "NYY", "mlb", "OF", 0.65),
    KeyPlayer("B. Harper",  "PHI", "mlb", "IF", 0.50),
    KeyPlayer("J. Soto",    "NYM", "mlb", "OF", 0.55),
    KeyPlayer("B. Witt Jr.","KC",  "mlb", "IF", 0.60),
]

KEY_PLAYERS: list[KeyPlayer] = (
    _SCORER_PLAYERS
    + _CURATED_SOCCER
    + [KeyPlayer(n, t, "nfl", "QB", imp) for n, t, imp in _NFL_QBS]
    + _NFL_STARS
    + [KeyPlayer(n, t, "cfl", "QB", imp) for n, t, imp in _CFL_QBS]
    + [KeyPlayer(n, t, "mlb", "P", imp) for n, t, imp in _MLB_ACES]
    + _MLB_BATS
)

# Deduplicate by (sport, team, name) — curated wins over auto-seeded
_dedup: dict[tuple[str, str, str], KeyPlayer] = {}
for p in KEY_PLAYERS:
    _dedup.setdefault((p.sport, p.team, p.name), p)
KEY_PLAYERS = list(_dedup.values())


# ─── Availability store (in-memory, API-mutable) ──────────────────────────────

_availability: dict[tuple[str, str, str], str] = {}


def _key(sport: str, team: str, name: str) -> tuple[str, str, str]:
    return (sport.lower(), team.upper(), name)


def get_key_players(sport: str, team: str) -> list[KeyPlayer]:
    team = team.upper()
    sport = sport.lower()
    players = [p for p in KEY_PLAYERS if p.sport == sport and p.team == team]
    return sorted(players, key=lambda p: -p.importance)


def get_status(sport: str, team: str, name: str) -> str:
    return _availability.get(_key(sport, team, name), "fit")


def set_status(sport: str, team: str, name: str, status: str) -> KeyPlayer:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status {status!r}; must be one of {sorted(VALID_STATUSES)}")
    for p in get_key_players(sport, team):
        if p.name == name:
            _availability[_key(sport, team, name)] = status
            return p
    raise KeyError(f"Unknown {sport} key player {name!r} on {team}")


def reset_team(sport: str, team: str) -> None:
    keys = [k for k in _availability if k[0] == sport.lower() and k[1] == team.upper()]
    for k in keys:
        del _availability[k]


def unavailable_players(
    sport: str,
    team: str,
    extra_out: list[str] | None = None,
) -> list[tuple[KeyPlayer, float]]:
    """
    Players currently reducing team strength: returns (player, weight) where
    weight is 1.0 for OUT and 0.5 for DOUBTFUL. `extra_out` lets a request
    mark additional players out for what-if analysis without mutating state.
    """
    extra = {n for n in (extra_out or [])}
    result: list[tuple[KeyPlayer, float]] = []
    for p in get_key_players(sport, team):
        status = get_status(sport, team, p.name)
        if p.name in extra or status == "out":
            result.append((p, 1.0))
        elif status == "doubtful":
            result.append((p, 0.5))
    return result
