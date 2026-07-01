"""Celery application and Beat schedule."""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from src.config import settings

celery_app = Celery(
    "statedge",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["src.scheduler.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    # ── Tier 1: completed game results (game days only, every 5 min) ──────────
    "ingest-completed-games": {
        "task": "src.scheduler.tasks.ingest_completed_games",
        "schedule": crontab(minute="*/5"),
    },
    # ── Tier 2: live in-game state (every 30 s — scheduler polls, not fired here) ─
    # Handled by a separate lightweight websocket consumer, not beat.

    # ── Tier 3: injury reports — every hour, spike near reporting windows ─────
    "ingest-injury-reports": {
        "task": "src.scheduler.tasks.ingest_injury_reports",
        "schedule": crontab(minute=0),
    },
    # ── Tier 4: starting lineups (2 hours pre-game, every 10 min) ─────────────
    "ingest-lineups": {
        "task": "src.scheduler.tasks.ingest_lineups",
        "schedule": crontab(minute="*/10"),
    },
    # ── Tier 5: weather updates ───────────────────────────────────────────────
    "ingest-weather": {
        "task": "src.scheduler.tasks.ingest_weather",
        "schedule": crontab(minute=0, hour="*/3"),
    },
    # ── Tier 6: season stats / advanced metrics ───────────────────────────────
    "ingest-season-stats": {
        "task": "src.scheduler.tasks.ingest_season_stats",
        "schedule": crontab(minute=0, hour=4),   # 4 AM UTC daily
    },
}
