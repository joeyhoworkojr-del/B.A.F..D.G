"""Soccer and NFL prediction endpoints with live conditions and value math."""
from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException

from src.api.schemas import (
    AdjustmentOut,
    BestBetOut,
    BestBetsResponse,
    BestParlayResponse,
    EdgeOut,
    ParlayLeg,
    NFLPredictRequest,
    NFLPredictResponse,
    PlayerPropOut,
    RankedTeam,
    RankingsResponse,
    SimOut,
    SoccerPredictRequest,
    SoccerPredictResponse,
    TeamInfo,
    TotalsOut,
    WDLProbs,
    WeatherInfoOut,
    WhyFactorOut,
)
from src.data.cfl import all_cfl_teams_sorted, get_cfl_team
from src.data.mlb import all_mlb_teams_sorted, get_mlb_team
from src.data.ncaaf import all_ncaaf_teams_sorted, get_ncaaf_team
from src.data.nfl import all_nfl_teams_sorted, get_nfl_team
from src.data.world_cup import (
    R16_FIXTURES,
    TEAMS,
    all_teams_sorted,
    get_scorers_for_team,
    get_team,
)
from src.ingest.espn import LiveGame, fetch_scoreboard, is_current
from src.ingest.polymarket import fetch_league_markets, match_game
from src.ingest.weather import WeatherReport, fetch_gridiron_weather, fetch_weather
from src.predict.adjustments import (
    mlb_lineup_adjustments,
    mlb_weather_adjustments,
    nfl_lineup_adjustments,
    nfl_weather_adjustments,
    soccer_altitude_adjustments,
    soccer_lineup_adjustments,
    soccer_weather_adjustments,
)
from src.predict.baseball import predict_mlb_game
from src.predict.gridiron import LEAGUE_PARAMS as GRIDIRON_PARAMS
from src.predict.gridiron import live_projection, predict_nfl_game, win_probability
from src.predict.soccer import predict_match
from src.track import ledger, ratings
from src.value.edge import american_to_decimal
from src.simulate.monte_carlo import simulate_soccer
from src.value.edge import BetEdge, edge_rating, evaluate_market
from src.model_version import MODEL_VERSION

router = APIRouter()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _weather_out(w: Optional[WeatherReport]) -> Optional[WeatherInfoOut]:
    if w is None:
        return None
    return WeatherInfoOut(
        venue=w.venue,
        temperature_c=w.temperature_c,
        wind_speed_kmh=w.wind_speed_kmh,
        precipitation_prob=w.precipitation_prob,
        condition=w.condition,
        is_indoor=w.is_indoor,
    )


def _adjustments_out(conditions: list) -> list[AdjustmentOut]:
    return [
        AdjustmentOut(
            label=a.label, detail=a.detail, source=a.source,
            home_xg_mult=a.home_xg_mult, away_xg_mult=a.away_xg_mult,
            home_pts_delta=a.home_pts_delta, away_pts_delta=a.away_pts_delta,
        )
        for a in conditions
    ]


def _edges_out(edges: list[BetEdge]) -> list[EdgeOut]:
    return [
        EdgeOut(
            market=e.market, selection=e.selection,
            model_prob=e.model_prob, implied_prob=e.implied_prob,
            market_prob=e.market_prob, decimal_odds=e.decimal_odds,
            fair_odds=e.fair_odds, edge_pp=e.edge_pp,
            ev_per_unit=e.ev_per_unit, kelly_stake=e.kelly_stake,
            rating=e.rating,
        )
        for e in edges
    ]


def _wdl(probs) -> WDLProbs:
    return WDLProbs(
        home_win=probs.home_win, draw=probs.draw, away_win=probs.away_win,
        home_xg=probs.home_xg, away_xg=probs.away_xg,
    )


# ─── Soccer ───────────────────────────────────────────────────────────────────

@router.get("/teams/soccer", response_model=list[TeamInfo], tags=["Teams"])
def list_soccer_teams() -> list[TeamInfo]:
    return [
        TeamInfo(
            code=t.code, name=t.name, flag=t.flag, elo=t.elo,
            group=t.group, is_host=t.is_host,
        )
        for t in all_teams_sorted()
    ]


