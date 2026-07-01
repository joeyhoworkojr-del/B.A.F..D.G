"""Pydantic response/request schemas for the API."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


# ─── Shared ───────────────────────────────────────────────────────────────────

class TeamInfo(BaseModel):
    code: str
    name: str
    flag: str
    elo: float
    group: Optional[str] = None
    is_host: bool = False
    conference: Optional[str] = None   # NFL
    division: Optional[str] = None     # NFL


# ─── Soccer prediction request ───────────────────────────────────────────────

class SoccerPredictRequest(BaseModel):
    home: str = Field(..., description="Home team code, e.g. 'ARG'")
    away: str = Field(..., description="Away team code, e.g. 'CPV'")
    knockout: bool = Field(default=False, description="Knockout round (adds ET + pens)")
    neutral: bool = Field(default=True, description="Neutral-venue match")
    defensive_dampener: float = Field(default=1.0, ge=0.5, le=1.5)


# ─── Soccer prediction response ──────────────────────────────────────────────

class WDLProbs(BaseModel):
    home_win: float
    draw: float
    away_win: float
    home_xg: float
    away_xg: float


class TotalsOut(BaseModel):
    over_1_5: float
    under_1_5: float
    over_2_5: float
    under_2_5: float
    over_3_5: float
    under_3_5: float
    over_4_5: float
    under_4_5: float
    btts: float
    btts_no: float
    home_over_0_5: float
    home_over_1_5: float
    home_over_2_5: float
    away_over_0_5: float
    away_over_1_5: float
    away_over_2_5: float
    most_likely_total: int
    expected_scoreline: list[int]


class PlayerPropOut(BaseModel):
    name: str
    team: str
    anytime_scorer: float
    two_plus_goals: float
    xg: float


class WhyFactorOut(BaseModel):
    label: str
    value: float


class SimOut(BaseModel):
    home_wins: float
    draws: float
    away_wins: float
    home_advance: float
    away_advance: float
    home_score_dist: dict[str, float]
    away_score_dist: dict[str, float]
    total_score_dist: dict[str, float]
    std_error: float


class SoccerPredictResponse(BaseModel):
    home_team: TeamInfo
    away_team: TeamInfo
    model_probs: WDLProbs
    blended_probs: WDLProbs
    totals: TotalsOut
    player_props: list[PlayerPropOut]
    scoreline_grid: list[list[float]]
    why_factors: list[WhyFactorOut]
    simulation: SimOut
    sim_error_bound: float
    has_sr_data: bool
    data_warning: str = "Live data — model updated daily."


# ─── NFL prediction request / response ───────────────────────────────────────

class NFLPredictRequest(BaseModel):
    home: str = Field(..., description="Home team code, e.g. 'KC'")
    away: str = Field(..., description="Away team code, e.g. 'SF'")
    neutral_site: bool = False


class NFLPredictResponse(BaseModel):
    home_team: TeamInfo
    away_team: TeamInfo
    home_win_prob: float
    away_win_prob: float
    predicted_spread: float
    home_cover_prob: float
    away_cover_prob: float
    total_points_estimate: float
    why_factors: list[WhyFactorOut]
    data_warning: str = "Elo model — does not account for injuries or current depth chart."


# ─── Rankings ─────────────────────────────────────────────────────────────────

class RankedTeam(BaseModel):
    rank: int
    code: str
    name: str
    flag: str
    elo: float
    group: Optional[str] = None
    conference: Optional[str] = None


class RankingsResponse(BaseModel):
    sport: str
    teams: list[RankedTeam]


# ─── Health ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    database_reachable: bool
    redis_reachable: bool
    version: str = "1.0.0"
