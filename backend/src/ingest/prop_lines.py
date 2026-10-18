"""
Sportsbook player-prop lines.

StatEdge has always been able to project a player's production. What it has
never had is the number a book is actually offering, and without that there is
no edge to speak of: a projection of 284 passing yards is interesting, but
"284 against a posted 267.5" is the product.

ESPN's feeds carry game lines and no player props, so this needs a dedicated
odds provider. The Odds API is the integration here because its player-prop
markets are documented, per-event and priced per book, which is what lets a
best-price comparison be real rather than decorative.

No key, no lines. That is reported as exactly that — `ok=False` with a note
naming the variable to set — and never as "no edge found", because those are
different statements and only one of them is true.

    fly secrets set ODDS_API_KEY=... --app statedge-api

Costs: the per-event player-prop endpoint is billed per market per region, so
lines are fetched per game on demand and cached, not swept across a slate.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import httpx

log = logging.getLogger(__name__)

KEY_ENV_VAR = "ODDS_API_KEY"
BASE = "https://api.the-odds-api.com/v4"
SPORT_KEYS = {"nfl": "americanfootball_nfl", "ncaaf": "americanfootball_ncaaf"}

# Our market key → the provider's. Only markets we actually project are asked
# for, because each one is billed separately.
MARKET_MAP = {
    "pass_yards": "player_pass_yds",
    "pass_attempts": "player_pass_attempts",
    "pass_tds": "player_pass_tds",
    "rush_yards": "player_rush_yds",
    "carries": "player_rush_attempts",
    "rec_yards": "player_reception_yds",
    "receptions": "player_receptions",
}
REVERSE_MARKET = {v: k for k, v in MARKET_MAP.items()}

# Lines move, but not every few seconds, and every call costs quota.
CACHE_TTL_SECONDS = 180.0
REQUEST_TIMEOUT = 12.0

_cache: dict[str, tuple[float, "PropLines"]] = {}
_last_fetch: dict[str, dict] = {}


@dataclass
class PriceAtBook:
    book: str
    line: float
    over_price: Optional[float] = None
    under_price: Optional[float] = None


@dataclass
class PropLine:
    """Every book's price on one player's one market, and the best of them."""
    player: str
    market: str
    prices: list[PriceAtBook] = field(default_factory=list)

    def _best(self, side: str) -> Optional[PriceAtBook]:
        """
        The book paying most on a side.

        Compared on American prices, where "most" means the largest number:
        +120 beats +110 beats -105 beats -115. Straight numeric comparison gets
        that right across the sign change, which is the only subtlety.
        """
        attr = "over_price" if side == "over" else "under_price"
        priced = [p for p in self.prices if getattr(p, attr) is not None]
        if not priced:
            return None
        return max(priced, key=lambda p: getattr(p, attr))

    @property
    def consensus_line(self) -> Optional[float]:
        """The median posted line, which is the number to compare against."""
        lines = sorted(p.line for p in self.prices)
        if not lines:
            return None
        mid = len(lines) // 2
        return lines[mid] if len(lines) % 2 else (lines[mid - 1] + lines[mid]) / 2.0

    def best_over(self) -> Optional[PriceAtBook]:
        return self._best("over")

    def best_under(self) -> Optional[PriceAtBook]:
        return self._best("under")


@dataclass
class PropLines:
    league: str
    event_id: str = ""
    ok: bool = False
    source: str = "The Odds API"
    note: str = ""
    fetched_at: str = ""
    books: list[str] = field(default_factory=list)
    # (normalised player, our market key) → the line
    lines: dict[tuple[str, str], PropLine] = field(default_factory=dict)
    # How many posted lines could not be matched to a projected player. Carried
    # rather than swallowed: a quiet mismatch would look like a thin market.
    unmatched: int = 0

    def for_player(self, player: str, market: str) -> Optional[PropLine]:
        return self.lines.get((normalise_name(player), market))


def api_key() -> str:
    return (os.getenv(KEY_ENV_VAR) or "").strip()


_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def normalise_name(name: str) -> str:
    """
    A key that matches the same player across three feeds that spell him
    differently.

    ESPN publishes "J. Allen", nflverse "J.Allen", a book "Josh Allen". The
    only parts all three agree on are the surname and the first initial, so
    that is the key: "allen:j". Generational suffixes are dropped because the
    feeds disagree about those too.

    This is deliberately not a fuzzy match. Two players on one roster sharing a
    surname and an initial would collide, and a wrong line attached to the
    right name is worse than no line — so the caller counts what did not match
    instead of reaching for a closest guess.
    """
    raw = (name or "").lower()
    # "Allen, Josh" is the same player as "Josh Allen"; flipping it first means
    # the surname is in the place the rest of this function expects.
    if "," in raw:
        last, _, first = raw.partition(",")
        raw = f"{first.strip()} {last.strip()}"
    cleaned = re.sub(r"[^a-z\s.]", "", raw)
    parts = [p.strip(" .") for p in cleaned.replace(".", " ").split() if p.strip(" .")]
    parts = [p for p in parts if p not in _SUFFIXES]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return f"{parts[-1]}:{parts[0][0]}"


def _record(key: str, *, ok: bool, lines: int = 0, books: int = 0,
            unmatched: int = 0, error: str = "") -> None:
    _last_fetch[key] = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ok": ok, "lines": lines, "books": books,
        "unmatched": unmatched, "error": error,
    }


def fetch_report() -> dict:
    return dict(_last_fetch)


def status() -> dict:
    """For the public data-sources page. Never reports the key itself."""
    configured = bool(api_key())
    report = fetch_report()
    worked = any(r.get("ok") and r.get("lines") for r in report.values())
    return {
        "provider": "The Odds API (player props)",
        "requires_key": True,
        "key_env_var": KEY_ENV_VAR,
        "configured": configured,
        "leagues": list(SPORT_KEYS),
        "markets": sorted(MARKET_MAP),
        "last_success": worked,
        "last_error": "" if configured else f"set {KEY_ENV_VAR} to price player props",
        "note": (
            "Player prop lines and prices per book."
            if configured else
            "Not configured, so prop projections are published without lines "
            "and no prop edge is claimed."
        ),
        "last_fetch": report,
    }


def _parse_event(league: str, event: dict, wanted: set[str]) -> PropLines:
    """Turn one provider event into lines keyed by player and market."""
    out = PropLines(
        league=league, event_id=str(event.get("id") or ""), ok=True,
        fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    books: set[str] = set()
    for book in event.get("bookmakers") or []:
        title = (book.get("title") or book.get("key") or "").strip()
        for market in book.get("markets") or []:
            ours = REVERSE_MARKET.get(market.get("key") or "")
            if ours is None:
                continue
            for outcome in market.get("outcomes") or []:
                # The player's name is in `description`; `name` is Over/Under.
                player = (outcome.get("description") or "").strip()
                side = (outcome.get("name") or "").strip().lower()
                point, price = outcome.get("point"), outcome.get("price")
                if not player or point is None or price is None:
                    continue
                key = (normalise_name(player), ours)
                if wanted and key[0] not in wanted:
                    out.unmatched += 1
                    continue
                line = out.lines.get(key)
                if line is None:
                    line = out.lines[key] = PropLine(player=player, market=ours)
                at = next(
                    (p for p in line.prices
                     if p.book == title and abs(p.line - float(point)) < 1e-9),
                    None,
                )
                if at is None:
                    at = PriceAtBook(book=title, line=float(point))
                    line.prices.append(at)
                if side == "over":
                    at.over_price = float(price)
                elif side == "under":
                    at.under_price = float(price)
                books.add(title)
    out.books = sorted(books)
    return out


def _matches(event: dict, home: str, away: str) -> bool:
    """
    Is this the provider's record of our game?

    Matched on both team names, each compared on surname-style normalisation of
    the last word, because "LA Rams" and "Los Angeles Rams" are the same team
    and an event id from one feed means nothing in another.
    """
    def tail(name: str) -> str:
        parts = re.sub(r"[^a-z\s]", "", (name or "").lower()).split()
        return parts[-1] if parts else ""

    return (tail(event.get("home_team", "")) == tail(home)
            and tail(event.get("away_team", "")) == tail(away))


async def fetch_prop_lines(
    league: str, event_id: str, home: str, away: str,
    players: Optional[list[str]] = None,
) -> PropLines:
    """
    Posted prop lines for one game, priced across books. Never raises.

    `players` is the projected squad; lines for anyone not in it are counted as
    unmatched rather than kept, so what comes back lines up with what is on the
    page.
    """
    league = league.lower()
    sport = SPORT_KEYS.get(league)
    key = api_key()
    cache_key = f"{league}:{event_id}"

    if sport is None:
        return PropLines(league=league, event_id=event_id,
                         note=f"unsupported league {league!r}")
    if not key:
        return PropLines(
            league=league, event_id=event_id, ok=False,
            note=(
                f"No odds provider configured. Set {KEY_ENV_VAR} to price "
                "player props; until then projections are published without "
                "lines and no prop edge is claimed."
            ),
        )

    hit = _cache.get(cache_key)
    if hit and time.monotonic() - hit[0] < CACHE_TTL_SECONDS:
        return hit[1]

    wanted = {normalise_name(p) for p in (players or []) if p}
    markets = ",".join(sorted(MARKET_MAP.values()))
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            # The event list first: the provider's own ids are needed for the
            # per-event prop endpoint, and they are not ESPN's.
            listing = await client.get(
                f"{BASE}/sports/{sport}/events",
                params={"apiKey": key},
            )
            listing.raise_for_status()
            event = next(
                (e for e in listing.json() or [] if _matches(e, home, away)), None,
            )
            if event is None:
                _record(cache_key, ok=True, error="game not listed by the provider")
                out = PropLines(
                    league=league, event_id=event_id, ok=True,
                    note="The odds provider is not listing this game yet.",
                    fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                )
                _cache[cache_key] = (time.monotonic(), out)
                return out

            priced = await client.get(
                f"{BASE}/sports/{sport}/events/{event['id']}/odds",
                params={"apiKey": key, "markets": markets,
                        "oddsFormat": "american", "regions": "us"},
            )
            priced.raise_for_status()
            out = _parse_event(league, priced.json() or {}, wanted)
    except Exception as exc:
        log.warning("prop lines fetch failed for %s: %s", cache_key, exc)
        _record(cache_key, ok=False, error=f"{type(exc).__name__}: {exc}"[:200])
        return PropLines(
            league=league, event_id=event_id, ok=False,
            note="The odds provider is temporarily unreachable.",
        )

    out.event_id = event_id
    if not out.lines:
        out.note = "The provider is listing no player props for this game yet."
    _record(cache_key, ok=True, lines=len(out.lines),
            books=len(out.books), unmatched=out.unmatched)
    _cache[cache_key] = (time.monotonic(), out)
    return out


def clear_cache() -> None:
    _cache.clear()