@router.post("/predict/soccer", response_model=SoccerPredictResponse, tags=["Predictions"])
async def predict_soccer(req: SoccerPredictRequest) -> SoccerPredictResponse:
    home_code = req.home.upper()
    away_code = req.away.upper()

    try:
        home_t = get_team(home_code)
        away_t = get_team(away_code)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # Find SR reference probs and venue if a live fixture matches
    sr_hw = sr_dr = sr_aw = None
    fixture_venue: Optional[str] = None
    for fix in R16_FIXTURES:
        if fix.home == home_code and fix.away == away_code:
            sr_hw, sr_dr, sr_aw = fix.sr_home_win, fix.sr_draw, fix.sr_away_win
            fixture_venue = fix.venue or None
            break

    # ── Live conditions ──
    adjustments = []
    weather: Optional[WeatherReport] = None
    if req.apply_weather:
        venue = req.venue or fixture_venue
        if venue:
            weather = await fetch_weather(venue)
            adjustments.extend(soccer_weather_adjustments(weather))
            # Altitude is a property of the venue, not the weather — it applies
            # even indoors and regardless of the host designation.
            adjustments.extend(soccer_altitude_adjustments(
                venue, home_code, away_code, home_t.name, away_t.name,
            ))
    if req.apply_lineups:
        adjustments.extend(soccer_lineup_adjustments(
            home_code, away_code, req.missing_home, req.missing_away,
        ))

    scorers = get_scorers_for_team(home_code) + get_scorers_for_team(away_code)

    result = predict_match(
        home_code, away_code,
        ratings.adjust("wc", home_code, home_t.elo),
        ratings.adjust("wc", away_code, away_t.elo),
        home_is_host=home_t.is_host,
        neutral=req.neutral,
        defensive_dampener=req.defensive_dampener,
        sr_home_win=sr_hw,
        sr_draw=sr_dr,
        sr_away_win=sr_aw,
        scorers=scorers,
        adjustments=adjustments,
    )

    sim = simulate_soccer(
        result.model_probs.home_xg,
        result.model_probs.away_xg,
        knockout=req.knockout,
    )

    # ── Market edges ──
    edges: list[BetEdge] = []
    if req.odds:
        fmt = req.odds.format
        edges += evaluate_market(
            "1X2",
            [
                (f"{home_t.name} win", result.blended_probs.home_win, req.odds.home),
                ("Draw", result.blended_probs.draw, req.odds.draw),
                (f"{away_t.name} win", result.blended_probs.away_win, req.odds.away),
            ],
            odds_format=fmt,
        )
        edges += evaluate_market(
            "Total 2.5",
            [
                ("Over 2.5", result.totals.over_2_5, req.odds.over_2_5),
                ("Under 2.5", result.totals.under_2_5, req.odds.under_2_5),
            ],
            odds_format=fmt,
        )
        edges.sort(key=lambda e: -e.edge_pp)

    return SoccerPredictResponse(
        home_team=TeamInfo(
            code=home_t.code, name=home_t.name, flag=home_t.flag,
            elo=home_t.elo, group=home_t.group, is_host=home_t.is_host,
        ),
        away_team=TeamInfo(
            code=away_t.code, name=away_t.name, flag=away_t.flag,
            elo=away_t.elo, group=away_t.group, is_host=away_t.is_host,
        ),
        model_probs=_wdl(result.model_probs),
        blended_probs=_wdl(result.blended_probs),
        totals=TotalsOut(
            over_1_5=result.totals.over_1_5,
            under_1_5=result.totals.under_1_5,
            over_2_5=result.totals.over_2_5,
            under_2_5=result.totals.under_2_5,
            over_3_5=result.totals.over_3_5,
            under_3_5=result.totals.under_3_5,
            over_4_5=result.totals.over_4_5,
            under_4_5=result.totals.under_4_5,
            btts=result.totals.btts,
            btts_no=result.totals.btts_no,
            home_over_0_5=result.totals.home_over_0_5,
            home_over_1_5=result.totals.home_over_1_5,
            home_over_2_5=result.totals.home_over_2_5,
            away_over_0_5=result.totals.away_over_0_5,
            away_over_1_5=result.totals.away_over_1_5,
            away_over_2_5=result.totals.away_over_2_5,
            most_likely_total=result.totals.most_likely_total,
            expected_scoreline=list(result.totals.expected_scoreline),
            over_by_line=result.totals.over_by_line,
        ),
        player_props=[
            PlayerPropOut(
                name=p.name, team=p.team,
                anytime_scorer=p.anytime_scorer,
                two_plus_goals=p.two_plus_goals,
                xg=p.xg,
            )
            for p in result.player_props
        ],
        scoreline_grid=result.scoreline_grid,
        why_factors=[
            WhyFactorOut(label=f.label, value=f.value)
            for f in result.why_factors
        ],
        simulation=SimOut(
            home_wins=sim.home_wins,
            draws=sim.draws,
            away_wins=sim.away_wins,
            home_advance=sim.home_advance,
            away_advance=sim.away_advance,
            home_score_dist={str(k): v for k, v in sim.home_score_dist.items()},
            away_score_dist={str(k): v for k, v in sim.away_score_dist.items()},
            total_score_dist={str(k): v for k, v in sim.total_score_dist.items()},
            std_error=sim.std_error,
        ),
        sim_error_bound=result.sim_error_bound,
        has_sr_data=result.has_sr_data,
        base_probs=_wdl(result.base_probs) if result.base_probs else None,
        conditions=_adjustments_out(result.conditions),
        weather=_weather_out(weather),
        fair_odds=result.fair_odds,
        edges=_edges_out(edges),
    )


# ─── NFL ──────────────────────────────────────────────────────────────────────

@router.get("/teams/nfl", response_model=list[TeamInfo], tags=["Teams"])
def list_nfl_teams() -> list[TeamInfo]:
    return [
        TeamInfo(
            code=t.code, name=f"{t.city} {t.name}", flag=t.flag,
            elo=t.elo, conference=t.conference, division=t.division,
        )
        for t in all_nfl_teams_sorted()
    ]


_TEAM_GETTERS = {
    "nfl": get_nfl_team, "ncaaf": get_ncaaf_team,
    "cfl": get_cfl_team, "mlb": get_mlb_team,
}


