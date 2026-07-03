"""Soccer and NFL prediction endpoints with live conditions and value math."""
from __future__ import annotations

import asyncio
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
from src.data.nfl import all_nfl_teams_sorted, get_nfl_team
from src.data.world_cup import (
    R16_FIXTURES,
    all_teams_sorted,
    get_scorers_for_team,
    get_team,
)
from src.ingest.weather import WeatherReport, fetch_nfl_weather, fetch_weather
from src.predict.adjustments import (
    nfl_lineup_adjustments,
    nfl_weather_adjustments,
    soccer_lineup_adjustments,
    soccer_weather_adjustments,
)
from src.predict.gridiron import predict_nfl_game
from src.predict.soccer import predict_match
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
    if req.apply_lineups:
        adjustments.extend(soccer_lineup_adjustments(
            home_code, away_code, req.missing_home, req.missing_away,
        ))

    scorers = get_scorers_for_team(home_code) + get_scorers_for_team(away_code)

    result = predict_match(
        home_code, away_code,
        home_t.elo, away_t.elo,
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


@router.post("/predict/nfl", response_model=NFLPredictResponse, tags=["Predictions"])
async def predict_nfl(req: NFLPredictRequest) -> NFLPredictResponse:
    home_code = req.home.upper()
    away_code = req.away.upper()

    try:
        home_t = get_nfl_team(home_code)
        away_t = get_nfl_team(away_code)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # ── Live conditions ──
    adjustments = []
    weather: Optional[WeatherReport] = None
    if req.apply_weather and not req.neutral_site:
        weather = await fetch_nfl_weather(home_code)
        adjustments.extend(nfl_weather_adjustments(weather))
    if req.apply_lineups:
        adjustments.extend(nfl_lineup_adjustments(
            home_code, away_code, req.missing_home, req.missing_away,
        ))

    result = predict_nfl_game(
        home_code, away_code,
        home_t.elo, away_t.elo,
        neutral_site=req.neutral_site,
        spread_line=req.spread_line,
        total_line=req.total_line,
        adjustments=adjustments,
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
            conference=home_t.conference, division=home_t.division,
        ),
        away_team=TeamInfo(
            code=away_t.code, name=f"{away_t.city} {away_t.name}",
            flag=away_t.flag, elo=away_t.elo,
            conference=away_t.conference, division=away_t.division,
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


# ─── Best bets scanner ────────────────────────────────────────────────────────

@router.get("/best-bets", response_model=BestBetsResponse, tags=["Predictions"])
async def best_bets() -> BestBetsResponse:
    """
    Scan all upcoming fixtures with live weather + lineups applied and rank
    the biggest disagreements between our model and the SportRadar reference
    prices, plus strong totals signals.
    """
    # Fetch weather for all fixture venues concurrently (deduplicated)
    venues = {f.venue for f in R16_FIXTURES if f.venue}
    reports = await asyncio.gather(*(fetch_weather(v) for v in venues))
    weather_by_venue = dict(zip(venues, reports))

    bets: list[BestBetOut] = []
    for fix in R16_FIXTURES:
        try:
            ht = get_team(fix.home)
            at = get_team(fix.away)
        except KeyError:
            continue

        adjustments = list(soccer_weather_adjustments(weather_by_venue.get(fix.venue)))
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
        generated_with="Dixon-Coles Elo model + live weather + lineup availability",
        bets=bets,
    )


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
