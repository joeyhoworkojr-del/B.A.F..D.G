"""
NFL team and player performance from nflverse.

nflverse publishes the nflfastR data as plain CSV assets on GitHub releases:
free, no key, no rate limit, no terms to sign. Two files carry everything this
app needs:

  stats_player_week_{season}.csv  — every player's week: attempts, yards, TDs,
                                    target share, and EPA per phase.
  stats_team_week_{season}.csv    — the same aggregated to the team.

Deliberately *not* used: play_by_play_{season}.csv. A season of raw plays is
50 MB+ and ~380 columns, and the weekly files already carry the EPA totals the
model wants. Downloading it on a 512 MB instance to recompute a number that is
already published would be a good way to get the API OOM-killed.

Everything here degrades rather than fails. A missing season, a renamed
column, an upstream outage — all produce an empty result carrying a reason,
never an exception and never a fabricated number. Callers report "no data"
rather than guessing.
"""
from __future__ import annotations

import asyncio
import csv
import io
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Optional

import httpx

log = logging.getLogger(__name__)

RELEASE_BASE = "https://github.com/nflverse/nflverse-data/releases/download"
PLAYER_WEEK = "player_stats/stats_player_week_{season}.csv"
TEAM_WEEK = "stats_team/stats_team_week_{season}.csv"

# The weekly files are rebuilt after each slate, not during one, so a long TTL
# costs no freshness. Live score and clock come from ESPN; this is the slow
# layer underneath it.
TTL_SECONDS = 6 * 3600.0

# Hard ceiling on a single download. The weekly files run ~7 MB; anything an
# order of magnitude past that is a wrong URL or a changed release, and reading
# it into a 512 MB container is not worth finding out.
MAX_BYTES = 40 * 1024 * 1024

REQUEST_TIMEOUT = 30.0

# nflverse publishes a season once it starts, so the current year may 404 in
# the opening weeks. Walking back one year uses last season's form as the prior
# until this one exists — which is the right prior, and is labelled as such by
# `status()`. It deliberately does not reach further: a two-year-old season is
# not evidence about this one.
SEASON_LOOKBACK = 2


@dataclass
class PlayerWeek:
    """One player's line in one game."""
    player_id: str
    name: str
    position: str
    team: str
    opponent: str
    season: int
    week: int
    season_type: str            # REG | POST
    attempts: float = 0.0
    completions: float = 0.0
    passing_yards: float = 0.0
    passing_tds: float = 0.0
    passing_epa: Optional[float] = None
    carries: float = 0.0
    rushing_yards: float = 0.0
    rushing_tds: float = 0.0
    rushing_epa: Optional[float] = None
    targets: float = 0.0
    receptions: float = 0.0
    receiving_yards: float = 0.0
    receiving_tds: float = 0.0
    receiving_epa: Optional[float] = None
    target_share: Optional[float] = None


@dataclass
class TeamWeek:
    """One team's line in one game."""
    team: str
    opponent: str
    season: int
    week: int
    season_type: str
    passing_epa: Optional[float] = None
    rushing_epa: Optional[float] = None
    passing_yards: float = 0.0
    rushing_yards: float = 0.0
    points_for: Optional[float] = None


@dataclass
class TeamForm:
    """A team's season to date, from its own weekly rows and its opponents'."""
    team: str
    games: int = 0
    off_epa_per_game: Optional[float] = None
    def_epa_per_game: Optional[float] = None   # EPA allowed; lower is better
    off_yards_per_game: Optional[float] = None
    # Whether the EPA figures above account for who the team played. A raw
    # average and a schedule-adjusted one are different claims, so which one
    # this is has to travel with the number.
    opponent_adjusted: bool = False


@dataclass
class NflverseData:
    season: Optional[int] = None
    ok: bool = False
    note: str = ""
    fetched_at: str = ""
    players: list[PlayerWeek] = field(default_factory=list)
    teams: list[TeamWeek] = field(default_factory=list)


def _num(row: dict, key: str) -> Optional[float]:
    """CSV cells are strings; missing values arrive as '' or 'NA'."""
    raw = (row.get(key) or "").strip()
    if not raw or raw.upper() in ("NA", "NAN", "NULL"):
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _num0(row: dict, key: str) -> float:
    v = _num(row, key)
    return 0.0 if v is None else v


def _int(row: dict, key: str) -> int:
    v = _num(row, key)
    return 0 if v is None else int(v)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def current_season(now: Optional[datetime] = None) -> int:
    """
    The NFL season is labelled by the year it starts in, so anything before
    March belongs to the previous season's playoffs.
    """
    now = now or datetime.now(timezone.utc)
    return now.year if now.month >= 3 else now.year - 1