async def _predict_gridiron(req: NFLPredictRequest, league: str) -> NFLPredictResponse:
    home_code = req.home.upper()
    away_code = req.away.upper()
    get_team_fn = _TEAM_GETTERS[league]

    try:
        home_t = get_team_fn(home_code)
        away_t = get_team_fn(away_code)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # Self-correcting ratings: base prior + whatever recent results have taught us.
    home_elo = ratings.adjust(league, home_code, home_t.elo)
    away_elo = ratings.adjust(league, away_code, away_t.elo)

    # ── Live conditions ──
    # College football has no per-team stadium/roster data here, so it runs
    # purely off ratings + the market line (its most accurate signal anyway).
    has_live_conditions = league in ("nfl", "cfl", "mlb")
    adjustments = []
    weather: Optional[WeatherReport] = None
    if req.apply_weather and not req.neutral_site and has_live_conditions:
        weather = await fetch_gridiron_weather(league, home_code)
        adjustments.extend(
            mlb_weather_adjustments(weather) if league == "mlb"
            else nfl_weather_adjustments(weather)
        )
    if req.apply_lineups and has_live_conditions:
        if league == "mlb":
            adjustments.extend(mlb_lineup_adjustments(
                home_code, away_code, req.missing_home, req.missing_away,
            ))
        else:
            adjustments.extend(nfl_lineup_adjustments(
                home_code, away_code, req.missing_home, req.missing_away,
                sport=league,
            ))

    if league == "mlb":
        result = predict_mlb_game(
            home_code, away_code,
            home_elo, away_elo,
            neutral_site=req.neutral_site,
            spread_line=req.spread_line,
            total_line=req.total_line,
            adjustments=adjustments,
        )
    else:
        result = predict_nfl_game(
            home_code, away_code,
            home_elo, away_elo,
            neutral_site=req.neutral_site,
            spread_line=req.spread_line,
            total_line=req.total_line,
            adjustments=adjustments,
            league=league,
        )

    # ── Market edges ──
    edges: list[BetEdge] = []
    if req.odds:
        fmt = req.odds.format
        edges += evaluate_market(
            "Moneyline",
            [
                (f"{home_t.name} ML", result.home_win_prob, req.odds.moneyline_home),
                (f"{away_t.name} ML", result.away_win_prob, req.odds.moneyline_away),
            ],
            odds_format=fmt,
        )
        spread_txt = f"{result.predicted_spread:+.1f}" if req.spread_line is None else f"{req.spread_line:+.1f}"
        edges += evaluate_market(
            f"Spread {spread_txt}",
            [
                (f"{home_t.name} cover", result.home_cover_prob, req.odds.spread_home_price),
                (f"{away_t.name} cover", result.away_cover_prob, req.odds.spread_away_price),
            ],
            odds_format=fmt,
        )
        edges += evaluate_market(
            f"Total {result.total_line}",
            [
                (f"Over {result.total_line}", result.over_prob, req.odds.over_price),
                (f"Under {result.total_line}", result.under_prob, req.odds.under_price),
            ],
            odds_format=fmt,
        )
        edges.sort(key=lambda e: -e.edge_pp)

    def _full_name(t) -> str:
        city = getattr(t, "city", "")
        return f"{city} {t.name}".strip() if city else t.name

    return NFLPredictResponse(
        home_team=TeamInfo(
            code=home_t.code, name=_full_name(home_t),
            flag=home_t.flag, elo=home_t.elo,
            conference=getattr(home_t, "conference", None),
            division=getattr(home_t, "division", None),
        ),
        away_team=TeamInfo(
            code=away_t.code, name=_full_name(away_t),
            flag=away_t.flag, elo=away_t.elo,
            conference=getattr(away_t, "conference", None),
            division=getattr(away_t, "division", None),
        ),
        home_win_prob=result.home_win_prob,
        away_win_prob=result.away_win_prob,
        predicted_spread=result.predicted_spread,
        home_cover_prob=result.home_cover_prob,
        away_cover_prob=result.away_cover_prob,
        total_points_estimate=result.total_points_estimate,
        why_factors=[WhyFactorOut(**f) for f in result.why_factors],
        home_expected_pts=result.home_expected_pts,
        away_expected_pts=result.away_expected_pts,
        total_line=result.total_line,
        over_prob=result.over_prob,
        under_prob=result.under_prob,
        over_by_line=result.over_by_line,
        home_team_total_over=result.home_team_total_over,
        away_team_total_over=result.away_team_total_over,
        base_home_win_prob=result.base_home_win_prob,
        base_total_estimate=result.base_total_estimate,
        conditions=_adjustments_out(result.conditions),
        weather=_weather_out(weather),
        fair_odds=result.fair_odds,
        edges=_edges_out(edges),
    )


@router.post("/predict/nfl", response_model=NFLPredictResponse, tags=["Predictions"])
async def predict_nfl(req: NFLPredictRequest) -> NFLPredictResponse:
    return await _predict_gridiron(req, "nfl")


@router.post("/predict/ncaaf", response_model=NFLPredictResponse, tags=["Predictions"])
async def predict_ncaaf(req: NFLPredictRequest) -> NFLPredictResponse:
    """NCAA FBS football — same engine, college scoring environment. Unknown
    teams fall back to a neutral baseline and lean on the market line."""
    return await _predict_gridiron(req, "ncaaf")


@router.get("/teams/ncaaf", response_model=list[TeamInfo], tags=["Teams"])
def list_ncaaf_teams() -> list[TeamInfo]:
    # De-dupe alt abbreviations that share a name (e.g. UGA/GA, BSU/BOIS).
    seen: set[str] = set()
    out: list[TeamInfo] = []
    for t in all_ncaaf_teams_sorted():
        if t.name in seen:
            continue
        seen.add(t.name)
        out.append(TeamInfo(
            code=t.code, name=t.name, flag=t.flag,
            elo=t.elo, conference=t.conference,
        ))
    return out


@router.get("/rankings/ncaaf", response_model=RankingsResponse, tags=["Rankings"])
def ncaaf_rankings() -> RankingsResponse:
    seen: set[str] = set()
    teams: list[RankedTeam] = []
    for t in all_ncaaf_teams_sorted():
        if t.name in seen:
            continue
        seen.add(t.name)
        teams.append(RankedTeam(
            rank=len(teams) + 1, code=t.code, name=t.name,
            flag=t.flag, elo=t.elo, conference=t.conference,
        ))
    return RankingsResponse(sport="ncaaf", teams=teams)


@router.post("/predict/cfl", response_model=NFLPredictResponse, tags=["Predictions"])
async def predict_cfl(req: NFLPredictRequest) -> NFLPredictResponse:
    """CFL prediction — same engine, 3-down scoring environment."""
    return await _predict_gridiron(req, "cfl")


@router.get("/teams/cfl", response_model=list[TeamInfo], tags=["Teams"])
def list_cfl_teams() -> list[TeamInfo]:
    return [
        TeamInfo(
            code=t.code, name=f"{t.city} {t.name}", flag=t.flag,
            elo=t.elo, division=t.division,
        )
        for t in all_cfl_teams_sorted()
    ]


@router.get("/rankings/cfl", response_model=RankingsResponse, tags=["Rankings"])
def cfl_rankings() -> RankingsResponse:
    teams = [
        RankedTeam(
            rank=i + 1, code=t.code, name=f"{t.city} {t.name}",
            flag=t.flag, elo=t.elo,
        )
        for i, t in enumerate(all_cfl_teams_sorted())
    ]
    return RankingsResponse(sport="cfl", teams=teams)


@router.post("/predict/mlb", response_model=NFLPredictResponse, tags=["Predictions"])
async def predict_mlb(req: NFLPredictRequest) -> NFLPredictResponse:
    """MLB prediction — Poisson run-scoring grid with park factors."""
    return await _predict_gridiron(req, "mlb")


@router.get("/teams/mlb", response_model=list[TeamInfo], tags=["Teams"])
def list_mlb_teams() -> list[TeamInfo]:
    return [
        TeamInfo(
            code=t.code, name=f"{t.city} {t.name}", flag=t.flag,
            elo=t.elo, conference=t.league, division=t.division,
        )
        for t in all_mlb_teams_sorted()
    ]


@router.get("/rankings/mlb", response_model=RankingsResponse, tags=["Rankings"])
def mlb_rankings() -> RankingsResponse:
    teams = [
        RankedTeam(
            rank=i + 1, code=t.code, name=f"{t.city} {t.name}",
            flag=t.flag, elo=t.elo, conference=t.league,
        )
        for i, t in enumerate(all_mlb_teams_sorted())
    ]
    return RankingsResponse(sport="mlb", teams=teams)


