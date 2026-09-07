"""News ingest: parsing, attribution, and the projection-honesty contract."""
from __future__ import annotations

import pytest

from src.ingest import news


ARTICLE = {
    "id": 12345,
    "headline": "Starting QB ruled out for Saturday",
    "description": "The junior will miss the game with an ankle injury.",
    "published": "2026-09-05T18:30:00Z",
    "byline": "Staff",
    "type": "Story",
    "links": {"web": {"href": "https://www.espn.com/story/12345"}},
    "images": [{"url": "https://a.espncdn.com/photo.jpg"}],
    "categories": [
        {"team": {"abbreviation": "FSU"}},
        {"team": {"abbreviation": "FSU"}},
        {"team": {"shortName": "CLEM"}},
    ],
}


def test_parses_headline_summary_and_link():
    item = news._parse_article("ncaaf", ARTICLE)
    assert item is not None
    assert item.headline == "Starting QB ruled out for Saturday"
    # ESPN's own summary line — never a full article body.
    assert item.description == "The junior will miss the game with an ankle injury."
    assert item.url == "https://www.espn.com/story/12345"
    assert item.source == "ESPN"


def test_publish_stamp_normalised_to_utc_iso():
    item = news._parse_article("nfl", ARTICLE)
    assert item.published == "2026-09-05T18:30:00+00:00"


def test_unparseable_publish_stamp_is_blank_not_fatal():
    item = news._parse_article("nfl", {**ARTICLE, "published": "last tuesday"})
    assert item.published == ""


def test_teams_deduplicated_in_order():
    item = news._parse_article("ncaaf", ARTICLE)
    assert item.teams == ["FSU", "CLEM"]


def test_injury_language_is_categorised_as_injury():
    item = news._parse_article("ncaaf", ARTICLE)
    assert item.category == "injury"


def test_plain_story_is_categorised_as_news():
    plain = {**ARTICLE, "headline": "Week 2 power rankings",
             "description": "Where every team stands.", "categories": []}
    assert news._parse_article("nfl", plain).category == "news"


def test_article_without_a_headline_is_dropped():
    assert news._parse_article("nfl", {**ARTICLE, "headline": "  "}) is None


@pytest.mark.asyncio
async def test_unknown_league_reports_not_ok_instead_of_raising():
    feed = await news.fetch_news("cricket")
    assert feed.ok is False
    assert feed.items == []


@pytest.mark.asyncio
async def test_fetch_failure_reports_not_ok_instead_of_raising(monkeypatch):
    news._cache.clear()

    class Boom:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, *a, **k): raise RuntimeError("network down")

    monkeypatch.setattr(news.httpx, "AsyncClient", lambda **k: Boom())
    feed = await news.fetch_news("nfl")
    assert feed.ok is False
    assert feed.items == []
    assert "unreachable" in feed.source


@pytest.mark.asyncio
async def test_items_are_sorted_newest_first(monkeypatch):
    news._cache.clear()
    payload = {"articles": [
        {**ARTICLE, "id": 1, "published": "2026-09-01T12:00:00Z"},
        {**ARTICLE, "id": 2, "published": "2026-09-06T12:00:00Z"},
        {**ARTICLE, "id": 3, "published": "2026-09-03T12:00:00Z"},
    ]}

    class Stub:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, *a, **k):
            class R:
                def raise_for_status(self): pass
                def json(self): return payload
            return R()

    monkeypatch.setattr(news.httpx, "AsyncClient", lambda **k: Stub())
    feed = await news.fetch_news("nfl")
    assert [i.id for i in feed.items] == ["2", "3", "1"]
