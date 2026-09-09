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
    data_warning: str = (
        "Weather and team news are applied live; Elo ratings and fixture "
        "reference prices are a tournament snapshot."
    )
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
    data_warning: str = (
        "Stadium weather and inactives are applied live; team ratings are a "
        "season snapshot."
    )
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


# ─── Live scoreboards ─────────────────────────────────────────────────────────

class LiveGameOut(BaseModel):
    league: str
    event_id: str
    home: str
    away: str
    home_abbr: str = ""
    away_abbr: str = ""
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    state: str          # "pre" | "in" | "post"
    detail: str = ""    # "45' +2", "Q3 5:21", "Final", kickoff time…
    kickoff: str = ""
    # Live situation (football, in-game)
    period: Optional[int] = None
    clock: str = ""
    down_distance: str = ""
    possession_abbr: str = ""
    is_red_zone: bool = False
    # Yards from the possessing team's own goal line, 0-100. None whenever the
    # feed does not publish a position the offence can be placed on.
    yard_line: Optional[int] = None
    down: Optional[int] = None
    distance: Optional[int] = None
    last_play: str = ""
    home_logo: str = ""
    away_logo: str = ""
    # Live market
    market_spread: Optional[float] = None
    market_over_under: Optional[float] = None
    market_home_ml: Optional[float] = None
    market_away_ml: Optional[float] = None
    market_details: str = ""
    market_provider: str = ""


class PlayOut(BaseModel):
    period: Optional[int] = None
    clock: str = ""
    text: str = ""
    team_abbr: str = ""
    scoring: bool = False
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    # Ball position either side of the play, as yards from the offence's own
    # goal line. None whenever the feed did not publish it — the UI then shows
    # the play as text rather than drawing it somewhere it was not.
    start_yard_line: Optional[int] = None
    end_yard_line: Optional[int] = None
    yards_gained: Optional[int] = None
    down: Optional[int] = None
    distance: Optional[int] = None
    drive_id: str = ""
    drive_description: str = ""


class PlayByPlayOut(BaseModel):
    league: str
    event_id: str
    ok: bool = True
    plays: list[PlayOut] = Field(default_factory=list)
    fetched_at: str = ""


class NewsItemOut(BaseModel):
    """One story, attributed. Headline + the publisher's own summary line only."""
    league: str
    id: str
    headline: str
    description: str = ""
    published: str = ""       # ISO-8601 UTC
    byline: str = ""
    url: str = ""             # canonical link back to the publisher
    image: str = ""
    category: str = "news"    # news | injury | preview | recap
    teams: list[str] = Field(default_factory=list)
    source: str = "ESPN"
    # The model does not read these stories, so the UI must never claim one
    # moved a projection. Kept explicit rather than implied by omission.
    reflected_in_projection: bool = False


class NewsFeedOut(BaseModel):
    league: str
    items: list[NewsItemOut] = Field(default_factory=list)
    fetched_at: str = ""
    ok: bool = True
    source: str = "ESPN"
    attribution: str = "Headlines and summaries from ESPN. Follow a link to read the full story at the source."


class ScoreboardOut(BaseModel):
    league: str
    games: list[LiveGameOut] = Field(default_factory=list)
    fetched_at: str = ""    # ISO timestamp — freshness stamp
    source: str = "ESPN"
    ok: bool = True


class AllScoreboardsOut(BaseModel):
    boards: dict[str, ScoreboardOut]
    fetched_at: str = ""


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
    # Split out so the UI can deep-link to /game/{league}/{event_id} without
    # re-parsing the composite fixture_id.
    league: str = ""
    event_id: str = ""
    kickoff: str
    venue: str
    home: str
    away: str
    home_flag: str
    away_flag: str
    market: str
    # "moneyline", "spread" or "total" — the market kind on its own, so the
    # page can group and filter without parsing the display label.
    market_kind: str = ""
    selection: str
    model_prob: float
    market_prob: Optional[float] = None   # SR reference (None for totals signals)
    edge_pp: Optional[float] = None
    rating: str
    note: str = ""


class BestBetsResponse(BaseModel):
    generated_with: str
    bets: list[BestBetOut]


class ParlayLeg(BaseModel):
    fixture_id: str
    league: str
    kickoff: str
    home: str
    away: str
    market: str
    selection: str
    model_prob: float
    market_prob: float          # no-vig fair probability
    decimal_odds: float         # price this leg pays
    edge_pp: float
    rating: str


class BestParlayResponse(BaseModel):
    generated_with: str
    legs: list[ParlayLeg]                 # the featured parlay's legs
    leg_count: int
    model_prob: float                     # combined model probability (independent)
    decimal_odds: float                   # combined price
    american_odds: int                    # combined price, American
    implied_prob: float                   # break-even prob at the combined price
    edge_pp: float                        # model prob − implied prob, in points
    ev_per_unit: float                    # expected value on a 1-unit stake
    payout_per_unit: float                # profit on a 1-unit win
    pool: list[ParlayLeg] = []            # all qualifying legs to build your own


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