# ─── Today: auto-predict every game + live market comparison ─────────────────

# ESPN abbreviation → our team code, where they differ. ESPN is inconsistent
# about CFL abbreviations across endpoints, so we cover every form seen.
_ESPN_ALIASES: dict[str, dict[str, str]] = {
    "nfl": {"LAR": "LA", "WAS": "WSH"},
    "cfl": {
        "SAS": "SSK", "SASK": "SSK",             # Saskatchewan
        "WNP": "WPG", "WIN": "WPG", "WPG": "WPG",  # Winnipeg
        "BCL": "BC", "BClions": "BC",             # BC Lions
        "CAL": "CGY",                             # Calgary
        "EDM": "EDM", "ESK": "EDM",               # Edmonton (ex-Eskimos)
        "MTL": "MTL", "MON": "MTL",               # Montreal
        "HAM": "HAM", "TOR": "TOR", "OTT": "OTT",
    },
    "mlb": {"OAK": "ATH", "CWS": "CHW", "AZ": "ARI"},
}


def _map_code(league: str, abbr: str) -> Optional[str]:
    code = _ESPN_ALIASES.get(league, {}).get(abbr.upper(), abbr.upper())
    try:
        _TEAM_GETTERS[league](code)
        return code
    except KeyError:
        return None


# How far to shrink the model's headline win probability toward the no-vig
# market. Raw rating models are systematically over-confident; the closing line
# is the sharpest public estimator, so a modest anchor de-biases the number the
# user actually reads. The RAW model is still used for edge detection and the
# track record, so this never manufactures or erases an edge.
MARKET_ANCHOR_WEIGHT = 0.50

# College football has ~135 teams and weak per-team priors, so the market line
# is a far sharper estimate than our ratings — anchor harder to it. NFL priors
# are strong, so we trust the model more there.
_MARKET_ANCHOR_BY_LEAGUE = {"ncaaf": 0.72}

# How far the projected *score* is pulled toward the market-implied score
# (derived from the spread + total). The market total is the sharpest public
# estimate of the scoring environment, so we lean on it — most for college.
_SCORE_ANCHOR_BY_LEAGUE = {"ncaaf": 0.65, "nfl": 0.45, "cfl": 0.45, "mlb": 0.40}


def _spread_to_home_prob(spread: float, league: str) -> float:
    """Home win probability implied by a market spread (home-based, e.g. -6.5).

    Expected home margin is −spread; run it through the league's margin
    distribution. Lets us anchor to the line even when no moneyline is quoted.
    """
    sigma = GRIDIRON_PARAMS.get(league, GRIDIRON_PARAMS["nfl"])["margin_sigma"]
    return win_probability(-spread, sigma)


def _clock_seconds(clock: str) -> float:
    """Seconds left in the current period from a 'MM:SS' game clock."""
    try:
        mm, ss = clock.split(":")
        return int(mm) * 60 + int(ss)
    except (ValueError, AttributeError):
        return 0.0


def _market_implied_score(g: LiveGame) -> Optional[tuple[float, float]]:
    """(home_pts, away_pts) implied by the market spread + total, or None."""
    if g.market_spread is None or g.market_over_under is None:
        return None
    margin = -g.market_spread            # home favored by −spread
    total = g.market_over_under
    return (total + margin) / 2.0, (total - margin) / 2.0

# Raw rating models are systematically over-confident, so hunting for edges
# straight off the raw probability makes the model disagree with the market on
# *every* game — it "always fades the crowd." Before comparing to a market
# price we shrink the raw prob toward a 50/50 coin flip: marginal leans collapse
# into agreement with the book/crowd, and only a genuinely strong disagreement
# still clears the A/B edge bar and gets flagged. This is the share of the raw
# deviation from 50% we keep when detecting edges (headline prob + the Brier
# ledger keep the un-shrunk model).
EDGE_CONFIDENCE_SHRINK = 0.72


def _debias(p: float) -> float:
    """Shrink an over-confident model prob toward 50% for edge detection."""
    return 0.5 + EDGE_CONFIDENCE_SHRINK * (p - 0.5)


def _no_vig_home_prob(g: LiveGame) -> Optional[float]:
    """No-vig implied home win probability from the live moneylines, or None."""
    if not (g.market_home_ml and g.market_away_ml):
        return None
    try:
        ih = 1.0 / american_to_decimal(g.market_home_ml)
        ia = 1.0 / american_to_decimal(g.market_away_ml)
    except ValueError:
        return None
    return ih / (ih + ia)


# ─── Structured market comparison (Game Center data contract) ────────────────

# Edge grades, surfaced with the scale so the UI can explain them rather than
# showing an unexplained letter.
GRADE_SCALE = [
    {"grade": "A", "min_edge_pp": 6.0, "label": "Strong"},
    {"grade": "B", "min_edge_pp": 3.5, "label": "Solid"},
    {"grade": "C", "min_edge_pp": 1.5, "label": "Slight"},
    {"grade": "-", "min_edge_pp": 0.0, "label": "No edge"},
]

# ESPN publishes a spread/total line but no price for it, so we price those at
# the standard -110 and say so; the moneyline carries real quoted prices.
ASSUMED_PRICE = -110


def _american_from_prob(p: float) -> Optional[int]:
    """Fair American price for a probability (the model's break-even number)."""
    if p is None or p <= 0.0 or p >= 1.0:
        return None
    dec = 1.0 / p
    return _american_from_decimal(dec)


def _selection(
    *, label: str, side: str, model_prob: float, model_prob_raw: float,
    book_prob: Optional[float], price_american: Optional[float],
    crowd_prob: Optional[float] = None,
) -> dict:
    """One side of a market: model vs no-vig book vs crowd, priced."""
    price = price_american if price_american is not None else ASSUMED_PRICE
    try:
        dec = american_to_decimal(price)
    except ValueError:
        dec = None
    ev = (model_prob * (dec - 1.0) - (1.0 - model_prob)) if dec else None
    edge_pp = (model_prob - book_prob) * 100.0 if book_prob is not None else None
    return {
        "label": label,
        "side": side,
        "model_prob": round(model_prob, 4),
        "model_prob_raw": round(model_prob_raw, 4),
        "book_prob": round(book_prob, 4) if book_prob is not None else None,
        "crowd_prob": round(crowd_prob, 4) if crowd_prob is not None else None,
        "price_american": int(price),
        "price_decimal": round(dec, 3) if dec else None,
        "fair_price_american": _american_from_prob(model_prob),
        "edge_pp": round(edge_pp, 1) if edge_pp is not None else None,
        "ev_per_unit": round(ev, 4) if ev is not None else None,
        "grade": edge_rating(edge_pp) if edge_pp is not None else "-",
    }


