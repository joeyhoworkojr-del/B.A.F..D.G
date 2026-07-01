"""
SQLAlchemy ORM models — Phase 1 database schema.

Tables:
  teams          — one row per team (any sport), keyed by (sport, code)
  games          — completed / upcoming games
  predictions    — stored predictions for each game
  game_history   — user-logged results for Brier score tracking
  elo_snapshots  — daily Elo rating snapshots for trend charts
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("sport", "code", name="uq_teams_sport_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    sport: Mapped[str] = mapped_column(String(16), nullable=False)   # "soccer" | "nfl"
    code: Mapped[str] = mapped_column(String(8), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    flag: Mapped[str] = mapped_column(String(8), nullable=False, default="")
    elo: Mapped[float] = mapped_column(Float, nullable=False)
    group_name: Mapped[Optional[str]] = mapped_column(String(4))     # WC group
    conference: Mapped[Optional[str]] = mapped_column(String(8))     # NFL conference
    division: Mapped[Optional[str]] = mapped_column(String(8))       # NFL division
    is_host: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    elo_snapshots: Mapped[list["EloSnapshot"]] = relationship(back_populates="team")


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (
        UniqueConstraint("sport", "provider_id", name="uq_games_provider_id"),
        Index("ix_games_kickoff", "kickoff"),
        Index("ix_games_sport_status", "sport", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    sport: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_id: Mapped[str] = mapped_column(String(64), nullable=False)
    home_code: Mapped[str] = mapped_column(String(8), nullable=False)
    away_code: Mapped[str] = mapped_column(String(8), nullable=False)
    kickoff: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    venue: Mapped[Optional[str]] = mapped_column(String(128))
    stage: Mapped[Optional[str]] = mapped_column(String(32))         # "R16", "regular", …
    neutral: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(16), default="upcoming")  # upcoming|live|final
    home_goals: Mapped[Optional[int]] = mapped_column(Integer)
    away_goals: Mapped[Optional[int]] = mapped_column(Integer)
    home_elo_pre: Mapped[Optional[float]] = mapped_column(Float)
    away_elo_pre: Mapped[Optional[float]] = mapped_column(Float)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB)        # weather, SR probs, etc.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    predictions: Mapped[list["Prediction"]] = relationship(back_populates="game")
    history_entries: Mapped[list["GameHistory"]] = relationship(back_populates="game")


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        Index("ix_predictions_game_id", "game_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), nullable=False
    )
    model_version: Mapped[str] = mapped_column(String(32), default="v1")
    home_win_prob: Mapped[float] = mapped_column(Float)
    draw_prob: Mapped[Optional[float]] = mapped_column(Float)         # None for NFL
    away_win_prob: Mapped[float] = mapped_column(Float)
    home_xg: Mapped[Optional[float]] = mapped_column(Float)
    away_xg: Mapped[Optional[float]] = mapped_column(Float)
    blended_home_win: Mapped[Optional[float]] = mapped_column(Float)
    blended_draw: Mapped[Optional[float]] = mapped_column(Float)
    blended_away_win: Mapped[Optional[float]] = mapped_column(Float)
    totals_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    player_props_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    why_factors: Mapped[Optional[dict]] = mapped_column(JSONB)
    sim_home_advance: Mapped[Optional[float]] = mapped_column(Float)
    sim_away_advance: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    game: Mapped["Game"] = relationship(back_populates="predictions")


class GameHistory(Base):
    """User-logged results for Brier score / hit-rate tracking."""
    __tablename__ = "game_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    game_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id", ondelete="SET NULL")
    )
    sport: Mapped[str] = mapped_column(String(16), nullable=False)
    home_code: Mapped[str] = mapped_column(String(8), nullable=False)
    away_code: Mapped[str] = mapped_column(String(8), nullable=False)
    predicted_home_win: Mapped[float] = mapped_column(Float)         # probability used
    actual_outcome: Mapped[str] = mapped_column(String(8))           # "home"|"draw"|"away"
    home_goals_actual: Mapped[Optional[int]] = mapped_column(Integer)
    away_goals_actual: Mapped[Optional[int]] = mapped_column(Integer)
    brier_score: Mapped[Optional[float]] = mapped_column(Float)      # computed server-side
    notes: Mapped[Optional[str]] = mapped_column(Text)
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    game: Mapped[Optional["Game"]] = relationship(back_populates="history_entries")


class EloSnapshot(Base):
    """Daily Elo snapshots for historical trend charts."""
    __tablename__ = "elo_snapshots"
    __table_args__ = (
        UniqueConstraint("team_id", "snapshot_date", name="uq_elo_snap_team_date"),
        Index("ix_elo_snapshots_team_id", "team_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    elo: Mapped[float] = mapped_column(Float, nullable=False)

    team: Mapped["Team"] = relationship(back_populates="elo_snapshots")