# ── fetching ─────────────────────────────────────────────────────────────────

_cache: dict[str, tuple[float, NflverseData]] = {}
_locks: dict[str, asyncio.Lock] = {}


def _lock_for(key: str) -> asyncio.Lock:
    lock = _locks.get(key)
    if lock is None:
        lock = _locks[key] = asyncio.Lock()
    return lock


async def _download_csv(path: str) -> tuple[Optional[str], str]:
    """
    Fetch one release asset. Returns (text, note); text is None on any failure,
    and the note always says what happened so the caller can report it.
    """
    url = f"{RELEASE_BASE}/{path}"
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
            async with client.stream("GET", url) as resp:
                if resp.status_code == 404:
                    return None, "not published yet"
                if resp.status_code >= 400:
                    return None, f"HTTP {resp.status_code}"
                buf = bytearray()
                async for chunk in resp.aiter_bytes():
                    buf += chunk
                    if len(buf) > MAX_BYTES:
                        return None, f"exceeded {MAX_BYTES // (1024 * 1024)} MB cap"
        return buf.decode("utf-8", errors="replace"), "ok"
    except httpx.HTTPError as exc:
        return None, f"request failed: {type(exc).__name__}"
    except Exception as exc:                              # pragma: no cover
        log.warning("nflverse download failed for %s: %s", path, exc)
        return None, f"unexpected error: {type(exc).__name__}"


def parse_player_weeks(text: str) -> list[PlayerWeek]:
    """Narrow the ~90-column player file to the fields a projection uses."""
    out: list[PlayerWeek] = []
    for row in csv.DictReader(io.StringIO(text)):
        pid = (row.get("player_id") or "").strip()
        team = (row.get("team") or "").strip().upper()
        if not pid or not team:
            continue
        out.append(PlayerWeek(
            player_id=pid,
            name=(row.get("player_display_name") or row.get("player_name") or "").strip(),
            position=(row.get("position") or "").strip().upper(),
            team=team,
            opponent=(row.get("opponent_team") or "").strip().upper(),
            season=_int(row, "season"),
            week=_int(row, "week"),
            season_type=(row.get("season_type") or "REG").strip().upper(),
            attempts=_num0(row, "attempts"),
            completions=_num0(row, "completions"),
            passing_yards=_num0(row, "passing_yards"),
            passing_tds=_num0(row, "passing_tds"),
            passing_epa=_num(row, "passing_epa"),
            carries=_num0(row, "carries"),
            rushing_yards=_num0(row, "rushing_yards"),
            rushing_tds=_num0(row, "rushing_tds"),
            rushing_epa=_num(row, "rushing_epa"),
            targets=_num0(row, "targets"),
            receptions=_num0(row, "receptions"),
            receiving_yards=_num0(row, "receiving_yards"),
            receiving_tds=_num0(row, "receiving_tds"),
            receiving_epa=_num(row, "receiving_epa"),
            target_share=_num(row, "target_share"),
        ))
    return out


def parse_team_weeks(text: str) -> list[TeamWeek]:
    out: list[TeamWeek] = []
    for row in csv.DictReader(io.StringIO(text)):
        team = (row.get("team") or "").strip().upper()
        if not team:
            continue
        out.append(TeamWeek(
            team=team,
            opponent=(row.get("opponent_team") or "").strip().upper(),
            season=_int(row, "season"),
            week=_int(row, "week"),
            season_type=(row.get("season_type") or "REG").strip().upper(),
            passing_epa=_num(row, "passing_epa"),
            rushing_epa=_num(row, "rushing_epa"),
            passing_yards=_num0(row, "passing_yards"),
            rushing_yards=_num0(row, "rushing_yards"),
        ))
    return out


async def load_season(season: Optional[int] = None) -> NflverseData:
    """
    Fetch and cache one season of weekly player and team stats.

    With no season given, walks back from the current one until a published
    file is found — early in a season the current year does not exist yet, and
    last year's form is a far better prior than none.
    """
    if season is not None:
        return await _load_one(season)

    start = current_season()
    tried: list[str] = []
    for year in range(start, start - SEASON_LOOKBACK, -1):
        data = await _load_one(year)
        if data.ok:
            return data
        tried.append(f"{year}: {data.note}")
    return NflverseData(ok=False, note="; ".join(tried) or "no season available", fetched_at=_now())