def _build_markets(league: str, g: LiveGame, pred, home: str, away: str, pm: Optional[dict]) -> list[dict]:
    """Moneyline / Spread / Total, each comparing model, book and crowd.

    Probabilities are the de-biased model numbers the edges are actually taken
    on; the raw model number rides along for transparency.
    """
    markets: list[dict] = []
    source = g.market_provider or "ESPN"

    # ── Moneyline: real quoted prices, vig removed across the two sides ──
    if g.market_home_ml is not None and g.market_away_ml is not None:
        bh = _no_vig_home_prob(g)
        markets.append({
            "key": "moneyline",
            "label": "Moneyline",
            "question": "Who wins the game outright?",
            "probability_kind": "win",
            "line": None,
            "source": source,
            "assumed_price": False,
            "selections": [
                _selection(label=f"{g.away_abbr or away} ML", side="away",
                           model_prob=_debias(pred.away_win_prob), model_prob_raw=pred.away_win_prob,
                           book_prob=(1 - bh) if bh is not None else None,
                           price_american=g.market_away_ml,
                           crowd_prob=pm["away_prob"] if pm else None),
                _selection(label=f"{g.home_abbr or home} ML", side="home",
                           model_prob=_debias(pred.home_win_prob), model_prob_raw=pred.home_win_prob,
                           book_prob=bh, price_american=g.market_home_ml,
                           crowd_prob=pm["home_prob"] if pm else None),
            ],
        })

    # ── Spread: line published, price assumed at -110 (no-vig = 50/50) ──
    if g.market_spread is not None:
        sp = g.market_spread
        markets.append({
            "key": "spread",
            "label": "Spread",
            "question": "Who covers the point spread?",
            "probability_kind": "cover",
            "line": sp,
            "source": source,
            "assumed_price": True,
            "selections": [
                _selection(label=f"{g.away_abbr or away} {-sp:+.1f}", side="away",
                           model_prob=_debias(pred.away_cover_prob), model_prob_raw=pred.away_cover_prob,
                           book_prob=0.5, price_american=ASSUMED_PRICE),
                _selection(label=f"{g.home_abbr or home} {sp:+.1f}", side="home",
                           model_prob=_debias(pred.home_cover_prob), model_prob_raw=pred.home_cover_prob,
                           book_prob=0.5, price_american=ASSUMED_PRICE),
            ],
        })

    # ── Total: same, over/under the published number ──
    if g.market_over_under is not None:
        ou = g.market_over_under
        markets.append({
            "key": "total",
            "label": "Total",
            "question": f"Do both teams combine for more or fewer than {ou} points?",
            "probability_kind": "total",
            "line": ou,
            "source": source,
            "assumed_price": True,
            "selections": [
                _selection(label=f"Over {ou}", side="over",
                           model_prob=_debias(pred.over_prob), model_prob_raw=pred.over_prob,
                           book_prob=0.5, price_american=ASSUMED_PRICE),
                _selection(label=f"Under {ou}", side="under",
                           model_prob=_debias(pred.under_prob), model_prob_raw=pred.under_prob,
                           book_prob=0.5, price_american=ASSUMED_PRICE),
            ],
        })
    return markets


def _best_selection(markets: list[dict]) -> Optional[dict]:
    """The single strongest positive edge across every market, or None."""
    best = None
    for m in markets:
        for sel in m["selections"]:
            if sel["edge_pp"] is None or sel["edge_pp"] <= 0:
                continue
            if best is None or sel["edge_pp"] > best["edge_pp"]:
                best = {**sel, "market_key": m["key"], "market_label": m["label"],
                        "line": m["line"], "source": m["source"],
                        "assumed_price": m["assumed_price"],
                        "probability_kind": m["probability_kind"]}
    return best


