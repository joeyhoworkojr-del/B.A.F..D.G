"""
Altitude data + acclimatization for soccer.

Playing at high elevation is one of the most robust home-field effects in
football: visiting sides from sea level tire faster and the ball flies
differently. The effect is not about *who is nominally home* — it is about
the gap between the match altitude and the altitude a team is used to. A
Bolivian or Mexican side at 2,200 m is unaffected; a European side there is
badly disadvantaged (McSharry, BMJ 2007, on CONMEBOL qualifiers).

We therefore track two things:
  • the altitude of each venue, and
  • the altitude each national team is acclimatized to (its home venue).

The disadvantage for a side is the amount the venue sits *above* what that
side is used to — never below (a high-altitude team playing lower is fine).
"""
from __future__ import annotations

# Altitude threshold below which elevation has no material effect.
ALTITUDE_THRESHOLD_M: float = 1500.0

# Venue elevations (metres). Only high-altitude venues matter; everything
# else is near sea level. Keyed by the venue names used in world_cup fixtures.
VENUE_ALTITUDE_M: dict[str, float] = {
    "Estadio Azteca, CDMX": 2240.0,
    "State Farm Stadium, Glendale": 331.0,
    "Mercedes-Benz Stadium, Atlanta": 320.0,
    "Rose Bowl, Pasadena": 264.0,
    "AT&T Stadium, Dallas": 180.0,
    "SoFi Stadium, LA": 30.0,
    "MetLife Stadium, NJ": 5.0,
    "Levi's Stadium, SF": 5.0,
    "Hard Rock Stadium, Miami": 2.0,
    "BC Place, Vancouver": 3.0,
    "BMO Field, Toronto": 76.0,
    "NRG Stadium, Houston": 15.0,
    "Gillette Stadium, Boston": 89.0,
    "Lincoln Financial Field, Philly": 12.0,
}

# National-team home altitude (metres). Teams whose home matches are played
# at elevation are acclimatized; everyone else defaults to near sea level.
_DEFAULT_TEAM_ALTITUDE_M: float = 120.0
TEAM_HOME_ALTITUDE_M: dict[str, float] = {
    "BOL": 3640.0,   # La Paz
    "ECU": 2850.0,   # Quito
    "COL": 2640.0,   # Bogotá
    "MEX": 2240.0,   # Mexico City
    "PER": 150.0,    # Lima is at sea level despite the Andes
}


def venue_altitude(venue: str) -> float:
    """Elevation of a venue in metres (0 if unknown)."""
    return VENUE_ALTITUDE_M.get(venue, 0.0)


def team_home_altitude(code: str) -> float:
    """Altitude a national team is acclimatized to (metres)."""
    return TEAM_HOME_ALTITUDE_M.get(code.upper(), _DEFAULT_TEAM_ALTITUDE_M)


def altitude_disadvantage_m(venue_alt: float, team_code: str) -> float:
    """
    How far above its comfort zone a side is at this venue, in metres,
    floored at zero. A team used to higher elevation is never disadvantaged.
    """
    return max(0.0, venue_alt - team_home_altitude(team_code))
