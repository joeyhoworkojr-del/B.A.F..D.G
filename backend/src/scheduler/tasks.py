"""
Celery tasks — tiered data ingestion pipeline.

Each task is idempotent (upsert by natural key) so re-running never
duplicates or corrupts data.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.scheduler.app import celery_app

log = logging.getLogger(__name__)


# ─── Tier 1: Completed game results ──────────────────────────────────────────

@celery_app.task(name="src.scheduler.tasks.ingest_completed_games", bind=True, max_retries=3)
def ingest_completed_games(self) -> dict:  # type: ignore[override]
    """
    Fetch and upsert completed game results.
    Runs every 5 minutes on game days.
    Idempotent: re-fetch returns same rows, upsert by (sport, provider_id).
    """
    try:
        # TODO(Phase 6): replace stub with real provider call:
        #   from src.ingest.providers.cfbd import CFBDProvider
        #   games = CFBDProvider().fetch_completed_games()
        #   for game in games: db.upsert_game(game)
        log.info("ingest_completed_games: stub — wiring real provider in Phase 6")
        return {
            "status": "ok",
            "fetched": 0,
            "upserted": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        log.error("ingest_completed_games failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=60) from exc


# ─── Tier 2: Live in-game state ───────────────────────────────────────────────
# Handled by a dedicated WebSocket consumer (not a beat task).
# Kept here as a health-check probe only.

@celery_app.task(name="src.scheduler.tasks.probe_live_scores", bind=True)
def probe_live_scores(self) -> dict:  # type: ignore[override]
    """
    Poll football-data.org for live match scores.
    Only meaningful while a game is IN_PLAY — returns noop otherwise.
    """
    import asyncio
    try:
        from src.ingest.football_data import fetch_live_matches
        board = asyncio.run(fetch_live_matches())
        live = [m for m in board.matches if m.status in ("IN_PLAY", "PAUSED")]
        log.info("probe_live_scores: %d live games", len(live))
        return {"status": "ok", "live_games": len(live), "source": board.source}
    except Exception as exc:
        log.warning("probe_live_scores failed: %s", exc)
        return {"status": "error", "live_games": 0}


# ─── Tier 3: Injury reports ───────────────────────────────────────────────────

@celery_app.task(name="src.scheduler.tasks.ingest_injury_reports", bind=True, max_retries=3)
def ingest_injury_reports(self) -> dict:  # type: ignore[override]
    """
    Fetch injury reports (NFL: Wed/Thu/Fri practice reports; soccer: daily).
    Runs hourly.
    """
    try:
        # TODO(Phase 6): integrate with injury feed provider
        log.info("ingest_injury_reports: stub")
        return {"status": "ok", "reports": 0}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120) from exc


# ─── Tier 4: Starting lineups ─────────────────────────────────────────────────

@celery_app.task(name="src.scheduler.tasks.ingest_lineups", bind=True, max_retries=3)
def ingest_lineups(self) -> dict:  # type: ignore[override]
    """
    Fetch confirmed starting XIs / depth charts.
    Runs every 10 minutes starting 2 hours before kickoff.
    """
    try:
        # TODO(Phase 6): integrate lineup provider (SportRadar or official league feed)
        log.info("ingest_lineups: stub")
        return {"status": "ok", "lineups_fetched": 0}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30) from exc


# ─── Tier 5: Weather ─────────────────────────────────────────────────────────

@celery_app.task(name="src.scheduler.tasks.ingest_weather", bind=True, max_retries=3)
def ingest_weather(self) -> dict:  # type: ignore[override]
    """
    Fetch live weather from Open-Meteo (free, no key) for all WC venues.
    Runs every 3 hours.
    """
    import asyncio
    try:
        from src.ingest.weather import fetch_all_venue_weather
        results = asyncio.run(fetch_all_venue_weather())
        updated = sum(1 for r in results.values() if r is not None)
        failed  = sum(1 for r in results.values() if r is None)
        log.info("ingest_weather: %d venues updated, %d failed", updated, failed)
        return {"status": "ok", "venues_updated": updated, "venues_failed": failed}
    except Exception as exc:
        log.error("ingest_weather failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=300) from exc


# ─── Tier 6: Season stats / advanced metrics ──────────────────────────────────

@celery_app.task(name="src.scheduler.tasks.ingest_season_stats", bind=True, max_retries=2)
def ingest_season_stats(self) -> dict:  # type: ignore[override]
    """
    Fetch season-level stats, EPA, and advanced metrics.
    nflfastR updates weekly; CFBD updates daily.
    Runs at 4 AM UTC.
    """
    try:
        # TODO(Phase 6): pull nflfastR / CFBD season data
        log.info("ingest_season_stats: stub")
        return {"status": "ok", "teams_updated": 0}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=600) from exc