async def _slate_entry(
    league: str, g: LiveGame, poly_markets, *, snapshot: bool = False,
) -> dict:
    """Model + live-market comparison for one scoreboard game.

    Pure by default: reading a page never writes a prediction. The scheduled
    server-side job passes ``snapshot=True`` to freeze pre-game picks into the
    ledger, so the track record does not depend on someone loading a page.
    """
    entry: dict = {
        "game": g.__dict__,
        "mapped": False,
        "model": None,
        "edges": [],
        "markets": [],
        "best_edge": None,
        "polymarket": match_game(poly_markets, g.home, g.away),
    }
    home = _map_code(league, g.home_abbr)
    away = _map_code(league, g.away_abbr)
    if not (home and away and home != away):
        return entry
    try:
        req = NFLPredictRequest(
            home=home, away=away,
            spread_line=g.market_spread,
            total_line=g.market_over_under,
        )
        pred = await _predict_gridiron(req, league)
        entry["mapped"] = True

        # Market-anchored calibration: shrink the headline win prob toward the
        # sharpest public estimate. Prefer the no-vig moneyline; fall back to the
        # win prob implied by the spread; fall back to the raw model.
        book_home = _no_vig_home_prob(g)
        anchor_home = book_home
        if anchor_home is None and g.market_spread is not None:
            anchor_home = _spread_to_home_prob(g.market_spread, league)
        if anchor_home is not None:
            w = _MARKET_ANCHOR_BY_LEAGUE.get(league, MARKET_ANCHOR_WEIGHT)
            cal_home = w * anchor_home + (1 - w) * pred.home_win_prob
        else:
            cal_home = pred.home_win_prob

        # Projected score: blend the model's expected points toward the score
        # implied by the market spread + total (the sharpest scoring estimate).
        implied = _market_implied_score(g)
        if implied is not None:
            sw = _SCORE_ANCHOR_BY_LEAGUE.get(league, 0.5)
            proj_home = sw * implied[0] + (1 - sw) * pred.home_expected_pts
            proj_away = sw * implied[1] + (1 - sw) * pred.away_expected_pts
        else:
            proj_home, proj_away = pred.home_expected_pts, pred.away_expected_pts

        entry["model"] = {
            "home_win_prob": pred.home_win_prob,
            "away_win_prob": pred.away_win_prob,
            "calibrated_home_win": cal_home,
            "calibrated_away_win": 1.0 - cal_home,
            "market_anchored": anchor_home is not None,
            "home_expected": pred.home_expected_pts,
            "away_expected": pred.away_expected_pts,
            "proj_home_score": round(proj_home, 1),
            "proj_away_score": round(proj_away, 1),
            "total_estimate": pred.total_points_estimate,
            "over_prob": pred.over_prob,
            "under_prob": pred.under_prob,
            "home_cover_prob": pred.home_cover_prob,
            "total_line": pred.total_line,
            "conditions": [c.model_dump() for c in pred.conditions],
            "live": False,
        }

        # ── Live in-game update: revise win prob + projected score from the
        #    current score, clock, and possession as events unfold ──
        if g.state == "in" and g.home_score is not None and g.away_score is not None:
            tot = pred.home_expected_pts + pred.away_expected_pts
            share = pred.home_expected_pts / tot if tot > 0 else 0.5
            live = live_projection(
                league=league,
                home_score=g.home_score, away_score=g.away_score,
                period=g.period, clock_seconds=_clock_seconds(g.clock),
                pregame_margin=pred.predicted_spread,
                total_estimate=pred.total_points_estimate,
                home_share=share,
                possession_home=(bool(g.possession_abbr) and g.possession_abbr == g.home_abbr),
            )
            entry["model"].update({
                "live": True,
                "live_home_win": live["home_win"],
                "live_away_win": live["away_win"],
                "live_proj_home": live["proj_home"],
                "live_proj_away": live["proj_away"],
                "time_remaining_pct": live["time_remaining_pct"],
            })

        # ── Model vs the live market ──
        edges: list[BetEdge] = []
        if g.market_home_ml and g.market_away_ml:
            edges += evaluate_market(
                "Moneyline (live)",
                [
                    (f"{home} ML", _debias(pred.home_win_prob), g.market_home_ml),
                    (f"{away} ML", _debias(pred.away_win_prob), g.market_away_ml),
                ],
                odds_format="american",
            )
        if g.market_over_under is not None:
            # Standard -110 pricing assumed when the feed has no prices
            edges += evaluate_market(
                f"Total {g.market_over_under} (−110 assumed)",
                [
                    (f"Over {g.market_over_under}", _debias(pred.over_prob), -110),
                    (f"Under {g.market_over_under}", _debias(pred.under_prob), -110),
                ],
                odds_format="american",
            )
        if g.market_spread is not None:
            edges += evaluate_market(
                f"Spread {g.market_spread:+.1f} (−110 assumed)",
                [
                    (f"{home} {g.market_spread:+.1f}", _debias(pred.home_cover_prob), -110),
                    (f"{away} {-g.market_spread:+.1f}", _debias(pred.away_cover_prob), -110),
                ],
                odds_format="american",
            )
        pm = entry["polymarket"]
        if pm:
            # Crowd prices are probabilities; 1/p = crowd decimal odds
            edges += evaluate_market(
                "Polymarket crowd",
                [
                    (f"{home} vs crowd", _debias(pred.home_win_prob),
                     max(1.01, 1.0 / max(pm["home_prob"], 1e-6))),
                    (f"{away} vs crowd", _debias(pred.away_win_prob),
                     max(1.01, 1.0 / max(pm["away_prob"], 1e-6))),
                ],
                odds_format="decimal",
            )
        edges.sort(key=lambda e: -e.edge_pp)
        entry["edges"] = [_edges_out([e])[0].model_dump() for e in edges]

        # Structured per-market comparison (model vs no-vig book vs crowd),
        # which is what the Game Center renders.
        entry["markets"] = _build_markets(league, g, pred, home, away, pm)
        entry["best_edge"] = _best_selection(entry["markets"])

        # ── Track record: snapshot pre-game; grading happens on every board fetch ──
        # The ledger stores the RAW model prob (book_home is logged separately),
        # so the head-to-head Brier stays an honest model-vs-book comparison.
        if snapshot and g.state == "pre":
            ledger.record_pregame(
                event_id=f"{league}:{g.event_id}",
                league=league,
                kickoff=g.kickoff,
                home=g.home,
                away=g.away,
                model_home_prob=pred.home_win_prob,
                model_total=pred.total_points_estimate,
                book_home_prob=book_home,
                crowd_home_prob=pm["home_prob"] if pm else None,
                market_spread=g.market_spread,
                market_total=g.market_over_under,
                home_code=home,
                away_code=away,
                home_elo=ratings.adjust(league, home, _TEAM_GETTERS[league](home).elo),
                away_elo=ratings.adjust(league, away, _TEAM_GETTERS[league](away).elo),
                consensus_home_prob=cal_home,
                model_version=MODEL_VERSION,
                book_source=g.market_provider or None,
            )
    except HTTPException:
        pass
    return entry


@router.get("/game/{league}/{event_id}", tags=["Predictions"])
async def game_detail(league: str, event_id: str) -> dict:
    """
    One game, fully modelled — the Game Center contract.

    Deliberately scoped to a single event: the slate endpoint runs the model for
    every game on the board, which is far too much work to render one matchup.
    Returns the live state, the model, a structured market comparison
    (model vs no-vig book vs crowd), the strongest edge, and the frozen ledger
    snapshot once one exists.
    """
    league = league.lower()
    if league not in FOCUS_LEAGUES:
        raise HTTPException(
            status_code=404,
            detail=f"league must be one of: {', '.join(FOCUS_LEAGUES)}",
        )

    board, poly = await asyncio.gather(
        fetch_scoreboard(league),
        fetch_league_markets(league),
    )
    ledger.grade_board(league, board.games)
    game = next((g for g in board.games if str(g.event_id) == str(event_id)), None)
    if game is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No {league.upper()} game {event_id!r} on the current board"
                if board.ok else "Live feed is temporarily unreachable"
            ),
        )

    entry = await _slate_entry(league, game, poly)
    snapshot = ledger.get_snapshot(f"{league}:{game.event_id}")

    return {
        "league": league,
        "event_id": str(game.event_id),
        "status": game.state,
        "fetched_at": board.fetched_at,
        "source_ok": board.ok,
        "source": game.market_provider or board.source,
        "model_version": MODEL_VERSION,
        "grade_scale": GRADE_SCALE,
        **entry,
        "snapshot": snapshot,
    }


