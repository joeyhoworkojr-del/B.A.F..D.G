"""Central configuration — reads from environment variables with sane defaults."""
from __future__ import annotations

import os
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://statedge:statedge@localhost:5432/statedge",
        alias="DATABASE_URL",
    )
    database_url_sync: str = Field(
        default="postgresql://statedge:statedge@localhost:5432/statedge",
        alias="DATABASE_URL_SYNC",
    )

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # ── API ───────────────────────────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:4173"],
        alias="CORS_ORIGINS",
    )

    # ── Model params (soccer Elo-Poisson) ─────────────────────────────────────
    elo_mu: float = Field(default=1.06, alias="ELO_MU")        # base goals per side
    elo_q: float = Field(default=1540.0, alias="ELO_Q")        # Elo scale divisor
    elo_host_edge: float = Field(default=150.0, alias="ELO_HOST_EDGE")  # home-field Elo bonus
    sr_blend_weight: float = Field(default=0.60, alias="SR_BLEND_WEIGHT")  # SportRadar weight

    # ── Simulation ────────────────────────────────────────────────────────────
    monte_carlo_sims: int = Field(default=50_000, alias="MONTE_CARLO_SIMS")

    # ── External data ─────────────────────────────────────────────────────────
    cfbd_api_key: str = Field(default="", alias="CFBD_API_KEY")
    sportradar_api_key: str = Field(default="", alias="SPORTRADAR_API_KEY")
    football_data_api_key: str = Field(default="", alias="FOOTBALL_DATA_API_KEY")
    # ── Environment ───────────────────────────────────────────────────────────
    env: str = Field(default="development", alias="ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = {"env_file": os.path.join(os.path.dirname(__file__), "../../.env")}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
