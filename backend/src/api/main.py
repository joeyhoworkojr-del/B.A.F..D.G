"""FastAPI application — main entry point.

Serves the JSON API under /api/v1 and, when a built frontend is present
(STATIC_DIR, baked in by the production Docker image), the React SPA on
every other route — one process, one deployment, no CORS.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes.predictions import router as pred_router
from src.api.routes.live import router as live_router
from src.api.schemas import HealthResponse
from src.config import settings

# Built frontend (Vite dist). Absent in dev → API-only, unchanged behavior.
STATIC_DIR = Path(
    os.getenv("STATIC_DIR", Path(__file__).resolve().parents[2] / "static")
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: could warm caches here
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="StatEdge Sports Analytics API",
    description=(
        "Elo-Poisson soccer predictions, NFL Elo predictions, "
        "Monte Carlo simulation, over/unders, and player props."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pred_router, prefix="/api/v1")
app.include_router(live_router, prefix="/api/v1")


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