async def snapshot_pregame(league: str) -> int:
    """Freeze every pre-game pick for a league into the ledger.

    Runs on the server's own schedule (see the app lifespan), never on a page
    view, so the track record reflects what the model said at a fixed cadence
    rather than whenever a visitor happened to load the site.
    """
    board, poly = await asyncio.gather(
        fetch_scoreboard(league),
        fetch_league_markets(league),
    )
    ledger.grade_board(league, board.games)
    ratings.reconcile()
    n = 0
    for g in board.games:
        if g.state != "pre" or not is_current(g):
            continue
        entry = await _slate_entry(league, g, poly, snapshot=True)
        if entry["mapped"]:
            n += 1
    return n


@router.get("/today/{league}", tags=["Predictions"])
async def today(league: str) -> dict:
    """
    The whole slate, auto-predicted: every game on today's board for a league
    (nfl | cfl | mlb) gets a model prediction with live weather + lineups,
    compared against the live sportsbook market from the ESPN feed —
    model probability vs where the public's money actually is.
    """
    league = league.lower()
    if league not in _TEAM_GETTERS:
        raise HTTPException(status_code=404, detail="league must be one of: nfl, cfl, mlb")

    board, poly_markets = await asyncio.gather(
        fetch_scoreboard(league),
        fetch_league_markets(league),
    )
    # Settle any finished games first (including yesterday's, which the date
    # window still covers), fold results into the self-correcting ratings, then
    # keep only games that belong on today's board.
    ledger.grade_board(league, board.games)
    ratings.reconcile()
    current = [g for g in board.games if is_current(g)]
    out_games = [await _slate_entry(league, g, poly_markets) for g in current]

    return {
        "league": league,
        "fetched_at": board.fetched_at,
        "source_ok": board.ok,
        "market_source": next(
            (g.market_provider for g in current if g.market_provider), "",
        ),
        "games": out_games,
    }


# ─── Best bets scanner ────────────────────────────────────────────────────────

_LEAGUE_FLAGS = {"nfl": "🏈", "ncaaf": "🏈"}

# The product is focused on American football: the NFL and NCAA FBS.
FOCUS_LEAGUES = ("nfl", "ncaaf")


@router.get("/best-bets", response_model=BestBetsResponse, tags=["Predictions"])
async def best_bets() -> BestBetsResponse:
    """
    Scan today's live NFL and NCAA football slates, comparing our (de-biased)
    model to the live sportsbook prices, and rank the strongest disagreements.
    Games already played never appear.
    """
    bets: list[BestBetOut] = []

    for lg in FOCUS_LEAGUES:
        board, poly = await asyncio.gather(
            fetch_scoreboard(lg),
            fetch_league_markets(lg),
        )
        ledger.grade_board(lg, board.games)
        flag = _LEAGUE_FLAGS[lg]
        label = lg.upper()
        for g in board.games:
            if g.state != "pre" or not is_current(g):
                continue
            entry = await _slate_entry(lg, g, poly)
            if not entry["mapped"]:
                continue
            for e in entry["edges"][:2]:   # top two edges per game, A/B only
                if e["rating"] not in ("A", "B"):
                    continue
                bets.append(BestBetOut(
                    fixture_id=f"{lg}:{g.event_id}",
                    kickoff=g.kickoff, venue="",
                    home=g.home, away=g.away,
                    home_flag=flag, away_flag=flag,
                    market=f"{label} · {e['market']}",
                    selection=e["selection"],
                    model_prob=e["model_prob"], market_prob=e["market_prob"],
                    edge_pp=e["edge_pp"], rating=e["rating"],
                    note=f"Model vs live {g.market_provider or 'market'} price",
                ))

    bets.sort(key=lambda b: (b.edge_pp is None, -(b.edge_pp or 0), -b.model_prob))
    return BestBetsResponse(
        generated_with="Live NFL + NCAA football slates, model de-biased and anchored to the market line",
        bets=bets[:24],
    )


# ─── Best parlay builder ──────────────────────────────────────────────────────

def _american_from_decimal(dec: float) -> int:
    """Decimal odds → American odds (rounded)."""
    if dec >= 2.0:
        return round((dec - 1.0) * 100.0)
    return round(-100.0 / (dec - 1.0))


async def _scan_parlay_legs() -> list[ParlayLeg]:
    """One strongest qualifying leg per upcoming football game.

    A parlay only makes sense out of plays the model both *likes to win* and
    sees *value* on, so a leg must clear the A/B edge bar (de-biased vs the
    market) AND be a better-than-even pick. One leg per game keeps outcomes
    independent-ish.
    """
    legs: list[ParlayLeg] = []
    for lg in FOCUS_LEAGUES:
        board, poly = await asyncio.gather(
            fetch_scoreboard(lg),
            fetch_league_markets(lg),
        )
        ledger.grade_board(lg, board.games)
        for g in board.games:
            if g.state != "pre" or not is_current(g):
                continue
            entry = await _slate_entry(lg, g, poly)
            if not entry["mapped"]:
                continue
            best = None
            for e in entry["edges"]:
                if e["rating"] not in ("A", "B"):
                    continue
                if e["model_prob"] < 0.50:          # parlay legs should be favourites
                    continue
                if e["decimal_odds"] <= 1.0:
                    continue
                if best is None or e["edge_pp"] > best["edge_pp"]:
                    best = e
            if best is not None:
                legs.append(ParlayLeg(
                    fixture_id=f"{lg}:{g.event_id}", league=lg, kickoff=g.kickoff,
                    home=g.home, away=g.away,
                    market=f"{lg.upper()} · {best['market']}", selection=best["selection"],
                    model_prob=best["model_prob"], market_prob=best["market_prob"],
                    decimal_odds=best["decimal_odds"], edge_pp=best["edge_pp"],
                    rating=best["rating"],
                ))
    legs.sort(key=lambda leg: -leg.edge_pp)
    return legs


