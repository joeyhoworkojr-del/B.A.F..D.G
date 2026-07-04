"""
Polymarket prediction-market prices via the public (keyless) Gamma API.

Prediction markets are real money on real probabilities — a sharper crowd
signal than sportsbook lines in some spots. We match open game markets to
our slate by team nickname and expose the crowd's implied probabilities
plus traded volume.

Responses cached 120s. Every failure degrades to "no data" — never breaks
a prediction.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

log = logging.getLogger(__name__)

GAMMA_BASE = "https://gamma-api.polymarket.com"

# Gamma tag slugs per league (CFL has no Polymarket coverage today — fine)
LEAGUE_TAGS: dict[str, str] = {
    "mlb": "mlb",
    "nfl": "nfl",
    "cfl": "cfl",
    "wc": "fifa-world-cup",
}

CACHE_TTL_SECONDS = 120.0
_cache: dict[str, tuple[float, list["PolyMarket"]]] = {}


@dataclass
class PolyMarket:
    slug: str
    title: str
    outcomes: list[str]          # e.g. ["Yankees", "Red Sox"]
    prices: list[float]          # aligned with outcomes, sum ≈ 1
    volume_usd: float
    url: str


def _listify(v) -> list:
    """Gamma returns outcomes/outcomePrices as JSON-encoded strings."""
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except json.JSONDecodeError:
            return []
    return v if isinstance(v, list) else []


def _parse_event(ev: dict) -> Optional[PolyMarket]:
    try:
        slug = ev.get("slug", "")
        title = ev.get("title", "") or ev.get("question", "")
        best: Optional[tuple[list[str], list[float], float]] = None
        for mk in ev.get("markets", []) or []:
            outcomes = [str(o) for o in _listify(mk.get("outcomes"))]
            prices = [float(p) for p in _listify(mk.get("outcomePrices"))]
            if len(outcomes) != 2 or len(prices) != 2:
                continue
            vol = float(mk.get("volume") or ev.get("volume") or 0.0)
            # Prefer team-vs-team (non Yes/No) markets, then highest volume
            is_team = {o.lower() for o in outcomes} != {"yes", "no"}
            score = (1 if is_team else 0, vol)
            if best is None or score > (1 if {o.lower() for o in best[0]} != {"yes", "no"} else 0, best[2]):
                best = (outcomes, prices, vol)
        if best is None:
            return None
        outcomes, prices, vol = best
        total = sum(prices)
        if total <= 0:
            return None
        return PolyMarket(
            slug=slug,
            title=title,
            outcomes=outcomes,
            prices=[p / total for p in prices],
            volume_usd=vol,
            url=f"https://polymarket.com/event/{slug}" if slug else "https://polymarket.com",
        )
    except Exception:
        return None


async def fetch_league_markets(league: str) -> list[PolyMarket]:
    """Open game markets for a league. Never raises."""
    league = league.lower()
    tag = LEAGUE_TAGS.get(league)
    if tag is None:
        return []

    cached = _cache.get(league)
    if cached and time.monotonic() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{GAMMA_BASE}/events",
                params={"closed": "false", "tag_slug": tag, "limit": 200},
            )
            resp.raise_for_status()
            data = resp.json()
        markets = [m for m in (_parse_event(ev) for ev in data or []) if m]
        _cache[league] = (time.monotonic(), markets)
        return markets
    except Exception as exc:
        log.error("Polymarket fetch failed for %s: %s", league, exc)
        return []


def _nickname(display_name: str) -> str:
    """'Kansas City Chiefs' → 'chiefs'; 'St. Louis Cardinals' → 'cardinals'."""
    parts = display_name.strip().split()
    return parts[-1].lower() if parts else ""


def match_game(
    markets: list[PolyMarket],
    home_name: str,
    away_name: str,
) -> Optional[dict]:
    """
    Find the market for a game and return crowd probabilities keyed to our
    home/away orientation: {home_prob, away_prob, volume_usd, url, title}.
    """
    h, a = _nickname(home_name), _nickname(away_name)
    if not h or not a:
        return None

    for m in markets:
        title_l = m.title.lower()
        outs_l = [o.lower() for o in m.outcomes]
        in_title = h in title_l and a in title_l
        in_outcomes = any(h in o for o in outs_l) and any(a in o for o in outs_l)
        if not (in_title or in_outcomes):
            continue

        home_prob: Optional[float] = None
        if in_outcomes:
            for o, p in zip(outs_l, m.prices):
                if h in o:
                    home_prob = p
                    break
        elif outs_l and {*outs_l} == {"yes", "no"}:
            # "Will <team> beat <team>?" — Yes maps to the first team named
            yes_idx = outs_l.index("yes")
            first_is_home = title_l.find(h) < title_l.find(a)
            home_prob = m.prices[yes_idx] if first_is_home else 1 - m.prices[yes_idx]
        if home_prob is None:
            continue

        return {
            "home_prob": home_prob,
            "away_prob": 1.0 - home_prob,
            "volume_usd": m.volume_usd,
            "url": m.url,
            "title": m.title,
        }
    return None
