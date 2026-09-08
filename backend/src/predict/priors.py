"""
Data-driven team priors.

The gridiron model starts from a static Elo per team, hand-set at the top of
the season. That is a reasonable day-one guess and a poor week-eight one. Two
free feeds carry what actually happened:

  NFL    → nflverse weekly team EPA (no key)
  NCAAF  → CFBD SP+, falling back to season PPA (needs CFBD_API_KEY)

Both are converted to the same unit — *points of margin per game versus an
average team* — blended with the static prior, and handed back as an Elo. The
existing self-correcting delta then runs on top, unchanged, so this layer
sharpens the starting point rather than competing with it.

Three rules keep it honest:

  1. A provider that is unavailable changes nothing. `prior_elo` returns the
     static rating and says so; it never partially applies a stale snapshot.
  2. Early-season samples are shrunk toward the static prior, so one blowout in
     week one cannot rewrite a rating.
  3. The shift is capped. Even a full season of data moves a team by at most
     MAX_SHIFT_POINTS, because these feeds inform the prior — they are not a
     replacement model.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from src.data import ncaaf as ncaaf_data
from src.data import nfl as nfl_data
from src.ingest import cfbd, nflverse

log = logging.getLogger(__name__)

# How far a feed may move a team, in points of expected margin per game.
MAX_SHIFT_POINTS = 6.0

# Maximum weight the feed may take from the static prior, before shrinkage.
FEED_WEIGHT = 0.60

# Sample size at which the feed reaches half its maximum weight. Roughly a
# third of an NFL season — enough for EPA to mean something, short enough that
# it is contributing well before the playoffs.
SHRINK_GAMES = 6.0

REFRESH_SECONDS = 3600.0


def _points_per_elo(league: str) -> float:
    """
    Points of expected margin per Elo point, on this app's rating scale.

    A team's rating feeds both its own offense and the opponent's defense, and
    margin averages the two sides, hence the halving.
    """
    if league == "nfl":
        return (nfl_data._OFF_COEF + nfl_data._DEF_COEF) / 2.0
    if league == "ncaaf":
        return (ncaaf_data._OFF_COEF + ncaaf_data._DEF_COEF) / 2.0
    return 0.0


@dataclass
class TeamPrior:
    """One team's feed-derived strength, in points of margin per game."""
    code: str
    points: float               # vs an average team, positive = better
    games: int
    source: str                 # "nflverse-epa" | "cfbd-sp+" | "cfbd-ppa"


@dataclass
class LeaguePriors:
    league: str
    source: str = ""
    ok: bool = False
    note: str = ""
    fetched_at: str = ""
    teams: dict[str, TeamPrior] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.teams is None:
            self.teams = {}


_priors: dict[str, LeaguePriors] = {}
_refresh_lock = asyncio.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── NFL: nflverse EPA ────────────────────────────────────────────────────────

# nflverse abbreviations match this app's team codes except for Washington.
_NFLVERSE_ALIASES = {"WAS": "WSH", "LAR": "LA", "OAK": "LV", "SD": "LAC", "STL": "LA"}


def _nfl_code(team: str) -> str:
    code = (team or "").strip().upper()
    return _NFLVERSE_ALIASES.get(code, code)


async def _load_nfl() -> LeaguePriors:
    data = await nflverse.load_season()
    if not data.ok:
        return LeaguePriors(league="nfl", ok=False, note=data.note, fetched_at=_now())

    forms = nflverse.team_form(data)
    teams: dict[str, TeamPrior] = {}
    for raw_code, form in forms.items():
        code = _nfl_code(raw_code)
        if code not in nfl_data.NFL_TEAMS:
            continue
        if form.off_epa_per_game is None or form.def_epa_per_game is None:
            continue
        # EPA is already denominated in points, so offense minus defence
        # allowed is directly a per-game margin versus an average opponent.
        net = form.off_epa_per_game - form.def_epa_per_game
        teams[code] = TeamPrior(code=code, points=net, games=form.games,
                                source="nflverse-epa")

    if not teams:
        return LeaguePriors(league="nfl", ok=False, fetched_at=_now(),
                            note="nflverse returned no usable team rows")
    return LeaguePriors(league="nfl", ok=True, source=f"nflverse {data.season}",
                        note="ok", fetched_at=_now(), teams=_centre(teams))


# ── NCAAF: CFBD SP+, then PPA ────────────────────────────────────────────────

# CFBD keys teams by school name; this app keys them by ESPN-style code, and
# carries more than one code for some schools (ESPN has used both "GA" and
# "UGA" for Georgia). A name therefore maps to every code that shares it, and
# the prior is applied to all of them — mapping to just one would leave the
# alias running on a stale static rating.
def _build_name_index() -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for team in ncaaf_data.NCAAF_TEAMS.values():
        index.setdefault(team.name.strip().lower(), []).append(team.code)
    return index


_NCAAF_BY_NAME = _build_name_index()


def _ncaaf_codes(school: str) -> list[str]:
    return _NCAAF_BY_NAME.get((school or "").strip().lower(), [])