@router.get("/best-parlay", response_model=BestParlayResponse, tags=["Predictions"])
async def best_parlay(max_legs: int = 3) -> BestParlayResponse:
    """
    Build the model's best-value parlay from today's NFL + NCAA football slate:
    the strongest de-biased edges the model both favours to win and sees value
    on, combined into one ticket with honest combined odds and expected value.
    """
    max_legs = max(2, min(max_legs, 5))
    pool = await _scan_parlay_legs()
    featured = pool[:max_legs]

    if not featured:
        return BestParlayResponse(
            generated_with="No qualifying value legs on the board right now — the model only parlays plays it both favours and prices as value.",
            legs=[], leg_count=0, model_prob=0.0, decimal_odds=1.0, american_odds=0,
            implied_prob=0.0, edge_pp=0.0, ev_per_unit=0.0, payout_per_unit=0.0, pool=pool,
        )

    dec = 1.0
    mp = 1.0
    for leg in featured:
        dec *= leg.decimal_odds
        mp *= leg.model_prob
    implied = 1.0 / dec
    ev = mp * (dec - 1.0) - (1.0 - mp)

    return BestParlayResponse(
        generated_with="Model's best-value parlay — de-biased edges the model favours to win, priced at the live line",
        legs=featured,
        leg_count=len(featured),
        model_prob=round(mp, 4),
        decimal_odds=round(dec, 2),
        american_odds=_american_from_decimal(dec),
        implied_prob=round(implied, 4),
        edge_pp=round((mp - implied) * 100, 1),
        ev_per_unit=round(ev, 3),
        payout_per_unit=round(dec - 1.0, 2),
        pool=pool[:8],
    )


# ─── World Cup spotlight for the dashboard ────────────────────────────────────

# Map an ESPN World Cup entrant (display name or abbreviation) to our team.
_WC_NAME_TO_CODE = {t.name.lower(): t.code for t in TEAMS.values()}
_WC_ABBR_ALIASES = {"USA": "USA", "MEX": "MEX", "KOR": "KOR", "NED": "NED"}


def _map_wc_team(name: str, abbr: str) -> Optional[str]:
    """Resolve a live World Cup team to our code by name first, then abbr."""
    if name and name.lower() in _WC_NAME_TO_CODE:
        return _WC_NAME_TO_CODE[name.lower()]
    code = _WC_ABBR_ALIASES.get(abbr.upper(), abbr.upper())
    return code if code in TEAMS else None


async def _wc_model_games() -> list[dict]:
    """
    Real World Cup games from the live ESPN feed (scheduled or in progress),
    each with the model run. Returns [] when nothing is on — we never invent
    fixtures for the front page.
    """
    board = await fetch_scoreboard("wc")
    ledger.grade_board("wc", board.games)
    games: list[dict] = []
    for g in board.games:
        if g.state == "post" or not is_current(g):
            continue
        home = _map_wc_team(g.home, g.home_abbr)
        away = _map_wc_team(g.away, g.away_abbr)
        if not (home and away and home != away):
            continue
        ht, at = get_team(home), get_team(away)
        r = predict_match(
            home, away,
            ratings.adjust("wc", home, ht.elo),
            ratings.adjust("wc", away, at.elo),
            neutral=True,
        )
        b = r.blended_probs
        games.append({
            "id": g.event_id, "kickoff": g.kickoff, "state": g.state, "detail": g.detail,
            "home": {"code": ht.code, "name": ht.name, "flag": ht.flag},
            "away": {"code": at.code, "name": at.name, "flag": at.flag},
            "home_score": g.home_score, "away_score": g.away_score,
            "home_win": b.home_win, "draw": b.draw, "away_win": b.away_win,
            "expected_scoreline": list(r.totals.expected_scoreline),
            "over_2_5": r.totals.over_2_5,
        })
    return games


@router.get("/soccer/upcoming", tags=["Predictions"])
async def soccer_upcoming(limit: int = 8) -> dict:
    """
    Real, scheduled/live World Cup games (from the ESPN feed) with the model
    already run. Empty when no World Cup games are actually on — the front page
    never shows invented fixtures.
    """
    games = sorted(await _wc_model_games(), key=lambda x: (x["state"] != "in", x["kickoff"]))
    return {"generated_with": "Dixon-Coles model on live ESPN fixtures", "games": games[:limit]}


# ─── Track record ─────────────────────────────────────────────────────────────

@router.get("/accuracy", tags=["Track record"])
def accuracy() -> dict:
    """
    The verifiable track record: every mapped pre-game prediction is
    snapshotted (model + book + crowd at the same instant) and auto-graded
    when the game goes final. Brier scores head-to-head on identical games.
    """
    ratings.reconcile()
    return {
        **ledger.accuracy_summary(),
        "performance": ledger.performance(),
        "recent": ledger.recent_graded(25),
    }


@router.get("/ratings/{league}/form", tags=["Track record"])
def ratings_form(league: str) -> dict:
    """
    How much recent results have moved each team's rating off its static prior
    (Elo points). Positive = playing above its baseline, negative = below.
    """
    league = league.lower()
    ratings.reconcile()
    rows = [r for r in ratings.standings(league) if abs(r["delta"]) >= 0.05]
    for r in rows:
        r["delta"] = round(r["delta"], 1)
    return {"league": league, "teams": rows}


# ─── Rankings ─────────────────────────────────────────────────────────────────

@router.get("/rankings/soccer", response_model=RankingsResponse, tags=["Rankings"])
def soccer_rankings() -> RankingsResponse:
    teams = [
        RankedTeam(
            rank=i + 1, code=t.code, name=t.name, flag=t.flag,
            elo=t.elo, group=t.group,
        )
        for i, t in enumerate(all_teams_sorted())
    ]
    return RankingsResponse(sport="soccer", teams=teams)


@router.get("/rankings/nfl", response_model=RankingsResponse, tags=["Rankings"])
def nfl_rankings() -> RankingsResponse:
    teams = [
        RankedTeam(
            rank=i + 1, code=t.code, name=f"{t.city} {t.name}",
            flag=t.flag, elo=t.elo, conference=t.conference,
        )
        for i, t in enumerate(all_nfl_teams_sorted())
    ]
    return RankingsResponse(sport="nfl", teams=teams)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@router.get("/fixtures/r16", tags=["Fixtures"])
def get_r16_fixtures() -> list[dict]:
    out = []
    for f in R16_FIXTURES:
        try:
            ht = get_team(f.home)
            at = get_team(f.away)
        except KeyError:
            continue
        out.append({
            "id": f.id,
            "stage": f.stage,
            "home": {"code": f.home, "name": ht.name, "flag": ht.flag, "elo": ht.elo},
            "away": {"code": f.away, "name": at.name, "flag": at.flag, "elo": at.elo},
            "venue": f.venue,
            "kickoff": f.kickoff,
            "sr_home_win": f.sr_home_win,
            "sr_draw": f.sr_draw,
            "sr_away_win": f.sr_away_win,
        })
    return out
