"""FastAPI application — main entry point.

Serves the JSON API under /api/v1 and, when a built frontend is present
(STATIC_DIR, baked in by the production Docker image), the React SPA on
every other route — one process, one deployment, no CORS.
"""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes.predictions import router as pred_router
from src.api.routes.account import router as account_router
from src.api.routes.live import router as live_router
from src.api.schemas import HealthResponse
from src.config import settings

# Built frontend (Vite dist). Absent in dev → API-only, unchanged behavior.
STATIC_DIR = Path(
    os.getenv("STATIC_DIR", Path(__file__).resolve().parents[2] / "static")
)


log = logging.getLogger(__name__)

# How often the server freezes pre-game predictions into the ledger. Snapshots
# are a server responsibility: the track record must not depend on whether a
# visitor happened to open a page.
SNAPSHOT_INTERVAL_SECONDS = int(os.getenv("SNAPSHOT_INTERVAL_SECONDS", "600"))
SNAPSHOTS_ENABLED = os.getenv("SNAPSHOTS_ENABLED", "1") != "0"


async def _snapshot_loop() -> None:
    """Periodically snapshot pre-game picks and grade finished games."""
    from src.api.routes.predictions import FOCUS_LEAGUES, snapshot_pregame

    while True:
        for league in FOCUS_LEAGUES:
            try:
                n = await snapshot_pregame(league)
                log.info("snapshot: froze %d %s pre-game picks", n, league)
            except asyncio.CancelledError:
                raise
            except Exception as exc:   # a bad feed must never kill the loop
                log.warning("snapshot failed for %s: %s", league, exc)
        await asyncio.sleep(SNAPSHOT_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    task: asyncio.Task | None = None
    if SNAPSHOTS_ENABLED:
        task = asyncio.create_task(_snapshot_loop())
    yield
    if task is not None:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


app = FastAPI(
    title="StatEdge Sports Analytics API",
    description=(
        "Elo-Poisson soccer predictions, NFL Elo predictions, "
        "Monte Carlo simulation, over/unders, and player props."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Compress anything worth compressing. JSON payloads and the JS bundle are
# highly compressible, and nothing upstream was doing this.
app.add_middleware(GZipMiddleware, minimum_size=500)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pred_router, prefix="/api/v1")
app.include_router(live_router, prefix="/api/v1")
app.include_router(account_router, prefix="/api/v1")


# ─── Caching ──────────────────────────────────────────────────────────────────
# Every endpoint here is public, read-only data, so a shared cache (the browser
# or a CDN) may serve it. Live paths get a short max-age plus
# stale-while-revalidate: a poll landing between updates is answered instantly
# instead of re-running the model, while the client still refreshes in the
# background. TTLs stay at or below the upstream cache windows so a response is
# never fresher-looking than the data behind it.
_CACHE_RULES: tuple[tuple[str, str], ...] = (
    # Browser cache and server cache stack: an 8s max-age on top of an 8s
    # server TTL meant a play could be 16s old before anything refetched.
    # Two seconds keeps a burst of tabs cheap without adding visible lag.
    ("/api/v1/live/pbp/", "public, max-age=2, stale-while-revalidate=10"),
    ("/api/v1/live/scores", "public, max-age=15, stale-while-revalidate=45"),
    ("/api/v1/game/", "public, max-age=10, stale-while-revalidate=30"),
    ("/api/v1/today/", "public, max-age=15, stale-while-revalidate=45"),
    ("/api/v1/best-bets", "public, max-age=30, stale-while-revalidate=90"),
    ("/api/v1/best-parlay", "public, max-age=30, stale-while-revalidate=90"),
    ("/api/v1/accuracy", "public, max-age=60, stale-while-revalidate=300"),
    ("/api/v1/news", "public, max-age=120, stale-while-revalidate=600"),
    ("/api/v1/props", "public, max-age=300"),
    # Entitlements are per-caller. Even while every caller is anonymous, a
    # shared cache here would leak one person's plan to the next once auth
    # lands, so this is never stored.
    ("/api/v1/entitlements", "private, no-store"),
    ("/api/v1/teams/", "public, max-age=300"),
    ("/api/v1/rankings/", "public, max-age=300"),
)

# Vite emits content-hashed asset filenames, so a given URL's bytes never change.
_IMMUTABLE = "public, max-age=31536000, immutable"


@app.middleware("http")
async def cache_control(request, call_next):
    """Attach a cache policy to safe, successful GETs."""
    response = await call_next(request)

    if request.method != "GET" or response.status_code >= 400:
        return response
    if "cache-control" in response.headers:      # an endpoint set its own policy
        return response

    path = request.url.path
    if path.startswith("/assets/"):
        response.headers["Cache-Control"] = _IMMUTABLE
        return response

    for prefix, policy in _CACHE_RULES:
        if path.startswith(prefix):
            response.headers["Cache-Control"] = policy
            return response

    if not path.startswith("/api/"):
        # The SPA shell (and any unhashed file) must revalidate, or a deploy
        # leaves people on an old bundle pointed at new asset URLs.
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    db_ok = False
    redis_ok = False

    try:
        import asyncpg  # type: ignore
        conn = await asyncpg.connect(settings.database_url.replace("+asyncpg", ""))
        await conn.close()
        db_ok = True
    except Exception:
        pass

    try:
        import redis.asyncio as aioredis  # type: ignore
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        database_reachable=db_ok,
        redis_reachable=redis_ok,
    )


# ─── Frontend (single-app deployment) ─────────────────────────────────────────
# Registered last so every explicit route above (API, /health, /docs) wins.

if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        # Unknown API paths must stay 404s, not silently return the SPA
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        candidate = (STATIC_DIR / full_path).resolve()
        if (
            full_path
            and candidate.is_file()
            and candidate.is_relative_to(STATIC_DIR.resolve())
        ):
            return FileResponse(candidate)
        # Client-side routes (/nfl, /best-bets, …) fall back to the SPA shell
        return FileResponse(STATIC_DIR / "index.html")