# College seasons are ~12 games; PPA is per play, so it needs a scale factor to
# become per-game margin. ~140 plays a game across both sides, halved because
# offense and defence each account for their own half.
_PPA_PLAYS_PER_GAME = 70.0
_ASSUMED_NCAAF_GAMES = 12


async def _load_ncaaf() -> LeaguePriors:
    if not cfbd.configured():
        return LeaguePriors(league="ncaaf", ok=False, fetched_at=_now(),
                            note=f"needs {cfbd.KEY_ENV_VAR}; register free at {cfbd.KEY_SIGNUP_URL}")

    sp = await cfbd.sp_ratings()
    if sp.ok and sp.rows:
        teams: dict[str, TeamPrior] = {}
        for row in sp.rows:
            if row.rating is None:
                continue
            # SP+ is already "points better than average on a neutral field".
            for code in _ncaaf_codes(row.team):
                teams[code] = TeamPrior(code=code, points=float(row.rating),
                                        games=_ASSUMED_NCAAF_GAMES, source="cfbd-sp+")
        if teams:
            return LeaguePriors(league="ncaaf", ok=True, source="CFBD SP+",
                                note="ok", fetched_at=_now(), teams=_centre(teams))

    adv = await cfbd.team_advanced()
    if adv.ok and adv.rows:
        teams = {}
        for row in adv.rows:
            if row.off_ppa is None or row.def_ppa is None:
                continue
            net = (row.off_ppa - row.def_ppa) * _PPA_PLAYS_PER_GAME
            for code in _ncaaf_codes(row.team):
                teams[code] = TeamPrior(code=code, points=net,
                                        games=_ASSUMED_NCAAF_GAMES, source="cfbd-ppa")
        if teams:
            return LeaguePriors(league="ncaaf", ok=True, source="CFBD season PPA",
                                note="SP+ unavailable, using season PPA",
                                fetched_at=_now(), teams=_centre(teams))

    reason = sp.note if not sp.ok else adv.note
    return LeaguePriors(league="ncaaf", ok=False, note=reason or "no usable rows",
                        fetched_at=_now())


def _centre(teams: dict[str, TeamPrior]) -> dict[str, TeamPrior]:
    """
    Re-centre on the mean of the teams we actually matched.

    Only a subset of FBS is modelled here, and a subset's average is not the
    league average. Without this the whole subset drifts up or down together
    and every game inherits the bias.
    """
    if not teams:
        return teams
    mean = sum(t.points for t in teams.values()) / len(teams)
    return {
        code: TeamPrior(code=t.code, points=t.points - mean, games=t.games, source=t.source)
        for code, t in teams.items()
    }


# ── applying ─────────────────────────────────────────────────────────────────

def prior_elo(league: str, code: str, static_elo: float) -> tuple[float, str]:
    """
    The Elo to feed the model, and where it came from.

    Returns the static rating unchanged whenever the feed has nothing to say
    about this team — a missing provider must never silently become a zero.
    """
    league = (league or "").lower()
    per_elo = _points_per_elo(league)
    lp = _priors.get(league)
    if per_elo <= 0 or lp is None or not lp.ok:
        return static_elo, "static"

    team = lp.teams.get((code or "").upper())
    if team is None:
        return static_elo, "static"

    static_points = (static_elo - 1500.0) * per_elo
    weight = FEED_WEIGHT * (team.games / (team.games + SHRINK_GAMES))
    blended = (1.0 - weight) * static_points + weight * team.points

    shift = max(-MAX_SHIFT_POINTS, min(MAX_SHIFT_POINTS, blended - static_points))
    return 1500.0 + (static_points + shift) / per_elo, team.source


async def refresh() -> dict[str, LeaguePriors]:
    """Reload both feeds. Safe to call concurrently; failures leave the last good snapshot in place."""
    async with _refresh_lock:
        for league, loader in (("nfl", _load_nfl), ("ncaaf", _load_ncaaf)):
            try:
                loaded = await loader()
            except Exception as exc:                      # pragma: no cover
                log.warning("prior refresh failed for %s: %s", league, exc)
                continue
            # A failed reload must not discard a snapshot that is still usable.
            if loaded.ok or league not in _priors:
                _priors[league] = loaded
        return dict(_priors)


async def refresh_forever(interval: float = REFRESH_SECONDS) -> None:
    """Background refresh loop; started by the app lifespan."""
    while True:
        try:
            await refresh()
        except asyncio.CancelledError:
            raise
        except Exception as exc:                          # pragma: no cover
            log.warning("prior refresh loop error: %s", exc)
        await asyncio.sleep(interval)


def status() -> dict:
    """
    What is actually driving the priors right now.

    Reports the last successful load, not merely that a provider is
    configured — "a key is set" and "data arrived" are different claims.
    """
    return {
        "max_shift_points": MAX_SHIFT_POINTS,
        "leagues": {
            league: {
                "ok": lp.ok,
                "source": lp.source,
                "teams": len(lp.teams),
                "note": lp.note,
                "fetched_at": lp.fetched_at,
            }
            for league, lp in _priors.items()
        },
    }


def reset() -> None:
    _priors.clear()