async def _load_one(season: int) -> NflverseData:
    key = str(season)
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < TTL_SECONDS:
        return hit[1]

    async with _lock_for(key):
        # Another request may have filled the cache while this one waited.
        hit = _cache.get(key)
        if hit and time.monotonic() - hit[0] < TTL_SECONDS:
            return hit[1]

        player_text, player_note = await _download_csv(PLAYER_WEEK.format(season=season))
        team_text, team_note = await _download_csv(TEAM_WEEK.format(season=season))

        players = parse_player_weeks(player_text) if player_text else []
        teams = parse_team_weeks(team_text) if team_text else []
        ok = bool(players or teams)
        note = "ok" if ok else f"players: {player_note}; teams: {team_note}"

        data = NflverseData(
            season=season if ok else None,
            ok=ok,
            note=note,
            fetched_at=_now(),
            players=players,
            teams=teams,
        )
        # A failed season is cached too, briefly, so a 404 during the offseason
        # does not mean a download attempt on every request.
        _cache[key] = (time.monotonic() if ok else time.monotonic() - TTL_SECONDS + 600.0, data)
        return data


# ── derived views ────────────────────────────────────────────────────────────

# Passes of opponent adjustment. Each pass re-reads every game against the
# current estimate of who the opponent was; three is enough to converge on an
# NFL schedule and cheap enough to run on every refresh.
SOS_PASSES = 3


def _mean_or(values: list[float], fallback: float = 0.0) -> float:
    return sum(values) / len(values) if values else fallback


def opponent_adjust(
    games: list[tuple[str, str, float]], passes: int = SOS_PASSES,
) -> tuple[dict[str, float], dict[str, float]]:
    """
    Split raw per-game EPA into offense and defence ratings that account for who
    each team played.

    `games` is (team, opponent, epa the team produced). A raw average punishes
    an offence that faced the best defences and flatters one that did not — the
    difference between a 9-1 team that beat nobody and a 7-3 team that beat
    everybody. Each pass re-scores a performance against what its opponent
    normally allows, then re-centres so the league still averages zero.

    Returns (offense, defence) as deviations from league average, where a
    positive defence number means *more* EPA allowed — worse.
    """
    teams = {t for t, _, _ in games} | {o for _, o, _ in games if o}
    offense = {t: 0.0 for t in teams}
    defence = {t: 0.0 for t in teams}
    if not games:
        return offense, defence

    league_mean = _mean_or([e for _, _, e in games])

    for _ in range(max(1, passes)):
        new_off: dict[str, list[float]] = {t: [] for t in teams}
        new_def: dict[str, list[float]] = {t: [] for t in teams}
        for team, opp, epa in games:
            # What this performance was worth once the opponent's usual
            # concession is taken out of it.
            new_off[team].append(epa - league_mean - defence.get(opp, 0.0))
            if opp in new_def:
                new_def[opp].append(epa - league_mean - offense.get(team, 0.0))

        offense = {t: _mean_or(v) for t, v in new_off.items()}
        defence = {t: _mean_or(v) for t, v in new_def.items()}
        # Re-centre so the ratings stay deviations and cannot drift together.
        off_mean = _mean_or(list(offense.values()))
        def_mean = _mean_or(list(defence.values()))
        offense = {t: v - off_mean for t, v in offense.items()}
        defence = {t: v - def_mean for t, v in defence.items()}

    return offense, defence


def team_form(
    data: NflverseData, *, season_type: str = "REG", adjust_for_opponent: bool = True,
) -> dict[str, TeamForm]:
    """
    Per-team offensive and defensive EPA per game.

    Defence is derived by attributing each team-week's offensive EPA to the
    opponent it was produced against — nflverse's team file is offense-side, so
    "EPA allowed" is the same rows read from the other direction.

    With `adjust_for_opponent` (the default) the numbers are strength-of-
    schedule adjusted, so a team is not rated up for having played nobody. The
    raw averages remain available for comparison by passing False.
    """
    games: list[tuple[str, str, float]] = []
    yards: dict[str, list[float]] = {}
    raw_off: dict[str, list[float]] = {}
    raw_allowed: dict[str, list[float]] = {}

    for row in data.teams:
        if season_type and row.season_type != season_type:
            continue
        epa = None
        if row.passing_epa is not None or row.rushing_epa is not None:
            epa = (row.passing_epa or 0.0) + (row.rushing_epa or 0.0)
        if epa is not None:
            raw_off.setdefault(row.team, []).append(epa)
            if row.opponent:
                raw_allowed.setdefault(row.opponent, []).append(epa)
                games.append((row.team, row.opponent, epa))
        yards.setdefault(row.team, []).append(row.passing_yards + row.rushing_yards)

    adj_off: dict[str, float] = {}
    adj_def: dict[str, float] = {}
    if adjust_for_opponent and games:
        adj_off, adj_def = opponent_adjust(games)

    forms: dict[str, TeamForm] = {}
    for team in set(raw_off) | set(yards) | set(raw_allowed):
        o, a, y = raw_off.get(team, []), raw_allowed.get(team, []), yards.get(team, [])
        if team in adj_off:
            off_val: Optional[float] = adj_off[team]
            def_val: Optional[float] = adj_def.get(team)
        else:
            off_val = (sum(o) / len(o)) if o else None
            def_val = (sum(a) / len(a)) if a else None
        forms[team] = TeamForm(
            team=team,
            games=len(y) or len(o),
            off_epa_per_game=off_val,
            def_epa_per_game=def_val,
            off_yards_per_game=(sum(y) / len(y)) if y else None,
            opponent_adjusted=team in adj_off,
        )
    return forms


