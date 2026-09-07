"""
League news via ESPN's public (keyless) site API.

Same source and terms as the scoreboard feed the rest of the app already uses,
so it needs no credentials. Only the headline, ESPN's own one-line description,
the byline and a link back to the article are carried — full article bodies are
never fetched or reproduced. Every item keeps its source and canonical URL so
the UI can attribute it.

The model does not consume these articles. Anything the UI says about a story's
effect on a projection must therefore read "Not yet reflected in projection"
unless the projection itself changed for a reason recorded in the ledger.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import httpx

from .espn import ESPN_BASE, LEAGUE_PATHS

log = logging.getLogger(__name__)

# News moves slower than a scoreboard; a 5-minute cache keeps the page snappy
# without hammering the upstream feed.
NEWS_TTL_SECONDS = 300.0
_cache: dict[str, tuple[float, list["NewsItem"]]] = {}

SOURCE_NAME = "ESPN"


@dataclass
class NewsItem:
    league: str
    id: str
    headline: str
    description: str
    published: str            # ISO-8601 UTC
    byline: str = ""
    url: str = ""             # canonical link back to the publisher
    image: str = ""
    category: str = "news"    # news | injury | preview | recap
    teams: list[str] = field(default_factory=list)   # team abbreviations
    source: str = SOURCE_NAME


@dataclass
class NewsFeed:
    league: str
    items: list[NewsItem] = field(default_factory=list)
    fetched_at: str = ""
    ok: bool = True
    source: str = SOURCE_NAME


def _iso(raw: Optional[str]) -> str:
    """Normalise ESPN's publish stamp to ISO-8601 UTC; blank if unparseable."""
    if not raw:
        return ""
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def _category(article: dict) -> str:
    """Map ESPN's loose `type` field onto the four buckets the UI filters on."""
    raw = (article.get("type") or "").strip().lower()
    text = f"{article.get('headline', '')} {article.get('description', '')}".lower()
    if raw in {"injury", "injuries"} or "injur" in text or "questionable" in text or "ruled out" in text:
        return "injury"
    if raw in {"preview"}:
        return "preview"
    if raw in {"recap"}:
        return "recap"
    return "news"


def _teams(article: dict) -> list[str]:
    """Team abbreviations tagged on the article, de-duplicated, order kept."""
    out: list[str] = []
    for cat in article.get("categories", []) or []:
        team = cat.get("team") or {}
        abbr = team.get("abbreviation") or team.get("shortName") or ""
        if abbr and abbr not in out:
            out.append(str(abbr))
    return out


def _link(article: dict) -> str:
    links = article.get("links") or {}
    for key in ("web", "mobile"):
        href = ((links.get(key) or {}).get("href") or "").strip()
        if href:
            return href
    return ""


def _image(article: dict) -> str:
    for img in article.get("images", []) or []:
        url = (img.get("url") or "").strip()
        if url:
            return url
    return ""


def _parse_article(league: str, article: dict) -> Optional[NewsItem]:
    headline = (article.get("headline") or "").strip()
    if not headline:
        return None
    return NewsItem(
        league=league,
        id=str(article.get("id") or _link(article) or headline),
        headline=headline,
        # ESPN's own summary line, not the article body.
        description=(article.get("description") or "").strip(),
        published=_iso(article.get("published") or article.get("lastModified")),
        byline=(article.get("byline") or "").strip(),
        url=_link(article),
        image=_image(article),
        category=_category(article),
        teams=_teams(article),
    )


async def fetch_news(league: str, limit: int = 30) -> NewsFeed:
    """Latest league news. Never raises — ok=False on failure."""
    league = league.lower()
    path = LEAGUE_PATHS.get(league)
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if path is None:
        return NewsFeed(league=league, ok=False, fetched_at=now_iso,
                        source=f"unknown league {league!r}")

    cached = _cache.get(league)
    if cached and time.monotonic() - cached[0] < NEWS_TTL_SECONDS:
        return NewsFeed(league=league, items=cached[1][:limit], fetched_at=now_iso)

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(f"{ESPN_BASE}/{path}/news", params={"limit": 50})
            resp.raise_for_status()
            data = resp.json()
        items = [i for i in (_parse_article(league, a) for a in data.get("articles", []) or []) if i]
        items.sort(key=lambda i: i.published, reverse=True)
        _cache[league] = (time.monotonic(), items)
        return NewsFeed(league=league, items=items[:limit], fetched_at=now_iso)
    except Exception as exc:
        log.error("ESPN news fetch failed for %s: %s", league, exc)
        return NewsFeed(league=league, ok=False, fetched_at=now_iso,
                        source=f"{SOURCE_NAME} (temporarily unreachable)")


async def fetch_news_multi(leagues: tuple[str, ...], limit: int = 30) -> NewsFeed:
    """Merged, newest-first news across several leagues."""
    feeds = await asyncio.gather(*(fetch_news(lg, limit=limit) for lg in leagues))
    items: list[NewsItem] = []
    for feed in feeds:
        items.extend(feed.items)
    items.sort(key=lambda i: i.published, reverse=True)
    return NewsFeed(
        league="+".join(leagues),
        items=items[:limit],
        fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ok=any(f.ok for f in feeds),
    )
