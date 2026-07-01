"""FastAPI application — main entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.predictions import router as pred_router
from src.api.routes.live import router as live_router
from src.api.schemas import HealthResponse
from src.config import settings


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
