"""
Live-conditions adjustment engine.

Turns live inputs (venue weather, lineup availability) into concrete model
shifts, each with a human-readable label so the UI can show exactly what
moved the number and by how much.

Soccer adjustments are multiplicative on team xG.
NFL adjustments are additive on expected points per team.

Effect sizes are conservative, drawn from published research on weather and
absence effects (e.g. wind is the only weather variable with a robust,
material effect on NFL totals; rain shaves goals slightly in soccer).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.data.altitude import (
    ALTITUDE_THRESHOLD_M,
    altitude_disadvantage_m,
    venue_altitude,
)
from src.data.lineups import unavailable_players
from src.ingest.weather import WeatherReport


@dataclass
class Adjustment:
    label: str                     # short name, e.g. "High wind (34 km/h)"
    detail: str                    # one-line explanation
    source: str                    # "weather" | "lineup"
    home_xg_mult: float = 1.0      # soccer
    away_xg_mult: float = 1.0
    home_pts_delta: float = 0.0    # NFL
    away_pts_delta: float = 0.0


@dataclass
class ConditionSet:
    adjustments: list[Adjustment] = field(default_factory=list)

    @property
    def home_xg_mult(self) -> float:
        m = 1.0
        for a in self.adjustments:
            m *= a.home_xg_mult
        return m

    @property
    def away_xg_mult(self) -> float:
        m = 1.0
        for a in self.adjustments:
            m *= a.away_xg_mult
        return m

    @property
    def home_pts_delta(self) -> float:
        return sum(a.home_pts_delta for a in self.adjustments)

    @property
    def away_pts_delta(self) -> float:
        return sum(a.away_pts_delta for a in self.adjustments)


# ─── Soccer: weather ──────────────────────────────────────────────────────────

_HEAVY_WMO = {65, 73, 75, 82, 95, 96}   # heavy rain/snow/storm codes
_WET_WMO = {51, 53, 55, 61, 63, 80, 81}


def soccer_weather_adjustments(w: WeatherReport | None) -> list[Adjustment]:
    if w is None or w.is_indoor:
        return []
    adj: list[Adjustment] = []

    if w.wind_speed_kmh >= 30:
        adj.append(Adjustment(
            label=f"Strong wind ({w.wind_speed_kmh:.0f} km/h)",
            detail="Crossing and long passing degrade badly in high wind — both teams' xG down 8%.",
            source="weather", home_xg_mult=0.92, away_xg_mult=0.92,
        ))
    elif w.wind_speed_kmh >= 20:
        adj.append(Adjustment(
            label=f"Breezy ({w.wind_speed_kmh:.0f} km/h)",
            detail="Moderate wind disrupts service into the box — both teams' xG down 4%.",
            source="weather", home_xg_mult=0.96, away_xg_mult=0.96,
        ))

    if w.wmo_code in _HEAVY_WMO:
        adj.append(Adjustment(
            label=f"Severe weather: {w.condition}",
            detail="Heavy rain/snow slows the ball and play — both teams' xG down 9%.",
            source="weather", home_xg_mult=0.91, away_xg_mult=0.91,
        ))
    elif w.wmo_code in _WET_WMO or w.precipitation_prob >= 60:
        adj.append(Adjustment(
            label=f"Wet conditions ({w.precipitation_prob}% rain)",
            detail="A wet pitch adds variance and slightly suppresses finishing — xG down 4%.",
            source="weather", home_xg_mult=0.96, away_xg_mult=0.96,
        ))

    if w.temperature_c >= 32:
        adj.append(Adjustment(
            label=f"Extreme heat ({w.temperature_c:.0f}°C)",
            detail="High heat slows tempo and pressing — both teams' xG down 5%.",
            source="weather", home_xg_mult=0.95, away_xg_mult=0.95,
        ))
    elif w.temperature_c <= -5:
        adj.append(Adjustment(
            label=f"Freezing ({w.temperature_c:.0f}°C)",
            detail="Sub-zero conditions reduce sharpness — both teams' xG down 4%.",
            source="weather", home_xg_mult=0.96, away_xg_mult=0.96,
        ))

    return adj


# ─── Soccer: altitude ─────────────────────────────────────────────────────────

# Per 1,000 m a non-acclimatized side is above its comfort zone:
_ALT_OWN_SUPPRESS = 0.05    # its own xG down (aerobic disadvantage)
_ALT_OPP_BOOST = 0.035      # opponent's xG up (they exploit the fatigue)
_ALT_CAP_M = 3000.0         # effect saturates past ~3 km of gap


def soccer_altitude_adjustments(
    venue: str,
    home_code: str,
    away_code: str,
    home_name: str | None = None,
    away_name: str | None = None,
) -> list[Adjustment]:
    """
    Model the high-altitude edge. Returns [] for sea-level venues or when both
    sides are equally acclimatized (e.g. Mexico vs Ecuador at Estadio Azteca —
    both used to thin air, so no altitude edge, only the host advantage).
    """
    alt = venue_altitude(venue)
    if alt < ALTITUDE_THRESHOLD_M:
        return []

    d_home = min(altitude_disadvantage_m(alt, home_code), _ALT_CAP_M) / 1000.0
    d_away = min(altitude_disadvantage_m(alt, away_code), _ALT_CAP_M) / 1000.0
    if d_home == 0.0 and d_away == 0.0:
        return []   # both acclimatized — no differential effect

    home_mult = (1.0 - _ALT_OWN_SUPPRESS * d_home) * (1.0 + _ALT_OPP_BOOST * d_away)
    away_mult = (1.0 - _ALT_OWN_SUPPRESS * d_away) * (1.0 + _ALT_OPP_BOOST * d_home)

    home_name = home_name or home_code
    away_name = away_name or away_code
    # Describe from the perspective of the more-disadvantaged (visiting) side.
    if d_away >= d_home:
        acclimatized, struggler = home_name, away_name
        swing = (1.0 - away_mult) * 100.0
    else:
        acclimatized, struggler = away_name, home_name
        swing = (1.0 - home_mult) * 100.0
    detail = (
        f"{acclimatized} is acclimatized to {alt:,.0f} m; {struggler} is not — "
        f"the visiting side's xG drops ~{abs(swing):.0f}% at this elevation."
    )

    return [Adjustment(
        label=f"Altitude ({alt:,.0f} m)",
        detail=detail,
        source="altitude",
        home_xg_mult=home_mult,
        away_xg_mult=away_mult,
    )]


# ─── Soccer: lineups ──────────────────────────────────────────────────────────

# Fraction of a player's importance that converts into an xG shift.
_ATT_WEIGHT = 0.35    # attacker out → own xG down importance×35%
_DEF_WEIGHT = 0.30    # defender/GK out → opponent xG up importance×30%
_MID_ATT_WEIGHT = 0.20
_MID_DEF_WEIGHT = 0.12


def _soccer_absence(side: str, name: str, position: str, impact: float, weight: float) -> Adjustment:
    own_mult, opp_mult = 1.0, 1.0
    if position == "FW":
        own_mult = 1.0 - _ATT_WEIGHT * impact * weight
        detail = f"{name} ({position}) unavailable — team xG down {(1 - own_mult) * 100:.0f}%."
    elif position in ("GK", "DF"):
        opp_mult = 1.0 + _DEF_WEIGHT * impact * weight
        detail = f"{name} ({position}) unavailable — opponent xG up {(opp_mult - 1) * 100:.0f}%."
    else:  # MF: some of both
        own_mult = 1.0 - _MID_ATT_WEIGHT * impact * weight
        opp_mult = 1.0 + _MID_DEF_WEIGHT * impact * weight
        detail = f"{name} ({position}) unavailable — team xG down {(1 - own_mult) * 100:.0f}%, opponent up {(opp_mult - 1) * 100:.0f}%."

    if side == "home":
        return Adjustment(
            label=f"{name} out (home)", detail=detail, source="lineup",
            home_xg_mult=own_mult, away_xg_mult=opp_mult,
        )
    return Adjustment(
        label=f"{name} out (away)", detail=detail, source="lineup",
        home_xg_mult=opp_mult, away_xg_mult=own_mult,
    )


def soccer_lineup_adjustments(
    home_code: str,
    away_code: str,
    extra_out_home: list[str] | None = None,
    extra_out_away: list[str] | None = None,
) -> list[Adjustment]:
    adj: list[Adjustment] = []
    for player, weight in unavailable_players("soccer", home_code, extra_out_home):
        adj.append(_soccer_absence("home", player.name, player.position, player.importance, weight))
    for player, weight in unavailable_players("soccer", away_code, extra_out_away):
        adj.append(_soccer_absence("away", player.name, player.position, player.importance, weight))
    return adj


# ─── NFL: weather ─────────────────────────────────────────────────────────────

def nfl_weather_adjustments(w: WeatherReport | None) -> list[Adjustment]:
    if w is None or w.is_indoor:
        return []
    adj: list[Adjustment] = []
    wind_mph = w.wind_speed_kmh / 1.609

    if wind_mph > 12:
        # ~ -0.6 points per team per 5 mph over 12, capped at -3.5/team
        per_team = min(3.5, 0.12 * (wind_mph - 12))
        adj.append(Adjustment(
            label=f"Wind {wind_mph:.0f} mph",
            detail=f"Wind past 12 mph measurably kills passing and kicking — total down {2 * per_team:.1f} pts.",
            source="weather", home_pts_delta=-per_team, away_pts_delta=-per_team,
        ))

    if w.wmo_code in _HEAVY_WMO:
        adj.append(Adjustment(
            label=f"Severe weather: {w.condition}",
            detail="Heavy precipitation — ball security and footing issues, total down 3 pts.",
            source="weather", home_pts_delta=-1.5, away_pts_delta=-1.5,
        ))
    elif w.wmo_code in _WET_WMO or w.precipitation_prob >= 60:
        adj.append(Adjustment(
            label=f"Rain likely ({w.precipitation_prob}%)",
            detail="Wet ball modestly suppresses passing efficiency — total down 1.5 pts.",
            source="weather", home_pts_delta=-0.75, away_pts_delta=-0.75,
        ))

    if w.temperature_c <= -8:
        adj.append(Adjustment(
            label=f"Deep freeze ({w.temperature_c:.0f}°C)",
            detail="Extreme cold stiffens the ball and hands — total down 2 pts.",
            source="weather", home_pts_delta=-1.0, away_pts_delta=-1.0,
        ))

    return adj


# ─── NFL: lineups ─────────────────────────────────────────────────────────────

_QB_PTS = 6.5      # a top starter out costs up to ~6.5 expected points
_SKILL_PTS = 2.5   # elite RB/WR/TE out
_DEF_PTS = 2.0     # elite defender out → opponent gains


def nfl_lineup_adjustments(
    home_code: str,
    away_code: str,
    extra_out_home: list[str] | None = None,
    extra_out_away: list[str] | None = None,
    *,
    sport: str = "nfl",   # "nfl" | "cfl" — same impact model for both
) -> list[Adjustment]:
    adj: list[Adjustment] = []

    def _absence(side: str, name: str, position: str, impact: float, weight: float) -> Adjustment:
        own_delta, opp_delta = 0.0, 0.0
        if position == "QB":
            own_delta = -_QB_PTS * impact * weight
            detail = f"{name} (QB) out — offense worth {abs(own_delta):.1f} fewer points."
        elif position == "DEF":
            opp_delta = _DEF_PTS * impact * weight
            detail = f"{name} (DEF) out — opponent gains {opp_delta:.1f} points."
        else:
            own_delta = -_SKILL_PTS * impact * weight
            detail = f"{name} ({position}) out — offense worth {abs(own_delta):.1f} fewer points."

        if side == "home":
            return Adjustment(
                label=f"{name} out (home)", detail=detail, source="lineup",
                home_pts_delta=own_delta, away_pts_delta=opp_delta,
            )
        return Adjustment(
            label=f"{name} out (away)", detail=detail, source="lineup",
            home_pts_delta=opp_delta, away_pts_delta=own_delta,
        )

    for player, weight in unavailable_players(sport, home_code, extra_out_home):
        adj.append(_absence("home", player.name, player.position, player.importance, weight))
    for player, weight in unavailable_players(sport, away_code, extra_out_away):
        adj.append(_absence("away", player.name, player.position, player.importance, weight))
    return adj


# ─── MLB: weather ─────────────────────────────────────────────────────────────

def mlb_weather_adjustments(w: WeatherReport | None) -> list[Adjustment]:
    if w is None or w.is_indoor:
        return []
    adj: list[Adjustment] = []

    if w.temperature_c >= 30:
        adj.append(Adjustment(
            label=f"Hot ({w.temperature_c:.0f}°C)",
            detail="The ball carries in heat — both teams' expected runs up 4%.",
            source="weather", home_xg_mult=1.04, away_xg_mult=1.04,
        ))
    elif w.temperature_c <= 5:
        adj.append(Adjustment(
            label=f"Cold ({w.temperature_c:.0f}°C)",
            detail="Cold air knocks down fly balls — expected runs down 5%.",
            source="weather", home_xg_mult=0.95, away_xg_mult=0.95,
        ))

    if w.wind_speed_kmh >= 30:
        adj.append(Adjustment(
            label=f"Strong wind ({w.wind_speed_kmh:.0f} km/h)",
            detail="High wind (direction unknown) adds noise — slight run suppression.",
            source="weather", home_xg_mult=0.97, away_xg_mult=0.97,
        ))

    if w.wmo_code in _HEAVY_WMO:
        adj.append(Adjustment(
            label=f"Severe weather: {w.condition}",
            detail="Rain risk — sloppy conditions suppress offense slightly.",
            source="weather", home_xg_mult=0.97, away_xg_mult=0.97,
        ))

    return adj


# ─── MLB: lineups ─────────────────────────────────────────────────────────────

def mlb_lineup_adjustments(
    home_code: str,
    away_code: str,
    extra_out_home: list[str] | None = None,
    extra_out_away: list[str] | None = None,
) -> list[Adjustment]:
    """Ace scratched → opponent scores more; star bat out → own runs dip."""
    adj: list[Adjustment] = []

    def _absence(side: str, name: str, position: str, impact: float, weight: float) -> Adjustment:
        own_mult, opp_mult = 1.0, 1.0
        if position == "P":
            opp_mult = 1.0 + 0.15 * impact * weight
            detail = f"{name} (SP) not starting — opponent expected runs up {(opp_mult - 1) * 100:.0f}%."
        else:
            own_mult = 1.0 - 0.06 * impact * weight
            detail = f"{name} ({position}) out — own expected runs down {(1 - own_mult) * 100:.0f}%."
        if side == "home":
            return Adjustment(label=f"{name} out (home)", detail=detail, source="lineup",
                              home_xg_mult=own_mult, away_xg_mult=opp_mult)
        return Adjustment(label=f"{name} out (away)", detail=detail, source="lineup",
                          home_xg_mult=opp_mult, away_xg_mult=own_mult)

    for player, weight in unavailable_players("mlb", home_code, extra_out_home):
        adj.append(_absence("home", player.name, player.position, player.importance, weight))
    for player, weight in unavailable_players("mlb", away_code, extra_out_away):
        adj.append(_absence("away", player.name, player.position, player.importance, weight))
    return adj
