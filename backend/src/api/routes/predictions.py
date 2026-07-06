"""Soccer and NFL prediction endpoints with live conditions and value math."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException

from src.api.schemas import (
    AdjustmentOut,
    BestBetOut,
    BestBetsResponse,
    EdgeOut,
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
from src.data.nfl import all_nfl_teams_sorted, get_nfl_team
from src.data.world_cup import (
    R16_FIXTURES,
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
from src.predict.gridiron import predict_nfl_game
from src.predict.soccer import predict_match
from src.track import ledger, ratings
from src.value.edge import american_to_decimal
from src.simulate.monte_carlo import simulate_soccer
from src.value.edge import BetEdge, evaluate_market

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


_TEAM_GETTERS = {"nfl": get_nfl_team, "cfl": get_cfl_team, "mlb": get_mlb_team}


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
    adjustments = []
    weather: Optional[WeatherReport] = None
    if req.apply_weather and not req.neutral_site:
        weather = await fetch_gridiron_weather(league, home_code)
        adjustments.extend(
            mlb_weather_adjustments(weather) if league == "mlb"
            else nfl_weather_adjustments(weather)
        )
    if req.apply_lineups:
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

    return NFLPredictResponse(
        home_team=TeamInfo(
            code=home_t.code, name=f"{home_t.city} {home_t.name}",
            flag=home_t.flag, elo=home_t.elo,
            conference=getattr(home_t, "conference", None), division=home_t.division,
        ),
        away_team=TeamInfo(
            code=away_t.code, name=f"{away_t.city} {away_t.name}",
            flag=away_t.flag, elo=away_t.elo,
            conference=getattr(away_t, "conference", None), division=away_t.division,
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
MARKET_ANCHOR_WEIGHT = 0.35


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


async def _slate_entry(league: str, g: LiveGame, poly_markets) -> dict:
    """Model + live-market comparison for one scoreboard game. Snapshots
    pre-game picks to the ledger as a side effect."""
    entry: dict = {
        "game": g.__dict__,
        "mapped": False,
        "model": None,
        "edges": [],
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
        # no-vig line. Falls back to the raw model when no market is available.
        book_home = _no_vig_home_prob(g)
        if book_home is not None:
            w = MARKET_ANCHOR_WEIGHT
            cal_home = w * book_home + (1 - w) * pred.home_win_prob
        else:
            cal_home = pred.home_win_prob

        entry["model"] = {
            "home_win_prob": pred.home_win_prob,
            "away_win_prob": pred.away_win_prob,
            "calibrated_home_win": cal_home,
            "calibrated_away_win": 1.0 - cal_home,
            "market_anchored": book_home is not None,
            "home_expected": pred.home_expected_pts,
            "away_expected": pred.away_expected_pts,
            "total_estimate": pred.total_points_estimate,
            "over_prob": pred.over_prob,
            "under_prob": pred.under_prob,
            "home_cover_prob": pred.home_cover_prob,
            "total_line": pred.total_line,
            "conditions": [c.model_dump() for c in pred.conditions],
        }

        # ── Model vs the live market ──
        edges: list[BetEdge] = []
        if g.market_home_ml and g.market_away_ml:
            edges += evaluate_market(
                "Moneyline (live)",
                [
                    (f"{home} ML", pred.home_win_prob, g.market_home_ml),
                    (f"{away} ML", pred.away_win_prob, g.market_away_ml),
                ],
                odds_format="american",
            )
        if g.market_over_under is not None:
            # Standard -110 pricing assumed when the feed has no prices
            edges += evaluate_market(
                f"Total {g.market_over_under} (−110 assumed)",
                [
                    (f"Over {g.market_over_under}", pred.over_prob, -110),
                    (f"Under {g.market_over_under}", pred.under_prob, -110),
                ],
                odds_format="american",
            )
        if g.market_spread is not None:
            edges += evaluate_market(
                f"Spread {g.market_spread:+.1f} (−110 assumed)",
                [
                    (f"{home} {g.market_spread:+.1f}", pred.home_cover_prob, -110),
                    (f"{away} {-g.market_spread:+.1f}", pred.away_cover_prob, -110),
                ],
                odds_format="american",
            )
        pm = entry["polymarket"]
        if pm:
            # Crowd prices are probabilities; 1/p = crowd decimal odds
            edges += evaluate_market(
                "Polymarket crowd",
                [
                    (f"{home} vs crowd", pred.home_win_prob,
                     max(1.01, 1.0 / max(pm["home_prob"], 1e-6))),
                    (f"{away} vs crowd", pred.away_win_prob,
                     max(1.01, 1.0 / max(pm["away_prob"], 1e-6))),
                ],
                odds_format="decimal",
            )
        edges.sort(key=lambda e: -e.edge_pp)
        entry["edges"] = [_edges_out([e])[0].model_dump() for e in edges]

        # ── Track record: snapshot pre-game; grading happens on every board fetch ──
        # The ledger stores the RAW model prob (book_home is logged separately),
        # so the head-to-head Brier stays an honest model-vs-book comparison.
        if g.state == "pre":
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
            )
    except HTTPException:
        pass
    return entry


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

_LEAGUE_FLAGS = {"mlb": "⚾", "nfl": "🏈", "cfl": "🍁"}


def _kickoff_upcoming(kickoff: str, now: datetime) -> bool:
    try:
        return datetime.fromisoformat(kickoff) > now
    except ValueError:
        return True   # unparseable — keep rather than silently hide


@router.get("/best-bets", response_model=BestBetsResponse, tags=["Predictions"])
async def best_bets() -> BestBetsResponse:
    """
    Scan today's live slates (MLB/NFL/CFL) and upcoming soccer fixtures with
    live weather + lineups applied, and rank the biggest disagreements between
    our model and the live market prices. Games already played never appear.
    """
    now = datetime.now(timezone.utc)
    bets: list[BestBetOut] = []

    # ── Live league slates: model vs the live sportsbook/crowd prices ──
    for lg in ("mlb", "nfl", "cfl"):
        board, poly = await asyncio.gather(
            fetch_scoreboard(lg),
            fetch_league_markets(lg),
        )
        ledger.grade_board(lg, board.games)
        flag = _LEAGUE_FLAGS[lg]
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
                    market=f"{lg.upper()} · {e['market']}",
                    selection=e["selection"],
                    model_prob=e["model_prob"], market_prob=e["market_prob"],
                    edge_pp=e["edge_pp"], rating=e["rating"],
                    note=f"Model vs live {g.market_provider or 'market'} price",
                ))

    # ── Soccer: upcoming fixtures only ──
    upcoming = [f for f in R16_FIXTURES if _kickoff_upcoming(f.kickoff, now)]
    venues = {f.venue for f in upcoming if f.venue}
    reports = await asyncio.gather(*(fetch_weather(v) for v in venues))
    weather_by_venue = dict(zip(venues, reports))

    for fix in upcoming:
        try:
            ht = get_team(fix.home)
            at = get_team(fix.away)
        except KeyError:
            continue

        adjustments = list(soccer_weather_adjustments(weather_by_venue.get(fix.venue)))
        adjustments += soccer_altitude_adjustments(fix.venue, fix.home, fix.away, ht.name, at.name)
        adjustments += soccer_lineup_adjustments(fix.home, fix.away)

        result = predict_match(
            fix.home, fix.away, ht.elo, at.elo,
            home_is_host=fix.home_is_host_nation,
            neutral=fix.neutral,
            sr_home_win=fix.sr_home_win,
            sr_draw=fix.sr_draw,
            sr_away_win=fix.sr_away_win,
            adjustments=adjustments,
        )

        common = dict(
            fixture_id=fix.id, kickoff=fix.kickoff, venue=fix.venue,
            home=ht.name, away=at.name, home_flag=ht.flag, away_flag=at.flag,
        )

        # Blended probs vs SR reference: the blend already anchors to SR, so a
        # residual gap only appears when live data or the model disagree hard.
        # Draws are excluded — Poisson models systematically inflate them.
        if fix.sr_home_win is not None:
            for selection, model_p, sr_p in (
                (f"{ht.name} win", result.blended_probs.home_win, fix.sr_home_win),
                (f"{at.name} win", result.blended_probs.away_win, fix.sr_away_win),
            ):
                if sr_p is None:
                    continue
                edge = (model_p - sr_p) * 100.0
                if edge >= 2.5:
                    bets.append(BestBetOut(
                        **common, market="1X2", selection=selection,
                        model_prob=model_p, market_prob=sr_p,
                        edge_pp=edge,
                        rating="A" if edge >= 4 else "B",
                        note="Blended model vs SportRadar reference price",
                    ))

        # Totals signals: strong model conviction on 2.5 either way
        if result.totals.over_2_5 >= 0.62:
            bets.append(BestBetOut(
                **common, market="Total 2.5", selection="Over 2.5",
                model_prob=result.totals.over_2_5, market_prob=None, edge_pp=None,
                rating="B" if result.totals.over_2_5 >= 0.68 else "C",
                note="Model conviction incl. live weather/lineups — compare to your book's price",
            ))
        elif result.totals.under_2_5 >= 0.62:
            bets.append(BestBetOut(
                **common, market="Total 2.5", selection="Under 2.5",
                model_prob=result.totals.under_2_5, market_prob=None, edge_pp=None,
                rating="B" if result.totals.under_2_5 >= 0.68 else "C",
                note="Model conviction incl. live weather/lineups — compare to your book's price",
            ))

    bets.sort(key=lambda b: (b.edge_pp is None, -(b.edge_pp or 0), -b.model_prob))
    return BestBetsResponse(
        generated_with="Live slates (MLB/NFL/CFL) + Dixon-Coles soccer, with live weather + lineups",
        bets=bets[:24],
    )


# ─── World Cup spotlight for the dashboard ────────────────────────────────────

@router.get("/soccer/upcoming", tags=["Predictions"])
async def soccer_upcoming(limit: int = 8) -> dict:
    """
    Upcoming World Cup fixtures with the model already run (win/draw/win,
    projected scoreline, over 2.5) plus live weather/altitude — so the front
    page can feature the tournament with nothing to fill in.
    """
    now = datetime.now(timezone.utc)
    upcoming = sorted(
        (f for f in R16_FIXTURES if _kickoff_upcoming(f.kickoff, now)),
        key=lambda f: f.kickoff,
    )
    venues = {f.venue for f in upcoming if f.venue}
    reports = await asyncio.gather(*(fetch_weather(v) for v in venues))
    wx = dict(zip(venues, reports))

    games: list[dict] = []
    for fix in upcoming[:limit]:
        try:
            ht = get_team(fix.home)
            at = get_team(fix.away)
        except KeyError:
            continue
        adj = list(soccer_weather_adjustments(wx.get(fix.venue)))
        adj += soccer_altitude_adjustments(fix.venue, fix.home, fix.away, ht.name, at.name)
        adj += soccer_lineup_adjustments(fix.home, fix.away)
        r = predict_match(
            fix.home, fix.away,
            ratings.adjust("wc", fix.home, ht.elo),
            ratings.adjust("wc", fix.away, at.elo),
            home_is_host=fix.home_is_host_nation, neutral=fix.neutral,
            sr_home_win=fix.sr_home_win, sr_draw=fix.sr_draw, sr_away_win=fix.sr_away_win,
            adjustments=adj,
        )
        b = r.blended_probs
        games.append({
            "id": fix.id, "kickoff": fix.kickoff, "venue": fix.venue,
            "home": {"code": ht.code, "name": ht.name, "flag": ht.flag},
            "away": {"code": at.code, "name": at.name, "flag": at.flag},
            "home_win": b.home_win, "draw": b.draw, "away_win": b.away_win,
            "expected_scoreline": list(r.totals.expected_scoreline),
            "over_2_5": r.totals.over_2_5,
            "conditions": [a.label for a in adj],
        })

    return {"generated_with": "Dixon-Coles model + live conditions", "games": games}


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