@dataclass
class PlayerForm:
    """A player's per-game averages over the games they actually played."""
    player_id: str
    name: str
    position: str
    team: str
    games: int
    pass_attempts_pg: Optional[float] = None
    pass_yards_pg: Optional[float] = None
    pass_tds_pg: Optional[float] = None
    carries_pg: Optional[float] = None
    rush_yards_pg: Optional[float] = None
    rush_tds_pg: Optional[float] = None
    targets_pg: Optional[float] = None
    receptions_pg: Optional[float] = None
    rec_yards_pg: Optional[float] = None
    rec_tds_pg: Optional[float] = None
    target_share: Optional[float] = None


def _mean(values: Iterable[float]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def player_form(
    data: NflverseData,
    *,
    team: Optional[str] = None,
    last_n: int = 0,
    season_type: str = "REG",
) -> list[PlayerForm]:
    """
    Aggregate weekly rows into per-game form.

    `last_n` limits to a player's most recent N games — recent form, not a
    season average diluted by a role they no longer have.
    """
    want = (team or "").strip().upper()
    by_player: dict[str, list[PlayerWeek]] = {}
    for row in data.players:
        if season_type and row.season_type != season_type:
            continue
        if want and row.team != want:
            continue
        by_player.setdefault(row.player_id, []).append(row)

    out: list[PlayerForm] = []
    for pid, rows in by_player.items():
        rows.sort(key=lambda r: (r.season, r.week))
        if last_n > 0:
            rows = rows[-last_n:]
        if not rows:
            continue
        latest = rows[-1]
        out.append(PlayerForm(
            player_id=pid,
            name=latest.name,
            position=latest.position,
            team=latest.team,
            games=len(rows),
            pass_attempts_pg=_mean(r.attempts for r in rows),
            pass_yards_pg=_mean(r.passing_yards for r in rows),
            pass_tds_pg=_mean(r.passing_tds for r in rows),
            carries_pg=_mean(r.carries for r in rows),
            rush_yards_pg=_mean(r.rushing_yards for r in rows),
            rush_tds_pg=_mean(r.rushing_tds for r in rows),
            targets_pg=_mean(r.targets for r in rows),
            receptions_pg=_mean(r.receptions for r in rows),
            rec_yards_pg=_mean(r.receiving_yards for r in rows),
            rec_tds_pg=_mean(r.receiving_tds for r in rows),
            target_share=_mean(r.target_share for r in rows if r.target_share is not None),
        ))
    out.sort(key=lambda p: -(p.pass_yards_pg or 0.0) - (p.rush_yards_pg or 0.0) - (p.rec_yards_pg or 0.0))
    return out


def status() -> dict:
    """What this provider is actually doing right now — no credentials to leak."""
    now = current_season()
    live = [
        {"season": data.season, "players": len(data.players), "teams": len(data.teams),
         "fetched_at": data.fetched_at, "is_current_season": data.season == now}
        for _, data in _cache.values() if data.ok
    ]
    stale = [row for row in live if not row["is_current_season"]]
    if not live:
        note = "no season loaded yet"
    elif stale:
        # Not an error, but not the current season either, and the difference
        # matters to anyone reading a projection built on it.
        note = (f"running on {stale[0]['season']} form; "
                f"{now} is not published by nflverse yet")
    else:
        note = ""
    return {
        "provider": "nflverse",
        "requires_key": False,
        "configured": True,
        "leagues": ["nfl"],
        "current_season": now,
        "loaded": live,
        "note": note,
    }


def reset_cache() -> None:
    _cache.clear()
