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


class WhyFactorOut(BaseModel):
    label: str
    value: float


class AdjustmentOut(BaseModel):
    """A live-condition adjustment applied to the model."""
    label: str
    detail: str
    source: str                 # "weather" | "lineup"
    home_xg_mult: float = 1.0   # soccer
    away_xg_mult: float = 1.0
    home_pts_delta: float = 0.0  # NFL
    away_pts_delta: float = 0.0


class WeatherInfoOut(BaseModel):
    venue: str
    temperature_c: float
    wind_speed_kmh: float
    precipitation_prob: int
    condition: str
    is_indoor: bool


class EdgeOut(BaseModel):
    """Model vs market comparison for one selection."""
    market: str
    selection: str
    model_prob: float
    implied_prob: float     # raw quoted implied prob (vig included)
    market_prob: float      # no-vig fair probability
    decimal_odds: float
    fair_odds: float        # model break-even odds
    edge_pp: float          # percentage points of edge
    ev_per_unit: float
    kelly_stake: float      # quarter-Kelly fraction of bankroll
    rating: str             # "A" | "B" | "C" | "-"


# ─── Soccer prediction request ───────────────────────────────────────────────

class SoccerMarketOdds(BaseModel):
    """Quoted market prices to compare the model against."""
    format: str = Field(default="decimal", description="'decimal' or 'american'")
    home: Optional[float] = None
    draw: Optional[float] = None
    away: Optional[float] = None
    over_2_5: Optional[float] = None
    under_2_5: Optional[float] = None


class SoccerPredictRequest(BaseModel):
    home: str = Field(..., description="Home team code, e.g. 'ARG'")
    away: str = Field(..., description="Away team code, e.g. 'CPV'")
    knockout: bool = Field(default=False, description="Knockout round (adds ET + pens)")
    neutral: bool = Field(default=True, description="Neutral-venue match")
    defensive_dampener: float = Field(default=1.0, ge=0.5, le=1.5)
    # Live conditions
    apply_weather: bool = Field(default=True, description="Fetch venue weather and adjust xG")
    apply_lineups: bool = Field(default=True, description="Apply lineup availability adjustments")
    venue: Optional[str] = Field(default=None, description="Venue for weather (auto from fixture if known)")
    missing_home: list[str] = Field(default_factory=list, description="Extra home players to treat as out")
    missing_away: list[str] = Field(default_factory=list, description="Extra away players to treat as out")
    # Market comparison
    odds: Optional[SoccerMarketOdds] = None


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
    over_by_line: dict[str, float] = Field(default_factory=dict)


class PlayerPropOut(BaseModel):
    name: str
    team: str
    anytime_scorer: float
    two_plus_goals: float
    xg: float


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
    # Live conditions + value
    base_probs: Optional[WDLProbs] = None      # before live conditions
    conditions: list[AdjustmentOut] = Field(default_factory=list)
    weather: Optional[WeatherInfoOut] = None
    fair_odds: dict[str, float] = Field(default_factory=dict)
    edges: list[EdgeOut] = Field(default_factory=list)


# ─── NFL prediction request / response ───────────────────────────────────────

class NFLMarketOdds(BaseModel):
    format: str = Field(default="american", description="'decimal' or 'american'")
    moneyline_home: Optional[float] = None
    moneyline_away: Optional[float] = None
    spread_home_price: Optional[float] = None   # price on the home spread
    spread_away_price: Optional[float] = None
    over_price: Optional[float] = None
    under_price: Optional[float] = None


class NFLPredictRequest(BaseModel):
    home: str = Field(..., description="Home team code, e.g. 'KC'")
    away: str = Field(..., description="Away team code, e.g. 'SF'")
    neutral_site: bool = False
    # Market lines
    spread_line: Optional[float] = Field(
        default=None, description="Quoted spread, betting convention (home -3.5 → -3.5)",
    )
    total_line: Optional[float] = Field(default=None, description="Quoted total, e.g. 44.5")
    odds: Optional[NFLMarketOdds] = None
    # Live conditions
    apply_weather: bool = Field(default=True, description="Fetch home-stadium weather and adjust")
    apply_lineups: bool = Field(default=True, description="Apply inactive-player adjustments")
    missing_home: list[str] = Field(default_factory=list)
    missing_away: list[str] = Field(default_factory=list)


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
    data_warning: str = "Expected-points model — check inactives before kickoff."
    # Expected points + totals market
    home_expected_pts: float = 0.0
    away_expected_pts: float = 0.0
    total_line: Optional[float] = None
    over_prob: float = 0.0
    under_prob: float = 0.0
    over_by_line: dict[str, float] = Field(default_factory=dict)
    home_team_total_over: dict[str, float] = Field(default_factory=dict)
    away_team_total_over: dict[str, float] = Field(default_factory=dict)
    # Live conditions + value
    base_home_win_prob: float = 0.0
    base_total_estimate: float = 0.0
    conditions: list[AdjustmentOut] = Field(default_factory=list)
    weather: Optional[WeatherInfoOut] = None
    fair_odds: dict[str, float] = Field(default_factory=dict)
    edges: list[EdgeOut] = Field(default_factory=list)


# ─── Lineups ──────────────────────────────────────────────────────────────────

class KeyPlayerOut(BaseModel):
    name: str
    team: str
    sport: str
    position: str
    importance: float
    status: str    # "fit" | "doubtful" | "out"


class SetPlayerStatusRequest(BaseModel):
    player: str
    status: str = Field(..., description="'fit', 'doubtful' or 'out'")


# ─── Best bets ────────────────────────────────────────────────────────────────

class BestBetOut(BaseModel):
    fixture_id: str
    kickoff: str
    venue: str
    home: str
    away: str
    home_flag: str
    away_flag: str
    market: str
    selection: str
    model_prob: float
    market_prob: Optional[float] = None   # SR reference (None for totals signals)
    edge_pp: Optional[float] = None
    rating: str
    note: str = ""


class BestBetsResponse(BaseModel):
    generated_with: str
    bets: list[BestBetOut]


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
    version: str = "2.0.0"
