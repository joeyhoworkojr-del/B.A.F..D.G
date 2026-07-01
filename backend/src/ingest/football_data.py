"""
Live sports data via football-data.org (free tier, requires API key).

Free tier: 10 requests/minute, major competitions only.
Set FOOTBALL_DATA_API_KEY in .env to enable. Falls back to cached/synthetic data.

Docs: https://www.football-data.org/documentation/quickstart
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from src.config import settings

log = logging.getLogger(__name__)

BASE_URL = "https://api.football-data.org/v4"

# 2026 World Cup competition ID (FIFA WC 2026)
WC_2026_ID = 2000   # update once football-data.org assigns the official ID


@dataclass
class LiveMatch:
    id: int
    home: str
    away: str
    home_score: Optional[int]
    away_score: Optional[int]
    status: str        # "IN_PLAY" | "PAUSED" | "FINISHED" | "SCHEDULED"
    minute: Optional[int]
    stage: str


@dataclass
class LiveScoreboard:
    matches: list[LiveMatch]
    source: str = "football-data.org"


def _headers() -> dict[str, str]:
    key = settings.football_data_api_key if hasattr(settings, "football_data_api_key") else ""
    return {"X-Auth-Token": key} if key else {}


async def fetch_live_matches(competition_id: int = WC_2026_ID) -> LiveScoreboard:
    """
    Fetch currently live and today's scheduled matches.
    Returns empty scoreboard if API key is missing or request fails.
    """
    key = getattr(settings, "football_data_api_key", "")
    if not key:
        log.info("FOOTBALL_DATA_API_KEY not set — live scores disabled")
        return LiveScoreboard(matches=[], source="unavailable — set FOOTBALL_DATA_API_KEY")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{BASE_URL}/competitions/{competition_id}/matches",
                params={"status": "LIVE,IN_PLAY,PAUSED,SCHEDULED"},
                headers=_headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        matches = []
        for m in data.get("matches", []):
            score = m.get("score", {})
            ft = score.get("fullTime", {})
            matches.append(LiveMatch(
                id=m["id"],
                home=m["homeTeam"]["tla"] or m["homeTeam"]["name"],
                away=m["awayTeam"]["tla"] or m["awayTeam"]["name"],
                home_score=ft.get("home"),
                away_score=ft.get("away"),
                status=m["status"],
                minute=m.get("minute"),
                stage=m.get("stage", ""),
            ))

        return LiveScoreboard(matches=matches)
    except httpx.HTTPError as exc:
        log.error("football-data.org fetch failed: %s", exc)
        return LiveScoreboard(matches=[], source=f"error: {exc}")


async def fetch_standings(competition_id: int = WC_2026_ID) -> dict:
    """Fetch group standings."""
    key = getattr(settings, "football_data_api_key", "")
    if not key:
        return {"error": "FOOTBALL_DATA_API_KEY not set"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{BASE_URL}/competitions/{competition_id}/standings",
                headers=_headers(),
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        return {"error": str(exc)}
